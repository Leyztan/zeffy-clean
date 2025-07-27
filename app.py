from flask import Flask, request, jsonify, render_template_string
import os
from google.oauth2 import service_account
from zeffy_scraper import scrape_and_update

app = Flask(__name__)

# Credential fallback for local dev
CREDENTIALS_PATH = "/var/render/secrets/google-credentials.json"
if not os.path.exists(CREDENTIALS_PATH):
    CREDENTIALS_PATH = "/Users/ataya1/Downloads/zeffy-scraper/google-credentials.json"

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)

# 🧞 Genie-style UI HTML
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Zeffy Magic</title>
  <style>
    body {
      background-color: #000;
      color: #fff;
      font-family: 'Trebuchet MS', sans-serif;
      text-align: center;
      padding-top: 80px;
    }
    #spinner {
      margin: 40px auto;
      display: none;
    }
    .lds-ellipsis div {
      position: absolute;
      top: 8px;
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: orange;
      animation-timing-function: cubic-bezier(0, 1, 1, 0);
    }
    .lds-ellipsis {
      display: inline-block;
      position: relative;
      width: 80px;
      height: 40px;
    }
    .lds-ellipsis div:nth-child(1) {
      left: 8px;
      animation: lds-ellipsis1 0.6s infinite;
    }
    .lds-ellipsis div:nth-child(2) {
      left: 8px;
      animation: lds-ellipsis2 0.6s infinite;
    }
    .lds-ellipsis div:nth-child(3) {
      left: 32px;
      animation: lds-ellipsis2 0.6s infinite;
    }
    .lds-ellipsis div:nth-child(4) {
      left: 56px;
      animation: lds-ellipsis3 0.6s infinite;
    }
    @keyframes lds-ellipsis1 {
      0% { transform: scale(0); }
      100% { transform: scale(1); }
    }
    @keyframes lds-ellipsis2 {
      0% { transform: translateX(0); }
      100% { transform: translateX(24px); }
    }
    @keyframes lds-ellipsis3 {
      0% { transform: scale(1); }
      100% { transform: scale(0); }
    }
    button {
      font-size: 18px;
      padding: 12px 25px;
      background: orange;
      color: black;
      border: none;
      border-radius: 8px;
      cursor: pointer;
    }
    button:disabled {
      background: gray;
      cursor: not-allowed;
    }
  </style>
</head>
<body>
  <h1>🧞 Your wish is my command...</h1>
  <button id="runButton" onclick="startScraping()">Start Magic</button>
  <div id="spinner" class="lds-ellipsis"><div></div><div></div><div></div><div></div></div>
  <p id="statusText"></p>

  <audio id="genieSound" src="https://upload.wikimedia.org/wikipedia/commons/3/3b/Magicwand.wav"></audio>

  <script>
    function startScraping() {
      const button = document.getElementById('runButton');
      const spinner = document.getElementById('spinner');
      const statusText = document.getElementById('statusText');
      const sound = document.getElementById('genieSound');

      button.disabled = true;
      spinner.style.display = 'inline-block';
      statusText.textContent = "✨ Gathering applications... Please wait.";

      sound.play();

      fetch('/webhook', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
          spinner.style.display = 'none';
          statusText.textContent = "✅ All done! Applications loaded into the sheet.";
        })
        .catch(err => {
          spinner.style.display = 'none';
          statusText.textContent = "❌ Oops! Something went wrong.";
          console.error(err);
        });
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/webhook", methods=["POST"])
def webhook():
    print("🔔 Webhook received")
    try:
        scrape_and_update(creds)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
