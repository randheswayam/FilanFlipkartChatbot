import os
from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder

# Global variables for caching singleton router
_router_instance = None

def get_router() -> RouteLayer:
    """Initializes and returns the cached RouteLayer instance (Singleton)."""
    global _router_instance
    if _router_instance is None:
        # 1. Define FAQ Utterances
        faq_route = Route(
            name="faq",
            utterances=[
                "What is the return policy of the products?",
                "Do I get discount with the HDFC credit card?",
                "How can I track my order?",
                "What payment methods are accepted?",
                "How long does it take to process a refund?",
                "Are there any ongoing sales or promotions?",
                "Can I cancel or modify my order after placing it?",
                "Do you offer international shipping?",
                "What should I do if I receive a damaged product?",
                "How do I use a promo code during checkout?",
                "how do I return my purchase?",
                "order status tracking link",
                "payment support options",
                "HDFC bank discount check",
                "process for refund",
                "cancel order guidelines",
                "international shipping fee",
                "support contact for damaged item",
                "apply coupon discount promo code"
            ]
        )
        
        # 2. Define Product Search Utterances
        product_route = Route(
            name="product_search",
            utterances=[
                "Show me sports shoes for women",
                "ALICE Running Shoes For Women",
                "find shoes under 1000 rupees",
                "Puma running sneakers",
                "Nike sports products",
                "shoes by Sparx",
                "sneakers for girls walking",
                "running shoes",
                "walking shoes for ladies",
                "brand Campus shoes price",
                "Vokline walking shoes",
                "lightweight comfort daily use shoes",
                "sports gym training shoes",
                "Fabbmate Memory Foam shoes",
                "are there any shoes under 500?",
                "show me sneakers"
            ]
        )
        
        # 3. Load Local HuggingFace Embedding Encoder
        # Uses sentence-transformers/all-MiniLM-L6-v2 by default
        encoder = HuggingFaceEncoder()
        
        # 4. Create Route Layer
        # Set the score threshold to 0.35 below which it routes to None
        _router_instance = RouteLayer(
            encoder=encoder, 
            routes=[faq_route, product_route]
        )
        _router_instance.score_threshold = 0.35
        
    return _router_instance

def route_query(query: str) -> str:
    """
    Routes a user query into: 'faq', 'product_search', or 'fallback'.
    Uses a similarity threshold of 0.35 configured on the RouteLayer.
    """
    router = get_router()
    try:
        # Route query
        result = router(query)
        if result and result.name:
            return result.name
        return "fallback"
    except Exception:
        # Fail gracefully to fallback
        return "fallback"
