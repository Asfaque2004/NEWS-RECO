import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import numpy as np

CSV_FILE = "user_activity.csv"  # User interaction log

def load_user_activity():
    """Load user activity from CSV."""
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=["user_id", "article_title", "category"])
    
    return pd.read_csv(CSV_FILE)

def extract_keywords(titles, top_n=5):
    """Extract important keywords from article titles using TF-IDF."""
    if len(titles) == 0:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=top_n)
    tfidf_matrix = vectorizer.fit_transform(titles)
    
    keywords = vectorizer.get_feature_names_out()
    return keywords.tolist()

def get_user_preferences(user_id):
    """Analyze user activity and find the most-read categories"""
    df = load_user_activity()

    if df.empty or user_id not in df["user_id"].values:
        return []  # No data for this user

    user_data = df[df["user_id"] == user_id]
    category_counts = user_data["category"].value_counts()
    top_categories = category_counts.index.tolist()[:3]  # Get top 3 categories

    return top_categories

def build_similarity_matrix(df):
    """Compute item similarity using TF-IDF on category + keywords."""
    if df.empty:
        return None, []

    df["combined_text"] = df["category"] + " " + df["article_title"]
    
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(df["combined_text"])
    
    similarity_matrix = cosine_similarity(tfidf_matrix)
    return similarity_matrix, df["article_title"].tolist()

def recommend_items(user_id, top_n=5):
    df = load_user_activity()
    
    if df.empty or user_id not in df["user_id"].values:
        return {"message": "No user activity found. Showing trending articles."}

    user_data = df[df["user_id"] == user_id]
    user_categories = user_data["category"].value_counts().index.tolist()[:3]  # Top 3 categories

    # Filter articles matching user's top categories
    relevant_articles = df[df["category"].isin(user_categories)]
    
    if relevant_articles.empty:
        return {"message": "No matching articles for your interests."}

    recommended_articles = relevant_articles["article_title"].sample(n=min(top_n, len(relevant_articles))).tolist()
    
    # Extract Keywords from User's Read Articles
    keywords = extract_keywords(user_data["article_title"].tolist(), top_n=5)

    return {
        "recommended_articles": recommended_articles,
        "top_categories": user_categories,
        "keywords": keywords  # ADDING THIS BACK
    }
# Call the recommendation function
user_id = "user123"  # Replace with an actual user ID from your CSV
result = recommend_items(user_id)

# Print results
if "message" in result:
    print("🔹", result["message"])
else:
    print("🔹 Recommended Articles:", result["recommended_articles"])
    print("🔹 User Interests (Categories):", result["top_categories"])
    print("🔹 Extracted Keywords:", result["keywords"])

