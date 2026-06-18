import os
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from src.utils import PRODUCT_PATH
from src.retriever import get_chroma_client, init_and_index_db

def scrape_flipkart_live(search_term: str, limit: int = 5) -> pd.DataFrame:
    """
    Searches live Flipkart using headless Selenium and extracts product detail information,
    following the scraping logic defined in flipkart_data_extraction.ipynb.
    """
    # Configure Chrome options to run headlessly
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")  # suppress logging
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Search URL
        encoded_term = search_term.replace(" ", "+")
        search_url = f"https://www.flipkart.com/search?q={encoded_term}"
        driver.get(search_url)
        
        # Wait for pagination/product card elements to load
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[target="_blank"]'))
        )
        
        # Collect links matching the rPDeLR product card class (as in the Jupyter notebook)
        elements = driver.find_elements(By.CLASS_NAME, 'rPDeLR')
        if not elements:
            # Fallback generic targets if class name differs (e.g. list view VS grid view layout)
            elements = driver.find_elements(By.CSS_SELECTOR, 'a[target="_blank"]')
            
        links = []
        for el in elements:
            href = el.get_attribute('href')
            if href and "/p/" in href:  # Ensure it is a product page link
                # Clean URL (strip tracking params for canonical storage)
                clean_href = href.split("?")[0]
                if clean_href not in links:
                    links.append(clean_href)
                    if len(links) >= limit:
                        break
                        
        if not links:
            return pd.DataFrame()
            
        # Parse each product link to get individual details (brand, title, price, discount, ratings)
        scraped_products = []
        for url in links:
            try:
                driver.get(url)
                # Wait for title element to be present
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'VU-ZEz'))
                )
                
                # Brand (class 'mEh187')
                try:
                    brand = driver.find_element(By.CLASS_NAME, 'mEh187').text
                except Exception:
                    brand = "Generic"
                    
                # Title (class 'VU-ZEz')
                try:
                    title = driver.find_element(By.CLASS_NAME, 'VU-ZEz').text
                    title = re.sub(r'\s*\([^)]*\)', '', title)  # remove color/size in parenthesis
                except Exception:
                    title = "Unknown Product"
                    
                # Price (class 'Nx9bqj')
                try:
                    price_text = driver.find_element(By.CLASS_NAME, 'Nx9bqj').text
                    price_num = "".join(re.findall(r'\d+', price_text))
                    price = float(price_num) if price_num else 0.0
                except Exception:
                    price = 0.0
                    
                # Discount (class 'UkUFwK')
                try:
                    discount_text = driver.find_element(By.CLASS_NAME, 'UkUFwK').text
                    disc_num = "".join(re.findall(r'\d+', discount_text))
                    discount = float(disc_num) / 100 if disc_num else 0.0
                except Exception:
                    discount = 0.0
                    
                # Average Rating (class 'XQDdHH')
                try:
                    avg_rating = float(driver.find_element(By.CLASS_NAME, 'XQDdHH').text)
                except Exception:
                    avg_rating = 0.0
                    
                # Total Ratings Count (class 'Wphh3N')
                try:
                    total_ratings_text = driver.find_element(By.CLASS_NAME, 'Wphh3N').text.split(' ')[0]
                    total_ratings = int(total_ratings_text.replace(',', ''))
                except Exception:
                    total_ratings = 0
                    
                scraped_products.append({
                    "product_link": url,
                    "title": title,
                    "brand": brand,
                    "price": price,
                    "discount": discount,
                    "avg_rating": avg_rating,
                    "total_ratings": total_ratings
                })
            except Exception:
                continue  # skip failed page
                
        return pd.DataFrame(scraped_products)
        
    finally:
        driver.quit()

def update_product_database_and_reindex(new_df: pd.DataFrame) -> int:
    """
    Appends new scraped products to the main CSV database and updates the ChromaDB vector index.
    """
    if new_df.empty:
        return 0
        
    # Read existing products database
    if os.path.exists(PRODUCT_PATH):
        old_df = pd.read_csv(PRODUCT_PATH)
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        
    # Deduplicate based on product links
    combined_df = combined_df.drop_duplicates(subset=['product_link'])
    
    # Save back to CSV
    combined_df.to_csv(PRODUCT_PATH, index=False)
    
    # Clear data cache to ensure loaders read the updated CSV from disk
    from src.utils import clear_data_caches
    clear_data_caches()
    
    # Delete old ChromaDB products collection to force re-indexing
    client = get_chroma_client()
    try:
        client.delete_collection("products")
    except Exception:
        pass
        
    # Trigger RAG re-indexing
    init_and_index_db()
    
    return len(new_df)
