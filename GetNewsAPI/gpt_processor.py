import os
import requests
import json
from datetime import datetime
from db import get_db_connection
from config import OPENAI_API_KEY

def process_with_gpt(raw_article):
    """
    Call the OpenAI responses endpoint directly (via HTTP) to translate and rewrite selected fields
    of the crypto news article into Serbian.
    Only the following fields will be adjusted:
      - title
      - full_text (article content)
      - topics
      - sentiment
    The following fields remain unchanged: news_url, publish_date, source_name, tickers, and image_url.
    The publish_date for the processed article will be set to the current datetime.
    """
    prompt = f"""
    Please translate and rewrite the following crypto news article into Serbian.
    Adjust only the following fields: Title, Full Text, Topics, and Sentiment.
    Do not change the following details: news_url, publish_date, source_name, tickers, and image_url.
    
    Title: {raw_article.get('title')}
    
    Article: {raw_article.get('text', '')}
    
    Topics (comma-separated): {', '.join(raw_article.get('topics', []))}
    
    Sentiment (a numeric value, e.g., between -1 and 1): {raw_article.get('sentiment', 0)}
    """
    
    payload = {
        "model": "gpt-4o-2024-08-06",
        "input": [
            {"role": "system", "content": (
                "You are a professional news editor and translator specializing in crypto news. "
                "Translate and rewrite articles from English into Serbian, but only adjust the title, "
                "article content, topics, and sentiment. Do not modify the fields news_url, publish_date, "
                "source_name, tickers, and image_url."
            )},
            {"role": "user", "content": prompt}
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "serbian_adjusted_fields",
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "full_text": {"type": "string"},
                        "topics": {"type": "string"},
                        "sentiment": {"type": "number"}
                    },
                    "required": ["title", "full_text", "topics", "sentiment"],
                    "additionalProperties": False
                }
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.openai.com/v1/responses"
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        print("Error during GPT call:", response.text)
        processed_fields = {
            "title": raw_article.get("title"),
            "full_text": raw_article.get("text", ""),
            "topics": ', '.join(raw_article.get("topics", [])),
            "sentiment": raw_article.get("sentiment", 0)
        }
    else:
        result = response.json()
        try:
            processed_fields = json.loads(result["output"][0]["content"][0]["text"].strip())
        except Exception as e:
            print("Error parsing GPT output:", e)
            processed_fields = {
                "title": raw_article.get("title"),
                "full_text": raw_article.get("text", ""),
                "topics": ', '.join(raw_article.get("topics", [])),
                "sentiment": raw_article.get("sentiment", 0)
            }
    
    processed_article = {
        "news_url": raw_article.get("news_url"),
        "publish_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_name": raw_article.get("source_name", ""),
        "tickers": ', '.join(raw_article.get("tickers", [])),
        "image_url": raw_article.get("image_url", "")
    }
    processed_article.update(processed_fields)
    
    return processed_article

def store_serbian_news(article):
    """
    Store the GPT-processed (Serbian) article into the 'serbian_cryptonews' table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    insert_sql = '''
        INSERT IGNORE INTO serbian_cryptonews
        (news_url, title, full_text, publish_date, source_name, topics, sentiment, type, tickers, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    '''
    cursor.execute(insert_sql, (
        article.get('news_url'),
        article.get('title'),
        article.get('full_text'),
        article.get('publish_date'),
        article.get('source_name'),
        article.get('topics'),
        article.get('sentiment'),
        article.get('type', ''),
        article.get('tickers'),
        article.get('image_url')
    ))
    
    conn.commit()
    cursor.close()
    conn.close()

def process_news_with_gpt():
    """
    Process a batch of raw news articles (from 'cryptonewsapi') with GPT,
    then store the rewritten version in 'serbian_cryptonews'.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM cryptonewsapi ORDER BY publish_date DESC LIMIT 20;')
    raw_news = cursor.fetchall()
    cursor.close()
    conn.close()
    
    for item in raw_news:
        processed = process_with_gpt(item)
        if processed:
            store_serbian_news(processed)
