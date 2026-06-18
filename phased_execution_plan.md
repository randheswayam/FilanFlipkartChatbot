# Phased Execution Plan: Flipkart FAQ & Product Inquiry Chatbot

This document details the phased implementation plan for the **Flipkart FAQ & Product Inquiry Chatbot**. The strategy focuses on incremental development. At the end of each session, the application will be in a **runnable state** that you can open, see, interact with, and verify before proceeding.

---

## Technical Stack Overview
- **UI**: Streamlit
- **Data Stores**: CSV files loaded via `pandas` (`faq_data.csv`, `ecommerce_data_final.csv`)
- **Querying**: `pandasql` (for SQL-like structured filters on price, rating, brand)
- **Vector DB**: `chromadb` (local instance)
- **Embeddings**: `sentence-transformers` (local model)
- **Intent Routing**: `semantic-router[local]` (local classification model)
- **LLM**: `groq` API (using `python-dotenv` for API key management)

---

## Phased Plan

### Phase 1: Streamlit Chat Interface & Brand Styling (UI Shell)
**Objective**: Build the visual framework of the chatbot with Flipkart-inspired styling and verify that the message loop works.

- **Tasks**:
  1. Set up the basic project structure:
     ```bash
     FilanFlipkartChatbot/
     ├── app.py
     ├── src/
     │   └── __init__.py
     └── data/
     ```
  2. Create a clean, responsive Streamlit chat interface in `app.py` using `st.chat_message` and `st.chat_input`.
  3. Apply custom CSS styles to match Flipkart’s corporate aesthetic (blue/yellow accents, clean modern chat bubbles, and an assistant avatar).
  4. Implement an "echo" or mock-response mechanism in `app.py` that immediately replies with a generic support greeting and echoes the user's text to verify the visual state.
- **Runnable State**: Run `streamlit run app.py` to open a web browser. You will see a fully styled chat interface. You can type messages and see them added to the thread with animated, styled response bubbles from the assistant.

---

### Phase 2: Data Loading & Keyword/Structured Search
**Objective**: Load the CSV datasets and allow the chatbot to search the catalog using keyword matching and basic SQL filters.

- **Tasks**:
  1. Create a data loader utility in `src/utils.py` to load:
     - `app/resources/faq_data.csv` (Columns: `question`, `answer`)
     - `app/resources/ecommerce_data_final.csv` (Columns: `product_link`, `title`, `brand`, `price`, `discount`, `avg_rating`, `total_ratings`)
  2. Implement a simple search function in `src/utils.py` using `pandas` and `pandasql` to query products based on brand keywords or basic price/rating criteria.
  3. Update `app.py` to intercept query patterns. If a query looks like a search command (e.g. starting with `/search` or featuring product keywords like "shoes" or "puma"), run the database query and display results in a neat markdown table or card block.
- **Runnable State**: Run `streamlit run app.py`. You can now search the product database. For example, typing `/search brand='Sparx'` or simply "shoes" will parse the query and display a formatted list of matching products with their prices and ratings.

---

### Phase 3: Semantic Intent Routing (semantic-router)
**Objective**: Integrate `semantic-router` to dynamically classify queries into FAQ, Product Search, or Fallback.

- **Tasks**:
  1. Create `src/router.py` using `semantic-router[local]`.
  2. Define three routes with distinct sample utterances:
     - `faq`: e.g., "Can I cancel my order?", "How to track shipping?", "What payment methods do you accept?"
     - `product_search`: e.g., "Show me running shoes", "laptops under 20000", "Nike sports items"
     - `fallback`: unrelated or out-of-scope inputs.
  3. Integrate the router into `app.py`. For every user message, classify the intent.
  4. Display the detected route in a small debug expander or badge on the UI (e.g., `[Route: FAQ]`) so the current classification can be verified visually.
- **Runnable State**: Run `streamlit run app.py`. When you type any question, the chatbot will display a badge showing how it classified your query:
  - "Do you accept HDFC card?" -> `[Route: FAQ]`
  - "Find me Puma shoes" -> `[Route: Product Search]`
  - "What is the capital of France?" -> `[Route: Fallback]`

---

### Phase 4: ChromaDB & Local Vector Retrieval
**Objective**: Set up ChromaDB to index the FAQs and products, enabling semantic search instead of simple keyword matching.

- **Tasks**:
  1. Create `src/retriever.py` to initialize a local, persistent ChromaDB client.
  2. Load a lightweight local embedding model (e.g., `all-MiniLM-L6-v2`) via `sentence-transformers`.
  3. Generate and store embeddings for:
     - The questions in `faq_data.csv`.
     - The product details in `ecommerce_data_final.csv` (combining title, brand, and description/metadata into text chunks).
  4. Implement semantic retrieval functions:
     - For FAQ: Retrieve the single closest matching FAQ answer.
     - For Product Search: Retrieve the top 3-5 candidate products matching the query.
  5. Connect the retriever to `app.py`. If a query is routed to `faq`, retrieve and output the exact CSV answer. If routed to `product_search`, display the top semantic matches.
- **Runnable State**: Run `streamlit run app.py`. You can now test semantic retrieval. Asking "Can I pay when it arrives?" (which doesn't match the exact words in `faq_data.csv`) will successfully retrieve the answer for "What payment methods are accepted?" from ChromaDB.

---

### Phase 5: Groq LLM & Conversational Fallback Guidance
**Objective**: Integrate the Groq LLM to generate natural, conversational responses based on the retrieved context, and finalize official support fallback routes.

- **Tasks**:
  1. Create `src/llm.py` to interface with the Groq API.
  2. Implement conversational prompting:
     - **FAQ Route**: Prompt the LLM to answer the user's question using only the retrieved FAQ text as context.
     - **Product Search Route**: Retrieve matching products (combining ChromaDB candidates and SQL price/rating filters if applicable) and prompt the LLM to format them in a friendly, conversational table/card format.
     - **Fallback/Low Confidence Route**: Return a standardized response recommending official support paths (Flipkart App -> Account -> Help Centre, or website 24x7 Customer Care).
  3. Set up the `.env` file to manage Groq API credentials.
- **Runnable State**: The completed, fully conversational chatbot app. Run `streamlit run app.py`. You can ask complex natural language questions. The assistant will retrieve database facts and write conversational, helpful responses. Unrelated or unsupported questions will trigger official Flipkart-aligned escalation steps.

---

## Verification Matrix

At each phase, use this table to verify the app status:

| Phase | Entry Point | Test Action | Expected Result |
| :--- | :--- | :--- | :--- |
| **1** | `app.py` | Type "hello" | UI displays "hello" and assistant echoes it back. |
| **2** | `app.py` | Type `shoes` | UI loads CSVs and displays a pandas-based list of matching shoes. |
| **3** | `app.py` | Type "How do I cancel?" | UI displays the active route badge: `[Route: FAQ]`. |
| **4** | `app.py` | Type "is cash accepted?" | App queries ChromaDB and returns the cash on delivery answer. |
| **5** | `app.py` | Ask "Do you have shoes under 800?" | Groq LLM generates a clean, conversational list of recommendations. |
