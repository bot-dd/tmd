import re
import requests
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

TMDB_API_KEY = "252ce4f9b28effb7b4e67d41bfedc51d"  # 🔐 Replace with your TMDB key

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
TMDB_MOVIE_IMAGES_URL = "https://api.themoviedb.org/3/movie/{id}/images"
JUSTWATCH_API_URL = "https://apis.justwatch.com/content/titles/en_IN/popular"


def clean_movie_query(raw_text):
    text = raw_text.lower()

    # Remove URLs and Telegram usernames
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'@\w+', '', text)

    # Replace dots and underscores with spaces
    text = text.replace('.', ' ').replace('_', ' ')

    # Remove file extensions
    text = re.sub(r'\.(mkv|mp4|avi|webm)$', '', text)

    # Remove known tags, encoders, resolutions, etc.
    text = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', text)
    text = re.sub(
        r'(?i)\b(WEB[-_. ]?DL|WEBRip|HDRip|BluRay|DVDRip|x264|x265|HEVC|AAC|DDP?|ESub|NF|AMZN|HD|HQ|4K|1080p|720p|2160p|480p|10bit|8bit|Dual Audio|UNCUT|MULTI|ESubs?|AVC|AC3|DD5\.1|H\.264|Hindi|Malayalam|Kannada|Tamil|Telugu|Eng|Subs?|GB|MB|YTS|RARBG|SRT|EVO|FULLMOVIE|FULL MOVIE|FULLHD|CAM|DVDSCR|WEBRIP|BRRIP|MOVIE|ESUB|ESUBS)\b',
        '',
        text,
    )

    # Normalize spaces and special characters
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # Capitalize for better TMDB match
    return ' '.join(word.capitalize() for word in text.split())


def extract_year_from_query(query):
    year_match = re.search(r'(19|20)\d{2}', query)
    return year_match.group(0) if year_match else None


def get_movie_id(query):
    name = clean_movie_query(query)
    year = extract_year_from_query(query)

    params = {
        "api_key": TMDB_API_KEY,
        "query": name
    }
    if year:
        params["year"] = year

    response = requests.get(TMDB_SEARCH_URL, params=params)
    data = response.json()
    if data.get("results"):
        return data["results"][0].get("id")
    return None


def get_tmdb_posters(movie_id):
    url = TMDB_MOVIE_IMAGES_URL.format(id=movie_id)
    response = requests.get(url, params={"api_key": TMDB_API_KEY})
    data = response.json()
    return [f"{TMDB_IMAGE_BASE}{b['file_path']}" for b in data.get("backdrops", [])]


def get_ott_posters(query):
    headers = {"User-Agent": "JustWatch client/1.0"}
    payload = {
        "query": clean_movie_query(query),
        "page_size": 1
    }

    posters = []
    try:
        response = requests.post(JUSTWATCH_API_URL, json=payload, headers=headers)
        data = response.json()
        if data.get("items"):
            offers = data["items"][0].get("offers", [])
            for offer in offers:
                if offer.get("monetization_type") == "flatrate":
                    url = f"https://images.justwatch.com{offer['urls']['standard_web']}/s332"
                    posters.append(url)
    except:
        pass
    return posters


@app.route('/api/posters', methods=['GET'])
def get_all_posters():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Missing query parameter"}), 400

    movie_id = get_movie_id(query)
    if not movie_id:
        return jsonify({"error": "Movie not found in TMDB"}), 404

    tmdb_posters = get_tmdb_posters(movie_id)
    ott_posters = get_ott_posters(query)

    all_posters = tmdb_posters + ott_posters
    result = {f"poster{i+1}": url for i, url in enumerate(all_posters)}

    return jsonify(result)


# ✅ Heroku-safe port bind fix
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
