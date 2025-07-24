from flask import Flask, request, jsonify
import os
from google.oauth2 import service_account

from zeffy_scraper import scrape_and_update

app = Flask(__name__)

# Load credentials
CREDENTIALS_PATH = "/var/render/secrets/google-credentials.json"
if not os.path.exists(CREDENTIALS_PATH):
    CREDENTIALS_PATH = "/Users/ataya1/Downloads/zeffy-scraper/google-credentials.json"

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)

@app.route("/")
def index():
    return "✅ Zeffy listener is live", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("🔔 Webhook received from Zapier")

    try:
        scrape_and_update()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # <- ✅ dynamic port for Render
    app.run(host="0.0.0.0", port=port)
