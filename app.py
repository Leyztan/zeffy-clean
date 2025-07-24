from flask import Flask, request, abort
import subprocess
import threading

app = Flask(__name__)
SECRET_KEY = "my-secret-key"  # Use this to protect against random access

@app.route("/run", methods=["POST"])
def run_scraper():
    if request.headers.get("X-Secret-Key") != SECRET_KEY:
        abort(403)

    def run():
        subprocess.run(["python3", "zeffy_scraper.py"])
    threading.Thread(target=run).start()
    return "✅ Zeffy scraper triggered!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)