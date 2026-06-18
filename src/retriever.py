import os
import pandas as pd
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer
from src.utils import get_faq_df, get_product_df

# Base directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
DB_PATH = f"{BASE_DIR}/chroma_db"

# Cache singletons
_model = None
_client = None

def get_embedding_model() -> SentenceTransformer:
    """Gets and caches the sentence-transformer embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_chroma_client() -> chromadb.PersistentClient:
    """Gets and caches the persistent ChromaDB client."""
    global _client
    if _client is None:
        os.makedirs(DB_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=DB_PATH)
    return _client

def init_and_index_db():
    """
    Initializes collections and indexes FAQ and product CSVs if they are not already cached.
    """
    client = get_chroma_client()
    model = get_embedding_model()
    
    # 1. FAQ collection
    faq_collection = client.get_or_create_collection(name="faqs")
    if faq_collection.count() == 0:
        faq_df = get_faq_df()
        questions = faq_df['question'].tolist()
        answers = faq_df['answer'].tolist()
        
        embeddings = model.encode(questions, show_progress_bar=False).tolist()
        metadatas = [{"question": q, "answer": a} for q, a in zip(questions, answers)]
        ids = [f"faq_{i}" for i in range(len(questions))]
        
        faq_collection.add(
            documents=questions,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
    # 2. Product collection
    prod_collection = client.get_or_create_collection(name="products")
    if prod_collection.count() == 0:
        prod_df = get_product_df()
        
        chunks = []
        metadatas = []
        ids = []
        for i, row in prod_df.iterrows():
            title = str(row['title'])
            brand = str(row['brand']).strip().capitalize()
            price = float(row['price'])
            rating = float(row['avg_rating'])
            link = str(row['product_link'])
            
            chunk = f"Product: {title}. Brand: {brand}. Price: Rs {price}. Rating: {rating} stars."
            chunks.append(chunk)
            
            # Save metadata values with standardized keys for queries
            metadatas.append({
                "title": title,
                "brand": brand,
                "price": price,
                "avg_rating": rating,
                "product_link": link
            })
            ids.append(f"prod_{i}")
            
        embeddings = model.encode(chunks, batch_size=64, show_progress_bar=False).tolist()
        
        prod_collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

def query_faqs(query_text: str, n_results: int = 1) -> list:
    """Queries the FAQ collection and returns matching questions and answers."""
    client = get_chroma_client()
    model = get_embedding_model()
    collection = client.get_collection(name="faqs")
    
    query_emb = model.encode([query_text]).tolist()
    res = collection.query(query_embeddings=query_emb, n_results=n_results)
    
    matches = []
    if res and res['metadatas'] and len(res['metadatas'][0]) > 0:
        for metadata, dist in zip(res['metadatas'][0], res['distances'][0]):
            matches.append({
                "question": metadata["question"],
                "answer": metadata["answer"],
                "distance": dist
            })
    return matches

def query_products(query_text: str, n_results: int = 5, where: dict = None) -> list:
    """
    Queries the Product collection semantically, with optional metadata filtering.
    Falls back to simple semantic search if metadata filters produce zero results.
    """
    client = get_chroma_client()
    model = get_embedding_model()
    collection = client.get_collection(name="products")
    
    query_emb = model.encode([query_text]).tolist()
    
    # 1. Execute query with metadata filter if provided
    if where:
        res = collection.query(query_embeddings=query_emb, n_results=n_results, where=where)
        # Fallback if strict filter yields no results
        if not res or not res['metadatas'] or len(res['metadatas'][0]) == 0:
            res = collection.query(query_embeddings=query_emb, n_results=n_results)
    else:
        res = collection.query(query_embeddings=query_emb, n_results=n_results)
        
    matches = []
    if res and res['metadatas'] and len(res['metadatas'][0]) > 0:
        seen = set()
        for metadata, dist in zip(res['metadatas'][0], res['distances'][0]):
            title = metadata["title"]
            brand = metadata["brand"]
            price = metadata["price"]
            
            key = (title, brand, price)
            if key in seen:
                continue
            seen.add(key)
            
            matches.append({
                "title": title,
                "brand": brand,
                "price": price,
                "avg_rating": metadata["avg_rating"],
                "product_link": metadata["product_link"],
                "distance": dist
            })
    return matches
