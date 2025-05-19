import tweepy
import os
from dotenv import load_dotenv
import datetime
import asyncio
import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import re
from threading import Thread
from collections import deque

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load .env file
env_path = '.env'
if not os.path.exists(env_path):
    with open(env_path, 'w') as f:
        f.write(
            'TWITTER_BEARER_TOKEN=your_twitter_bearer_token\n'
        )
    logging.info(f"Created .env file at {env_path}. Please update it with valid credentials.")

load_dotenv(env_path)
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

if not TWITTER_BEARER_TOKEN:
    logging.error("Missing TWITTER_BEARER_TOKEN. Check .env file.")
    exit(1)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Log static folder path for debugging
logging.info(f"Static folder path: {os.path.abspath(app.static_folder)}")

# Store tweets in memory (max 100 tweets to prevent memory issues)
tweets_storage = deque(maxlen=100)
user_cache = {}

# Polling function for recent tweets
async def poll_tweets(client):
    query = "@launchcoin"
    last_tweet_id = None
    retry_delay = 5
    
    while True:
        try:
            start_time = datetime.datetime.now()
            response = client.search_recent_tweets(
                query=query,
                tweet_fields=['created_at', 'author_id', 'text'],
                user_fields=['name', 'username', 'verified', 'public_metrics', 'profile_image_url', 'description', 'verified_type'],
                expansions=['author_id'],
                since_id=last_tweet_id,
                max_results=10
            )
            end_time = datetime.datetime.now()
            logging.info(f"API response time: {(end_time - start_time).total_seconds()} seconds")
            
            if not response.data:
                logging.info("No new tweets found")
                await asyncio.sleep(retry_delay)
                continue

            logging.info(f"Found {len(response.data)} tweets in response")
            last_tweet_id = response.meta.get('newest_id')
            logging.info(f"Updated last_tweet_id: {last_tweet_id}")

            current_time = datetime.datetime.now(datetime.timezone.utc)
            for tweet in response.data:
                time_diff = (current_time - tweet.created_at).total_seconds()
                if time_diff > 172800:
                    logging.info(f"Skipped tweet ID {tweet.id}: Too old ({time_diff} seconds)")
                    continue

                symbol_match = re.search(r'@launchcoin.*?\s\$(\S+)\s*\+(.+)', tweet.text.lower())
                if not symbol_match:
                    logging.info(f"Skipped tweet ID {tweet.id}: No @launchcoin $ticker +name pattern (text: {tweet.text})")
                    continue

                user = next((u for u in response.includes.get('users', []) if u.id == tweet.author_id), None)
                if not user:
                    logging.info(f"Skipped tweet ID {tweet.id}: No user data")
                    continue

                user_cache[tweet.author_id] = user
                symbol = symbol_match.group(1).upper()
                additional_text = symbol_match.group(2).strip()

                tweet_data = {
                    'id': str(tweet.id),
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat(),
                    'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                    'user': {
                        'username': user.username,
                        'name': user.name,
                        'profile_image_url': user.profile_image_url or '',
                        'followers_count': user.public_metrics['followers_count'],
                        'description': user.description or 'No bio available',
                        'verified': getattr(user, 'verified', False)
                    },
                    'symbol': symbol,
                    'additional_text': additional_text
                }
                tweets_storage.append(tweet_data)
                logging.info(f"Stored tweet ID {tweet.id}, symbol: {symbol}, additional_text: {additional_text}")

            await asyncio.sleep(retry_delay)

        except tweepy.TweepyException as e:
            logging.error(f"Error polling tweets: {e}")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            await asyncio.sleep(retry_delay)

# Start polling in a separate thread
def start_polling():
    logging.info("Starting polling thread")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN, wait_on_rate_limit=True)
    loop.run_until_complete(poll_tweets(client))

# Log all requests for debugging
@app.before_request
def log_request():
    logging.info(f"Request: {request.method} {request.path}")

# API endpoint to get tweets
@app.route('/api/tweets', methods=['GET'])
def get_tweets():
    logging.info("Serving /api/tweets")
    return jsonify(list(tweets_storage))

# Serve index.html from static folder
@app.route('/')
def serve_frontend():
    try:
        index_path = os.path.join(app.static_folder, 'index.html')
        if not os.path.exists(index_path):
            logging.error(f"index.html not found at {index_path}")
            return "Error: index.html not found in static folder", 404
        logging.info(f"Serving index.html from {index_path}")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logging.error(f"Error serving index.html: {e}")
        return f"Error serving page: {str(e)}", 500

# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    logging.error(f"404 error for {request.path}: {str(e)}")
    return f"Page not found: {request.path}. Check if resource exists.", 404

# Start Flask and polling
if __name__ == '__main__':
    polling_thread = Thread(target=start_polling, daemon=True)
    polling_thread.start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))