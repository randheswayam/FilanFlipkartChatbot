Product
Project Name: Flipkart FAQ & Product Inquiry Chatbot

Platform: Streamlit web app for demo and internal prototype use, with future potential to plug into Flipkart help flows where users already access support via app and website help sections.

Problem
Users often need quick help for common questions such as order help, returns, delivery, payment issues, and basic product queries, and Flipkart already guides users through Help Centre and Support Assistant paths on app and web.

A small AI chatbot can reduce friction by answering frequent questions instantly and by routing unclear questions to the right help topic or human support path when needed.

Goal
Build a simple chatbot that:

Answers common e-commerce FAQs.

Responds to basic product inquiries from a small product dataset.

Uses semantic retrieval for better matching instead of only keyword search.

Runs as a lightweight Streamlit app using Groq for fast response generation.

Users
Shoppers who want fast answers without browsing many help pages.

Users comparing products or checking basic product details such as price, category, rating, and availability from the demo dataset.

Support teams or stakeholders who want a simple proof of concept before a larger deployment.

Scope
In scope
Chat interface built with Streamlit.

FAQ knowledge base stored in CSV or pandas DataFrame.

Product catalog stored in CSV and queried with pandas or pandasql.

Semantic intent routing using semantic-router[local].

Vector storage with ChromaDB and embeddings from Sentence_transformers.

LLM response generation with Groq API loaded through python-dotenv.

Fallback response that suggests Help Centre or support escalation for unsupported questions, matching Flipkart’s existing support flow.

Out of scope
Real order tracking integration.

Live payment, return, or refund actions.

Full multilingual support.

Voice input, image search, and advanced recommendation engine.

Features
Core features
FAQ bot
Answers questions on returns, cancellation, delivery, payments, account issues, and support steps using a small curated FAQ dataset aligned with common help topics.

Product inquiry bot
Answers simple product questions such as:

“Show me smartphones under ₹20,000.”

“What is the rating of product X?”

“Which laptop has 16 GB RAM?”

Intent routing
Routes queries into:

FAQ

Product search

Out-of-scope / fallback

Semantic retrieval
Retrieves the most relevant FAQ or product records using embeddings and ChromaDB so wording variations still work.

Fallback guidance
If confidence is low, the bot replies with a safe fallback and suggests official support paths such as Help Centre, Need Help, or agent escalation.

User flow
Main flow
User opens Streamlit chatbot.

User types a question.

Router classifies the query as FAQ, product inquiry, or fallback.

Relevant data is retrieved from FAQ store or product catalog.

Groq generates a short, clear answer grounded in retrieved content.

If no strong answer exists, chatbot shows fallback support guidance.

Example
User asks: “How can I contact support for my order?”

Bot answers with steps like going to Account → Help Centre in the app or 24×7 Customer Care on the website, then using Need Help and escalating to chat, call, or email if required.

Requirements
Functional
The system must support text chat input and response in Streamlit.

The system must load API keys from .env using python-dotenv.

The system must store and read FAQ and product data using pandas.

The system should support simple SQL-like product filtering with pandasql where useful.

The system must generate embeddings for FAQ and product text using Sentence Transformers.

The system must store embeddings and documents in ChromaDB.

The system must classify user intent using semantic-router local routing.

The system must use Groq to generate final natural-language responses.

The system must return a fallback response for unsupported or low-confidence queries.

Non-functional
Response time target should be under 3 seconds for most queries in the demo environment, which fits the lightweight Groq + Streamlit prototype goal.

The chatbot should be easy to run locally with a simple requirements.txt and .env setup.

The system should use only demo or public data and avoid storing sensitive personal order details in this small version.

Tech stack
Layer	Tool	Purpose
UI	Streamlit	Simple chatbot interface for rapid prototyping. 
Data handling	pandas	Read and process FAQ and product CSV files. 
Querying	pandasql	Run lightweight SQL-style queries on product data. 
Config	python-dotenv	Load Groq API key securely from .env. 
LLM	Groq	Fast answer generation. 
Routing	semantic-router[local]	Detect FAQ vs product vs fallback intent. 
Vector DB	chromadb	Store and retrieve semantic chunks. 
Embeddings	Sentence_transformers	Convert text into embeddings for retrieval. 
Data design
Minimal datasets
Keep just two small files:

faqs.csv with columns: id, question, answer, category

products.csv with columns: id, name, category, brand, price, rating, availability, description

Retrieval strategy
FAQ entries are embedded and stored in ChromaDB.

Product rows are converted into short text records and embedded too.

For structured queries like price filters, pandas or pandasql can be used before or after semantic retrieval.

Success metrics
MVP metrics
80% of test FAQ questions answered correctly from the prepared dataset.

75% of basic product queries return a relevant result from the sample catalog.

90% of unsupported queries receive a safe fallback instead of a misleading answer.

App runs locally with one command and no complex setup beyond API key and package install.

Milestones
Small plan
Day 1: Prepare faqs.csv and products.csv.

Day 2: Build Streamlit chat UI and .env config.

Day 3: Add intent routing and ChromaDB retrieval.

Day 4: Connect Groq response generation.

Day 5: Test common questions, fallback cases, and cleanup.

Acceptance criteria
User can ask at least 10 FAQ questions and get sensible answers from the stored FAQ set.

User can ask at least 10 product-related questions and receive matching product information from the sample dataset.

Unsupported questions trigger a fallback that points users toward official support channels instead of inventing answers.

The app runs locally with the listed Python libraries and .env configuration.

Suggested folder structure
bash
flipkart-chatbot/
├── app.py
├── .env
├── requirements.txt
├── data/
│   ├── faqs.csv
│   └── products.csv
├── src/
│   ├── router.py
│   ├── retriever.py
│   ├── llm.py
│   └── utils.py
Simple product statement
This project is a small AI-powered chatbot prototype for Flipkart that helps users with common FAQs and basic product inquiries through a Streamlit interface, using semantic routing, vector search, and Groq-based answer generation.