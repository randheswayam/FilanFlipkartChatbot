import os
from groq import Groq
from dotenv import load_dotenv

# Cache client and discovered model
_client = None
_active_model = None

def get_groq_client() -> Groq:
    """Initializes and returns the cached Groq client if the API key is present."""
    global _client
    if _client is None:
        # Dynamically reload environment variables
        load_dotenv(override=True)
        api_key = os.environ.get("GROQ_API_KEY")
        
        if not api_key:
            return None
            
        # Clean API key
        api_key = api_key.strip().strip("'\"")
        
        if "your_groq_api_key" in api_key or not api_key:
            return None
            
        try:
            _client = Groq(api_key=api_key)
        except Exception:
            return None
            
    return _client

def get_best_model(client: Groq) -> str:
    """
    Queries the Groq API to discover active models for the API key.
    Prioritizes Llama 3.3 70B, Llama 3.1 8B, and Gemma 2.
    """
    global _active_model
    if _active_model is not None:
        return _active_model
        
    try:
        models_data = client.models.list().data
        model_ids = [m.id for m in models_data]
        
        # Prioritized list of active text models
        priorities = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "llama-3.2-3b-preview",
            "llama-3.2-1b-preview"
        ]
        
        for p in priorities:
            if p in model_ids:
                _active_model = p
                return _active_model
                
        # Filter out audio/vision models and pick first text model
        text_models = [
            m_id for m_id in model_ids 
            if not any(x in m_id.lower() for x in ["whisper", "vision", "audio", "guard"])
        ]
        if text_models:
            _active_model = text_models[0]
            return _active_model
            
    except Exception:
        pass
        
    # Default fallback if listing fails
    return "llama-3.1-8b-instant"

def generate_conversational_faq_answer(question: str, matched_q: str, matched_a: str) -> str:
    """
    Prompts the Groq LLM to rewrite the FAQ answer into a friendly conversational response,
    grounded strictly in the matching CSV record.
    """
    client = get_groq_client()
    if not client:
        return (
            "⚠️ **Groq API Key not configured in .env** (Showing direct CSV database result):\n\n"
            f"**Q**: {matched_q}\n\n"
            f"**A**: {matched_a}"
        )
        
    system_prompt = (
        "You are a friendly, helpful Flipkart Customer Support virtual assistant. "
        "Your task is to answer the user's question using ONLY the provided FAQ context. "
        "Keep your answer short, conversational, and direct (maximum 3 sentences). "
        "Do not invent facts or mention rules not explicitly stated in the context. "
        "If the question cannot be answered using the context, state that you can't help with that "
        "and suggest checking the official Help Centre."
    )
    
    user_prompt = (
        f"FAQ Context:\n"
        f"Question in DB: {matched_q}\n"
        f"Answer in DB: {matched_a}\n\n"
        f"User Question: {question}"
    )
    
    try:
        # Detect model dynamically
        model = get_best_model(client)
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            temperature=0.1,
            max_tokens=200
        )
        return completion.choices[0].message.content
    except Exception as e:
        # Check specifically for authentication error
        err_msg = str(e)
        if "API key" in err_msg or "unauthorized" in err_msg.lower() or "401" in err_msg:
            return (
                "❌ **Groq Authentication Error**: The API Key set in `.env` is invalid or inactive.\n"
                "Please verify your `GROQ_API_KEY` at https://console.groq.com/keys and check your `.env` settings.\n\n"
                f"**Database Match**:\n**Q**: {matched_q}\n**A**: {matched_a}"
            )
        return (
            f"⚠️ **Groq API Error** (Model: {model}): {err_msg}\n\n"
            f"**CSV Database Answer**:\n"
            f"**Q**: {matched_q}\n"
            f"**A**: {matched_a}"
        )

def generate_conversational_product_answer(query: str, products_list: list) -> str:
    """
    Prompts the Groq LLM to format the matched product catalog details into a helpful,
    conversational recommendation table and response.
    """
    client = get_groq_client()
    if not client:
        return None
        
    system_prompt = (
        "You are a helpful shopping assistant for Flipkart. Your task is to recommend products to the user "
        "based on their query and the retrieved database records. "
        "Write a friendly, brief response (under 2 sentences) introducing the recommendations, "
        "followed by a clean, formatted markdown table containing the matching products. "
        "Keep the table columns to: Product Title, Brand, Price, Rating, Link. "
        "Ground all information (title, price, ratings, links) strictly in the provided records. "
        "If a list of products is provided, do not add products that are not in the list."
    )
    
    context = ""
    for i, p in enumerate(products_list):
        context += (
            f"Product {i+1}:\n"
            f"Title: {p['title']}\n"
            f"Brand: {p['brand']}\n"
            f"Price: Rs {p['price']}\n"
            f"Rating: {p['avg_rating']} stars\n"
            f"Link: {p['product_link']}\n\n"
        )
        
    user_prompt = (
        f"Retrieved Product Catalog Records:\n{context}\n"
        f"User Query: {query}"
    )
    
    try:
        # Detect model dynamically
        model = get_best_model(client)
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            temperature=0.2,
            max_tokens=500
        )
        return completion.choices[0].message.content
    except Exception as e:
        err_msg = str(e)
        if "API key" in err_msg or "unauthorized" in err_msg.lower() or "401" in err_msg:
            return (
                "❌ **Groq Authentication Error**: The API Key set in `.env` is invalid.\n"
                "Please verify your `GROQ_API_KEY`."
            )
        return f"⚠️ **Groq API Error** (Model: {model}): {err_msg}"
