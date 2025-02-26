import os
import csv
import requests
import ollama
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests
from flask import Flask, jsonify, request, send_from_directory

@app.route("/")
def serve_index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['JSON_SORT_KEYS'] = False

NEWS_API_KEY = "f302623860014f70a9ce63000cec8be2"  # Replace with your key
CSV_FILE = "user_activity.csv"

# Initialize CSV if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "article_title", "category"])

# Fetch news articles
def get_news(category="general"):
    url = f"https://newsapi.org/v2/top-headlines?category={category}&country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    return response.json().get("articles", [])

# Summarize news article on demand
def summarize_article(content):
    if not content:
        return "No content available for summarization."
    
    prompt = f"Summarize this news article concisely: {content}"
    response = ollama.chat(model="tinyllama", messages=[{"role": "user", "content": prompt}])
    
    return response["message"]["content"]

# Log user interaction
def log_user_activity(user_id, article_title, category):
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([user_id, article_title, category])
        
def search_news(query):
    url = f"https://newsapi.org/v2/everything?q={query}&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    return response.json().get("articles", [])

@app.route("/search", methods=["GET"])
def fetch_search_results():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    news_articles = search_news(query)
    return jsonify(news_articles)

@app.route("/news", methods=["GET"])
def fetch_news():
    category = request.args.get("category", "general")
    news_articles = get_news(category)
    
    return jsonify(news_articles)

@app.route("/summarize", methods=["POST"])
def fetch_summary():
    data = request.json
    article_content = data.get("content", "")
    
    if article_content:
        summary = summarize_article(article_content)
        return jsonify({"summary": summary}), 200
    
    return jsonify({"error": "No content provided"}), 400

@app.route("/click", methods=["POST"])
def track_click():
    data = request.json
    user_id = data.get("user_id")
    article_title = data.get("article_title")
    category = data.get("category")
    
    if user_id and article_title and category:
        log_user_activity(user_id, article_title, category)
        return jsonify({"message": "User activity logged"}), 200
    
    return jsonify({"error": "Invalid data"}), 400

if __name__ == "__main__":
    print("Flask app is running at http://127.0.0.1:5000/")
    app.run(debug=True)