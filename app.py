
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

import datetime

def search_historical_news(query):
    """Fetch articles related to query from the last month."""
    last_month = (datetime.date.today() - datetime.timedelta(days=26)).strftime("%Y-%m-%d")
    url = f"https://newsapi.org/v2/everything?q={query}&from={last_month}&apiKey={NEWS_API_KEY}"
    print(url)
    
    response = requests.get(url).json()
    return response.get("articles", [])[:5]  # Get top 5 related articles

def summarize_historical_articles(articles):
    if not articles:
        return ""  # No historical data found

    historical_summary = []
    
    for article in articles:
        title = article.get("title", "Untitled")
        content = article.get("content", "")
        
        # Extract the first 100 words
        first_100_words = " ".join(content.split()[:100])

        # Append title + content snippet
        historical_summary.append(f"📰 {title}: {first_100_words}...")
    print(historical_summary)
    # Join all summaries
    return "\n\n".join(historical_summary)


from sklearn.feature_extraction.text import TfidfTransformer
import pandas as p

def analyze_user_preferences(user_id):
    try:
        df = pd.read_csv('user_activity.csv')

        if "user_id" not in df.columns or "category" not in df.columns:
            print("Error: CSV is missing required columns.")
            return []

        user_data = df[df["user_id"] == user_id]
        if user_data.empty:
            print("No data found for the user.")
            return []

        # Compute category frequency for each user
        category_counts = df.groupby(["user_id", "category"]).size().unstack(fill_value=0)

        # Apply TF-IDF transformation
        transformer = TfidfTransformer()
        tfidf_matrix = transformer.fit_transform(category_counts)

        # Get the row for the given user
        if user_id not in category_counts.index:
            return []

        user_tfidf_scores = tfidf_matrix[category_counts.index.get_loc(user_id)].toarray()[0]

        # Get top 3 categories for the user
        top_topics = category_counts.columns[user_tfidf_scores.argsort()[::-1][:3]].tolist()
        print("USER PREFERENCES ANALYZED")
        return top_topics
    except Exception as e:
        print(f"Error analyzing user preferences: {e}")
        return []


categories=analyze_user_preferences('user123')
print(categories)
# Fetch news articles
def get_news(category="general"):
    url = f"https://newsapi.org/v2/top-headlines?category={category}&country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    return response.json().get("articles", [])

@app.route("/get_rnews", methods=["GET"])
def get_rnews():
    categories = request.args.get("categories", "").split(",")
    all_articles = []

    for category in categories:
        category = category.strip().lower()  # Normalize category format
        url = f"https://newsapi.org/v2/top-headlines?category={category}&country=us&pageSize=10&apiKey={NEWS_API_KEY}"
        
        print(f"Fetching: {url}")  # Debugging line
        response = requests.get(url).json()

        if "articles" in response:
            articles = response["articles"][:10]  # ✅ Limit to 10 articles
            all_articles.extend(articles)
        else:
            print(f"No articles found for {category}")  # Debugging line

    print(f"Total Articles Collected: {len(all_articles)}")  # Debugging line
    return jsonify({"articles": all_articles})

# Summarize news article on demand

def summarize_article(content, historical_articles, model="tinyllama"):
    """Summarize an article with historical context in under 100 words."""
    prompt = (
        f"Create a very short news summary (under 100 words) combining:\n"
        f"1. Current event: {content[:300]}\n"
        f"2. Relevant history: {historical_articles[:300]}\n"
        "Just write the summary with no extra text."
    )

    response = ollama.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": prompt
        }],
        options={"temperature": 0.3}
    )

    return response["message"]["content"]


import ollama
def classify_category(content):
    categories = {
        "Politics", "Sports", "Tech", "Health", "Business", "Entertainment", "Science",
        "World", "Economy", "Finance", "Education", "Crime", "Law", "Military",
        "Environment", "Energy", "Startups", "AI", "Space", "Medicine", "Lifestyle",
        "Culture", "Travel", "Food", "Gaming", "Music", "Movies", "Television",
        "Fashion", "Social Media", "History", "Religion"
    }

    prompt = (
        f"Classify this news headline into one of these categories: {', '.join(categories)}.\n"
        "Return only one category as output without explanation\n\n"
        f"Headline: {content}"
    )

    response = ollama.chat(model="phi:2.7b", messages=[{"role": "user", "content": prompt}])
    
    # Get first word only and clean it
    raw_output = response["message"]["content"].strip()
    first_word = raw_output.split()[0] if raw_output else ""
    first_word = ''.join([c for c in first_word if c.isalpha()])  

    return raw_output

def analyze_user_preferences(user_id):
    """Reads CSV and prints the most-read topics by the user"""
    if not os.path.exists(CSV_FILE):
        print("No user activity found.")
        return

    df = pd.read_csv(CSV_FILE)

    if "category" not in df.columns:
        print("Error: 'category' column missing in CSV")
        return

    user_data = df[df["user_id"] == user_id]

    if user_data.empty:
        print(f"No activity found for user: {user_id}")
        return 0

    # Count category occurrences
    category_counts = user_data["category"].value_counts()
    top_categories = category_counts.index.tolist()

    #print(f"Most read topics for user {user_id}: {top_categories[:3]}")
    return(top_categories)

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


@app.route("/analyze_user_preferences", methods=["GET"])
def analyze_user_preferences_endpoint():
    user_id = request.args.get("user_id")
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    topics = analyze_user_preferences(user_id)
    
    return jsonify({"topics": topics})

@app.route("/recommend", methods=["GET"])
def recommend_articles():
    user_id = request.args.get("user_id")
    topics = request.args.get("topics")  # Optional filter

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    recommendations = recommend_items(user_id, topics)  # Pass topics to recommendation function

    return jsonify({"recommendations": recommendations})


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
    try:
        data = request.json
        article_content = data.get("content", "")
        user_id = data.get("user_id", "anonymous")
        article_title = data.get("article_title")
        model = data.get("model", "tinyllama")  # 🧠 New: Allow model selection from frontend

        category = classify_category(article_title)
        print("\n🟡 [Summarization Request Received]")
        print(f"🔹 User: {user_id}")
        print(f"🔹 Title: {article_title}")
        print(f"🔹 Category: {category}")
        print(f"🧠 Model: {model}")
        print(f"📌 Content (first 200 chars): {article_content[:200]}...\n")

        if not article_content:
            print("❌ No content provided!\n")
            return jsonify({"error": "No content provided"}), 400

        # Extract first 6 words of the title for historical search
        search_query = " ".join(article_title.split()[:6])
        print(f"🔍 Searching for historical context using query: '{search_query}'")

        # Fetch historical articles
        historical_articles = search_historical_news(search_query)
        print(f"📂 Found {len(historical_articles)} historical articles\n")

        if historical_articles:
            historical_summary = summarize_historical_articles(historical_articles)
            print("✅ Historical Context Summary Generated:")
            print(historical_summary[:300] + "...\n")
        else:
            historical_summary = ""
            print("⚠️ No relevant historical articles found. Proceeding with current article only.\n")

        # 🧠 Use selected model for summarization
        summary = summarize_article(article_content, historical_summary, model=model)
        print("✅ Final Summary Generated:")
        print(summary + "\n")

        # Log user activity
        log_user_activity(user_id, article_title, category)

        return jsonify({"summary": summary, "category": category}), 200

    except Exception as e:
        print(f"❌ Summarization Error: {str(e)}\n")
        return jsonify({"error": "Summarization failed"}), 500



@app.route("/click", methods=["POST"])
def track_click():
    data = request.json
    user_id = data.get("user_id")
    article_title = data.get("article_title")
    category = classify_category(article_title)  # Default to Unknown
    
    # Log the interaction with dynamic category classification
    log_user_activity(user_id, article_title, category)

    return jsonify({"message": "User activity logged"}), 200

if __name__ == "__main__":
    analyze_user_preferences('user123')
    print("Flask app is running at http://127.0.0.1:5000/")
    app.run(debug=True)
