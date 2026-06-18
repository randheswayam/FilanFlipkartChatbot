import os
import re
import pandas as pd
from pandasql import sqldf

# Determine the base directory and normalize backslashes to forward slashes to avoid Windows \r and \f escape sequences
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
FAQ_PATH = f"{BASE_DIR}/app/resources/faq_data.csv"
PRODUCT_PATH = f"{BASE_DIR}/app/resources/ecommerce_data_final.csv"

# Global variables to cache loaded DataFrames
_faq_df = None
_product_df = None

def clear_data_caches():
    """Clears the cached DataFrames to force reloading from disk."""
    global _faq_df, _product_df
    _faq_df = None
    _product_df = None

def get_faq_df():
    """Loads and caches the FAQ dataset."""
    global _faq_df
    if _faq_df is None:
        if os.path.exists(FAQ_PATH):
            _faq_df = pd.read_csv(FAQ_PATH)
            _faq_df.columns = _faq_df.columns.str.strip().str.lower()
        else:
            raise FileNotFoundError(f"FAQ file not found at {FAQ_PATH}")
    return _faq_df

def get_product_df():
    """Loads and caches the product catalog dataset."""
    global _product_df
    if _product_df is None:
        if os.path.exists(PRODUCT_PATH):
            _product_df = pd.read_csv(PRODUCT_PATH)
            _product_df.columns = _product_df.columns.str.strip().str.lower()
            
            # Clean up price (ensure numeric)
            if 'price' in _product_df.columns:
                if _product_df['price'].dtype == 'object':
                    _product_df['price'] = _product_df['price'].astype(str).str.replace(r'[^\d.]', '', regex=True)
                    _product_df['price'] = pd.to_numeric(_product_df['price'], errors='coerce')
                _product_df['price'] = _product_df['price'].fillna(0.0)
                
            # Clean up rating (ensure numeric)
            if 'avg_rating' in _product_df.columns:
                _product_df['avg_rating'] = pd.to_numeric(_product_df['avg_rating'], errors='coerce').fillna(0.0)
        else:
            raise FileNotFoundError(f"Product file not found at {PRODUCT_PATH}")
    return _product_df

# Common conversational stop words to filter out for keyword extraction
STOP_WORDS = {
    'what', 'is', 'the', 'of', 'for', 'in', 'on', 'at', 'with', 'a', 'an', 'to', 
    'do', 'you', 'have', 'show', 'me', 'find', 'get', 'price', 'rating', 'ratings', 
    'brand', 'product', 'products', 'any', 'some', 'please', 'tell', 'about', 
    'how', 'much', 'cost', 'can', 'i', 'policy', 'are', 'there', 'who', 'where'
}

def get_words(text) -> set:
    """Utility to tokenize text into a set of clean whole words."""
    if pd.isna(text):
        return set()
    clean = str(text).lower().replace('|', ' ').replace('/', ' ').replace('-', ' ').replace('\\', ' ')
    clean = clean.translate(str.maketrans('', '', '?!.,:;()[]{}""\'\''))
    return set(clean.split())

def search_faqs_keyword(query: str) -> pd.DataFrame:
    """Searches FAQs for occurrences of query terms in question or answer."""
    df = get_faq_df()
    if df.empty or not query:
        return pd.DataFrame(columns=df.columns)
    
    clean_query = query.lower().translate(str.maketrans('', '', '?!.,:;()'))
    raw_terms = clean_query.split()
    terms = [t for t in raw_terms if t not in STOP_WORDS]
    if not terms:
        terms = raw_terms
        
    mask = df.apply(
        lambda row: any(
            t in get_words(row['question']) or t in get_words(row['answer']) for t in terms
        ), axis=1
    )
    return df[mask]

def search_products_keyword(query: str, limit: int = 5) -> pd.DataFrame:
    """Searches products matching brand or title keywords."""
    df = get_product_df()
    if df.empty or not query:
        return pd.DataFrame(columns=df.columns)
    
    clean_query = query.lower().translate(str.maketrans('', '', '?!.,:;()'))
    raw_terms = clean_query.split()
    terms = [t for t in raw_terms if t not in STOP_WORDS]
    if not terms:
        terms = raw_terms
        
    mask = df.apply(
        lambda row: all(
            t in get_words(row['title']) or get_words(row['brand']) for t in terms
        ), axis=1
    )
    results = df[mask].drop_duplicates(subset=['title', 'brand', 'price'])
    return results.head(limit)

def search_products_sql(sql_where_clause: str, limit: int = 5) -> pd.DataFrame:
    """Executes a SQL query against the products table."""
    products = get_product_df()
    clean_where = sql_where_clause.strip()
    if clean_where.lower().startswith("where"):
        clean_where = clean_where[5:].strip()
        
    query = f"SELECT * FROM products WHERE {clean_where} LIMIT {limit}"
    try:
        result_df = sqldf(query, locals())
        return result_df
    except Exception as e:
        err_df = pd.DataFrame(columns=products.columns)
        err_df['error'] = [str(e)]
        return err_df

def extract_constraints(query_text: str) -> dict:
    """
    Parses conversational shopper requests to extract price limits and brands.
    Converts them into a ChromaDB 'where' metadata filter dictionary.
    """
    where = {}
    query_lower = query_text.lower()
    
    # 1. Extract price constraints
    price_match = re.search(r'(?:under|below|less than|less than or equal to|<=?|₹\s*)\s*(\d+)', query_lower)
    if price_match:
        price_val = float(price_match.group(1))
        where["price"] = {"$lte": price_val}
    else:
        # Check for greater than constraints
        price_gt_match = re.search(r'(?:above|over|greater than|>=?)\s*(\d+)', query_lower)
        if price_gt_match:
            price_val = float(price_gt_match.group(1))
            where["price"] = {"$gte": price_val}
            
    # 2. Extract brand names
    brands = ["puma", "nike", "sparx", "campus", "asian", "aadi", "shozie", "vokline", "fabbmate", "cultsport", "fila", "sparx"]
    matched_brand = None
    for b in brands:
        if b in query_lower:
            matched_brand = b.capitalize()
            if b == "fila":
                matched_brand = "FILA"
            elif b == "aadi":
                matched_brand = "aadi "
            break
            
    if matched_brand:
        brand_filter = {"brand": {"$eq": matched_brand}}
        if where:
            where = {
                "$and": [
                    where,
                    brand_filter
                ]
            }
        else:
            where = brand_filter
            
    return where if where else None
