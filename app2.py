import os
import csv
import requests
import ollama
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from recommendation import recommend_items, get_user_preferences


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
    
    prompt = f"Summarize this news article in 70 words: {content}"
    response = ollama.chat(model="phi:2.7b", messages=[{"role": "user", "content": prompt}])
    
    return response["message"]["content"]

def classify_category(article_title):
    categories = {
        "Politics", "Sports", "Tech", "Health", "Business", "Entertainment", "Science", "World", "Economy",
        "Finance", "Education", "Crime", "Law", "Military", "Environment", "Energy", "Startups", "AI",
        "Space", "Medicine", "Lifestyle", "Culture", "Travel", "Food", "Gaming", "Music", "Movies",
        "Television", "Fashion", "Social Media", "History", "Religion", "Other"
    }

    prompt = (
        f"Classify this news headline into one of these categories: {', '.join(categories)}.\n"
        "Return only ONE category as a single word from this list, without explanation or extra text.\n\n"
        f"Headline: {article_title}"
    )

    response = ollama.chat(model="phi:2.7b", messages=[{"role": "user", "content": prompt}])
    category = response["message"]["content"].strip().split()[0]  # Extract first word

    # Ensure valid category
    return category if category in categories else "Other"


# Log user interaction
def log_user_activity(user_id, article_title, category):
    if category == "Unknown" or not category:
        category = classify_category(article_title)  # Get category using Ollama
    
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([user_id, article_title, category])
        
def get_user_preferences(user_id):
    """Analyze user activity and find the most-read categories"""
    if not os.path.exists(CSV_FILE):
        return []

    df = pd.read_csv(CSV_FILE)
    user_data = df[df["user_id"] == user_id]

    if user_data.empty:
        return []  # No data for this user

    category_counts = user_data["category"].value_counts()
    top_categories = category_counts.index.tolist()[:3]  # Get top 3 categories

    return top_categories@app.route("/recommend", methods=["GET"])

def recommend_articles():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    recommendations = recommend_items(user_id)  # Call the function from recommendations.py
    
    return jsonify(recommendations)


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
    user_id = request.args.get("user_id", "anonymous")

    if user_id != "anonymous":
        top_categories = get_user_preferences(user_id)

        if top_categories:
            news_articles = []
            for category in top_categories:
                news_articles.extend(get_news(category))  # Fetch news for each category

            return jsonify(news_articles[:10])  # Show top 10 articles from preferred categories
    
    # Default to trending news if no user history
    return jsonify(get_news("general"))


@app.route("/summarize", methods=["POST"])
def fetch_summary():
    data = request.json
    article_content = data.get("content", "")
    user_id = data.get("user_id", "anonymous")
    article_title = data.get("article_title", "Unknown Title")
    category = data.get("category", "Unknown")

    if article_content:
        summary = summarize_article(article_content)
        
        # Log user activity with dynamic category classification
        log_user_activity(user_id, article_title, category)

        return jsonify({"summary": summary, "category": category}), 200

    return jsonify({"error": "No content provided"}), 400

@app.route("/click", methods=["POST"])
def track_click():
    data = request.json
    user_id = data.get("user_id")
    article_title = data.get("article_title")
    category = data.get("category", "Unknown")  # Default to Unknown
    
    # Log the interaction with dynamic category classification
    log_user_activity(user_id, article_title, category)

    return jsonify({"message": "User activity logged"}), 200

if __name__ == "__main__":
    print("Flask app is running at http://127.0.0.1:5000/")
    app.run(debug=True)
