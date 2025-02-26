from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

NEWS_API_KEY = "AIzaSyCihzPTt2ZC0iVQarAePfI6HlZPWxWjj_s"
NEWS_API_URL = "https://newsapi.org/v2/everything"

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/get_news', methods=['GET'])
def get_news():
    query = request.args.get('query', 'technology')
    response = requests.get(NEWS_API_URL, params={
        'q': query,
        'apiKey': NEWS_API_KEY,
        'language': 'en',
        'sortBy': 'publishedAt'
    })
    data = response.json()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)

hi nigga