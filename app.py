import os
import sys
import time
import pandas as pd

# Add the project root directory to sys.path to resolve local 'src' imports robustly
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils import (
    get_faq_df, 
    get_product_df, 
    search_products_sql,
    extract_constraints
)
from src.router import route_query
from src.retriever import init_and_index_db, query_faqs, query_products
from src.llm import generate_conversational_faq_answer, generate_conversational_product_answer
import streamlit as st

# Set up page configurations
st.set_page_config(
    page_title="Flipkart FAQ & Product Inquiry Chatbot",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Flipkart styling
custom_css = """
<style>
    /* Main body background & styling */
    .stApp {
        background-color: #f1f3f6;
    }
    
    /* Header Banner with Flipkart Blue Gradient */
    .fk-header {
        background: linear-gradient(90deg, #172337 0%, #2874f0 100%);
        padding: 20px;
        border-radius: 8px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .fk-header h1 {
        margin: 0;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        color: white !important;
    }
    
    .fk-header p {
        margin: 5px 0 0 0;
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        opacity: 0.95;
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #172337;
        color: white;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    /* Sidebar Headers */
    .sidebar-header {
        color: #ffe500;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.25rem;
        margin-top: 15px;
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 5px;
    }
    
    /* Highlight labels */
    .highlight-yellow {
        color: #ffe500;
        font-weight: bold;
    }
    
    /* Chat Container Tweaks */
    .stChatMessage {
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Style user messages */
    div[data-testid="stChatMessage"] {
        background-color: white;
        border-left: 5px solid #2874f0;
    }
    
    /* Style assistant messages */
    div[data-testid="stChatMessageAssis"] {
        background-color: #eaf2ff;
        border-left: 5px solid #ffe500;
    }
    
    /* Quick tip container */
    .tip-box {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 12px;
        border-radius: 6px;
        margin-top: 10px;
        font-size: 0.9rem;
    }
</style>
"""

# Inject custom styling
st.markdown(custom_css, unsafe_allow_html=True)

# Load databases & Index vector store
try:
    init_and_index_db()
    product_df = get_product_df()
    data_loaded = True
except Exception as e:
    st.error(f"Failed to initialize database: {e}")
    data_loaded = False

# Define Sidebar Content
with st.sidebar:
    st.image("https://img1a.flixcart.com/www/linchpin/fk-cp-zion/img/flipkart-plus_8d85f4.png", width=120)
    
    st.markdown('<div class="sidebar-header">Prototype Info</div>', unsafe_allow_html=True)
    st.markdown(
        f"**Active Phase**: <span class='highlight-yellow'>Phase 5 (Optimized)</span><br>"
        f"**Mode**: Hybrid Search RAG<br>"
        f"**Products Catalog Size**: {len(product_df) if data_loaded else 0} items",
        unsafe_allow_html=True
    )
    
    # Live Scraper Sidebar Console
    st.markdown('<div class="sidebar-header">🚀 Live Flipkart Scraper</div>', unsafe_allow_html=True)
    st.markdown("Query live Flipkart in background & update your vector store:")
    scrape_input = st.text_input("Enter product to scrape:", placeholder="e.g. smartwatches")
    
    if st.button("Scrape & Index Live Data"):
        if scrape_input.strip():
            with st.spinner(f"Scraping live Flipkart for '{scrape_input}'..."):
                try:
                    from src.scraper import scrape_flipkart_live, update_product_database_and_reindex
                    new_scraped_df = scrape_flipkart_live(scrape_input, limit=5)
                    if new_scraped_df.empty:
                        st.warning("No listings found. The site might be blocking headless requests. Try another term.")
                    else:
                        added_count = update_product_database_and_reindex(new_scraped_df)
                        st.success(f"Added {added_count} live products to vector store!")
                        time.sleep(2)
                        st.rerun()
                except Exception as ex:
                    st.error(f"Scraper Error: {ex}")
        else:
            st.warning("Please enter a search term.")
            
    st.markdown('<div class="sidebar-header">Testing Conversational Output</div>', unsafe_allow_html=True)
    st.markdown(
        "Try typing queries naturally:\n"
        "- *'can I pay on delivery?'*\n"
        "- *'what are options for damaged items?'*\n"
        "- *'find me some walking sneakers'*."
    )
    
    st.markdown(
        '<div class="tip-box">💡 <b>Note:</b> You can also trigger live scraping directly inside chat using <code>/scrape &lt;query&gt;</code>!</div>', 
        unsafe_allow_html=True
    )

# Render main header banner
st.markdown(
    """
    <div class="fk-header">
        <h1>Flipkart Support & Inquiry Assistant</h1>
        <p>Conversational RAG Assistant (ChromaDB + Groq) with Live Web Scraper</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Initialize message log in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 **Welcome to the Flipkart RAG Support Assistant!**\n\n"
                       "I am running with **Intent Routing, ChromaDB Vector Retrieval, and Groq LLM Generation**.\n\n"
                       "You can query our local catalog, or scrape new categories from the **live Flipkart website** using the sidebar console or typing `/scrape <query>` (e.g. `/scrape smartwatches`)."
        }
    ]

# Display historical messages from session state
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Helper function to convert products DataFrame to a neat Markdown table
def format_products_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "*No products found matching the criteria.*"
    
    md = "| Product Title | Brand | Price | Rating | Link |\n"
    md += "| :--- | :--- | :--- | :--- | :--- |\n"
    for _, row in df.iterrows():
        title = str(row['title'])
        if len(title) > 50:
            title = title[:47] + "..."
        brand = str(row['brand']).capitalize()
        price = f"₹{row['price']}"
        rating = f"⭐ {row['avg_rating']}"
        link = f"[View Details]({row['product_link']})"
        md += f"| {title} | {brand} | {price} | {rating} | {link} |\n"
    return md

# Helper function to convert product dictionaries list to Markdown table
def format_product_matches_markdown(matches: list) -> str:
    if not matches:
        return "*No products found matching the criteria.*"
        
    md = "| Product Title | Brand | Price | Rating | Distance | Link |\n"
    md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for row in matches:
        title = row['title']
        if len(title) > 50:
            title = title[:47] + "..."
        brand = row['brand'].capitalize()
        price = f"₹{row['price']}"
        rating = f"⭐ {row['avg_rating']}"
        dist = f"{row['distance']:.4f}"
        link = f"[View Details]({row['product_link']})"
        md += f"| {title} | {brand} | {price} | {rating} | `{dist}` | {link} |\n"
    return md

# Accept new user input
if data_loaded and (user_input := st.chat_input("Ask a question, enter keywords, or use /search ...")):
    # Render user input in the UI
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Save user input to session history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Process user query
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response_content = ""
        
        # 1. Check if user is triggering a live scrape from the chat box
        if user_input.strip().lower().startswith("/scrape"):
            parts = user_input.strip().split(maxsplit=1)
            scrape_term = parts[1] if len(parts) > 1 else ""
            if not scrape_term:
                response_content = "⚠️ **Scraper usage**: `/scrape <product name>`\n*Example*: `/scrape smartwatches`"
            else:
                st.write(f"🕵️ Connecting to Flipkart live web scraper to search for *\"{scrape_term}\"*...")
                try:
                    from src.scraper import scrape_flipkart_live, update_product_database_and_reindex
                    new_df = scrape_flipkart_live(scrape_term, limit=5)
                    if new_df.empty:
                        response_content = "⚠️ Scrape complete, but no products were found. Headless browser request may have been throttled."
                    else:
                        added = update_product_database_and_reindex(new_df)
                        response_content = (
                            f"✅ **Live Scraper Success!**\n\n"
                            f"Scraped and indexed {added} new products for *\"{scrape_term}\"* from live Flipkart search.\n\n"
                            f"They have been embedded in ChromaDB. You can now search or ask questions about them!"
                        )
                except Exception as e:
                    response_content = f"❌ **Scraper error**: {e}"
        
        # 2. SQL Override
        elif user_input.strip().startswith(("/search", "/sql")):
            route = "sql"
            parts = user_input.strip().split(maxsplit=1)
            sql_clause = parts[1] if len(parts) > 1 else ""
            
            if not sql_clause:
                response_content = "⚠️ **SQL Search usage**: `/search <sql condition>`\n*Example*: `/search price < 500`"
            else:
                res_df = search_products_sql(sql_clause)
                if 'error' in res_df.columns:
                    error_msg = res_df['error'].iloc[0]
                    response_content = (
                        f"🧭 *System Route: **SQL SEARCH***\n\n"
                        f"❌ **SQL Error:** Failed to parse condition.\n\n"
                        f"```sql\n{error_msg}\n```"
                    )
                elif res_df.empty:
                    response_content = f"🧭 *System Route: **SQL SEARCH***\n\n🔍 No products match your SQL criteria: `{sql_clause}`"
                else:
                    response_content = (
                        f"🧭 *System Route: **SQL SEARCH***\n\n"
                        f"📊 **SQL Search Results** (matching: `{sql_clause}`):\n\n"
                        f"{format_products_markdown(res_df)}"
                    )
                    
        # 3. Greeting check
        else:
            clean_input = user_input.strip().lower().translate(str.maketrans('', '', '?!.,:;()'))
            greetings = {"hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon"}
            list_catalog_words = {"product", "products", "profuct", "item", "items", "catalog", "catalogue"}
            
            if clean_input in greetings:
                response_content = (
                    "🧭 *System Route: **GREETING***\n\n"
                    "👋 **Hello! How can I help you today?**\n\n"
                    "I am your Flipkart virtual support assistant. Ask me questions about returns, payment options, or search for products!"
                )
            # Catalog listing shortcut
            elif clean_input in list_catalog_words or "show products" in clean_input or "list products" in clean_input or "all products" in clean_input:
                sample_df = get_product_df().head(5)
                response_content = (
                    "📋 **Flipkart Product Catalog (Showing first 5 sample items):**\n\n"
                    f"{format_products_markdown(sample_df)}"
                )
            else:
                # Run semantic-router classification
                route = route_query(user_input)
                
                # Execute logic based on classified route
                if route == "faq":
                    # Query ChromaDB FAQ collection
                    faq_matches = query_faqs(user_input, n_results=1)
                    
                    if not faq_matches:
                        response_content = (
                            f"🧭 *System Route: **FAQ (Vector Retrieval)***\n\n"
                            f"🤖 I classified this as FAQ, but no answers were retrieved."
                        )
                    else:
                        match = faq_matches[0]
                        # Query Groq LLM
                        conversational_reply = generate_conversational_faq_answer(
                            question=user_input,
                            matched_q=match['question'],
                            matched_a=match['answer']
                        )
                        response_content = (
                            f"🧭 *System Route: **FAQ (Conversational LLM response)***\n\n"
                            f"{conversational_reply}\n\n"
                            f"*(Vector similarity distance: `{match['distance']:.4f}`)*"
                        )
                        
                elif route == "product_search":
                    # Extract metadata filters (price bounds, brand bounds)
                    constraints = extract_constraints(user_input)
                    
                    # Query ChromaDB Products collection with hybrid constraints
                    prod_matches = query_products(user_input, n_results=5, where=constraints)
                    
                    if not prod_matches:
                        response_content = (
                            f"🧭 *System Route: **PRODUCT_SEARCH (Vector Retrieval)***\n\n"
                            f"🔍 I classified this as product inquiry, but no matching products were found in vector space."
                        )
                    else:
                        # Query Groq LLM
                        conversational_reply = generate_conversational_product_answer(
                            query=user_input,
                            products_list=prod_matches
                        )
                        
                        trace_tag = f"PRODUCT_SEARCH (Hybrid Filter: {constraints})" if constraints else "PRODUCT_SEARCH"
                        
                        if conversational_reply is None:
                            # Fallback if API key not present
                            response_content = (
                                f"🧭 *System Route: **{trace_tag}***\n\n"
                                f"⚠️ **Groq API Key not configured in .env** (Showing raw database retrieval):\n\n"
                                f"{format_product_matches_markdown(prod_matches)}"
                            )
                        else:
                            response_content = (
                                f"🧭 *System Route: **{trace_tag}***\n\n"
                                f"{conversational_reply}"
                            )
                        
                else:  # fallback
                    response_content = (
                        f"🧭 *System Route: **FALLBACK (OUT OF SCOPE)***\n\n"
                        f"🤖 **[Out of Scope Query]**\n\n"
                        f"For security and order-specific support, please refer to our official help paths:\n"
                        f"- **Flipkart Mobile App**: Go to **Account** -> **Help Centre** to chat with our executive.\n"
                        f"- **Flipkart Website**: Visit **24x7 Customer Care** and select **Need Help** for live support."
                    )
                
        # Simulate word-by-word streaming typing effect
        typed_text = ""
        for word in response_content.split(" "):
            typed_text += word + " "
            message_placeholder.markdown(typed_text + "▌")
            time.sleep(0.02)
        message_placeholder.markdown(typed_text)
        
    # Save assistant response to session history
    st.session_state.messages.append({"role": "assistant", "content": response_content})
    st.rerun()
st.write("")
