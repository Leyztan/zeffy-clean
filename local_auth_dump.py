# local_auth_dump.py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.zeffy.com/login")
    
    input("🧑‍💻 Log in manually, then press Enter here...")

    context.storage_state(path="auth_state.json")
    print("✅ Session saved to auth_state.json")
    browser.close()
