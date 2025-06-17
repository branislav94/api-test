import requests
import json
import base64
from datetime import datetime
from config import WP_API_URL, WP_USERNAME, WP_APP_PASSWORD
from config import DB_CONFIG  # For retrieving raw news
import mysql.connector

def slugify(text):
    import re
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def mark_news_as_published(news_url):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    update_sql = "UPDATE serbian_cryptonews SET published = 1 WHERE news_url = %s"
    cursor.execute(update_sql, (news_url,))
    conn.commit()
    cursor.close()
    conn.close()

def publish_news_to_wp():
    """
    Fetch processed news from `serbian_cryptonews` that haven't been published,
    and then publish them as native WordPress posts via the REST API.
    """
    # Retrieve raw processed news from your crypto database
    conn_raw = mysql.connector.connect(**DB_CONFIG)
    cursor_raw = conn_raw.cursor(dictionary=True)
    cursor_raw.execute("SELECT * FROM serbian_cryptonews WHERE published = 0 ORDER BY insertDate DESC LIMIT 5;")
    news_items = cursor_raw.fetchall()
    cursor_raw.close()
    conn_raw.close()
    
    if not news_items:
        print("No new news items to publish.")
        return

    # Build Basic Auth header for WordPress REST API
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode("utf-8")
    headers = {
        "Authorization": "Basic " + token,
        "Content-Type": "application/json"
    }

    for item in news_items:
        # Prepare post data (adjust as needed)
        post_data = {
            "title": item["title"],
            "content": item["full_text"],
            "status": "publish",
            "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),  # ISO 8601 format
            # Optionally, add excerpt or custom fields here if needed.
            "slug": slugify(item["title"])
        }
        
        # Send POST request to create a new post in WordPress
        response = requests.post(WP_API_URL + "/wp-json/wp/v2/posts",
                                 headers=headers,
                                 data=json.dumps(post_data))
        if response.status_code == 201:
            wp_post = response.json()
            print(f"Published news item as WordPress post ID: {wp_post['id']}")
            # Mark the news item as published in your raw table
            mark_news_as_published(item["news_url"])
        else:
            print("Error publishing post:", response.text)

if __name__ == '__main__':
    publish_news_to_wp()
