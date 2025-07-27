from playwright.sync_api import sync_playwright
import psutil
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from difflib import get_close_matches
import traceback
import time
import requests
import json
import os
from datetime import datetime
from google.oauth2 import service_account

SPREADSHEET_ID = "1aYtJlAx4VnO1aCAalzAEwRdilok-uoWgltoEJcK1pOc"
TAB_NAME = "Zeffy_Scraped_Results"
CAMPAIGN_URL = "https://www.zeffy.com/en-US/o/fundraising/campaigns/hub?formId=02136a57-f7b9-4023-a489-9c0136a4da37&tab=payment"
EMAIL = "atayan@elevationproject.com"
PASSWORD = "zobfo5-tofdEf-fykbys"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxog4Wq0jjvR6fDL-3O4xmZ2iAlAECu0j38Ri2Ta9bZZqptnHRQAGJFmBJosJA5JsDQxw/exec"

COLUMNS = [
    "Ticket Tier", "Name", "Phone number (WhatsApp preferred)", "Email", "Date of Birth", "Gender",
    "City, State, Country (in this format please):", "What’s your current profession and professional background?",
    "How did you hear about this retreat?",
    "Have you done any online Elevation programs or live events? (Please specify)",
    "Share about your connection/affiliation with Torah, Judaism, or Jewish teachings (min. 50 words)",
    "Who is your Rabbi, Rebbetzin, or mentor if any?", "What community are you part of, if any?",
    "Reference (name + contact info from mentor, rabbi, rebbetzin, or someone who knows you well):",
    "Have you had any previous experience in meditation or personal transformation work? If so, please specify what kind, where and how it was for you. If not, why this and now? (min. 50 words)",
    "What’s your main goal for this retreat?",
    "What, if any, are your biggest concerns in attending this event (physically, emotionally, spiritually)?",
    "In order to help us best support you, please specify if you're currently suffering from, or do you have a history of, any psychological or psychiatric challenges?",
    "Have you been specifically diagnoses with any of the following:",
    "If you are now, or have recently faced challenges like these, are you willing to provide a letter from a therapist or psychiatrist agreeing that this program is advisable for you? (we may or may not require this).",
    "Have you experienced or been diagnosed with anxiety, depression or PTSD? If so, please elaborate.",
    "Are you currently taking any psychiatric medication for them? If so, what type and for how long?",
    "Have you experienced suicidal thoughts or attempts at any time in your life? If so, please elaborate",
    "In the past 1-3 years, have you had any major traumatic events, or big or sudden life changes? If so, please elaborate.",
    "Are you holding any minor or major trauma? (events like major job changes, divorce, are also helpful for us to know). If so, please elaborate.",
    "Are you currently suffering from, or have history of, any other health conditions? If so, please specify.",
    "Are you currently taking any other medications for mental or physical health? (please consider any medications you have taken long term). If so, please specify.",
    "Have you undergone any surgeries in the past year? If so, please specify.",
    "Please provide the name, phone number, and email of your current or previous therapist and/or psychiatrist (if applicable).",
    "Do you have any allergies or dietary restrictions? If so, please specify.",
    "For General Admission Double Occupancy Tickets: If you’re attending with a specific person (same gender or a partner), please write their full name here and make sure they list your name in their application as well. Otherwise, we cannot guarantee that you'll be accommodated together. If you’re attending alone, our carefully curated process will pair you with a like-minded individual to ensure the best possible experience.",
    "Checkout note: at the final step of payment, Zeffy automatically prompts you to add a donation—this goes to Zeffy, not Elevation. To skip it, select “Other” and type $0. Check here to confirm you’ve read and are aware of this.",
    "Payment Amount"
]

KNOWN_TIERS = {
    "General Admission-Single Occupancy",
    "General Admission Double Occupancy",
    "VIP",
    "VIP+ PLUS",
    "Basic Access: No Accommodation",
    "Testing",
    "TEST"
}


def log_to_zeffy_logs(client, name, email, reason):
    try:
        log_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Zeffy_Logs")
    except Exception:
        log_sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(title="Zeffy_Logs", rows="100", cols="5")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_row = [timestamp, "Skipped", name, email, reason]
    log_sheet.append_row(log_row, value_input_option="RAW")


def login(page):
    print("🔐 Navigating to login page...")
    try:
        page.goto("https://www.zeffy.com/login", timeout=60000)
        print("📨 Filling in email...")
        page.fill("input[name='email']", EMAIL)

        print("👉 Clicking 'Next' button...")
        page.click("button:has-text('Next')")

        print("🔐 Waiting for password field...")
        page.wait_for_selector("input[name='password']", timeout=60000)

        print("🔑 Filling in password...")
        page.fill("input[name='password']", PASSWORD)

        print("✅ Clicking 'Confirm'...")
        page.click("button:has-text('Confirm')")

        print("⏳ Waiting for redirect to dashboard...")
        page.wait_for_url("**/o/fundraising/**", timeout=60000)

        print("🎉 Login successful.")
        time.sleep(2)

    except Exception as e:
        print("❌ Login failed. Attempting to save screenshot for debugging...")
        page.screenshot(path="/tmp/login_error.png", full_page=True)
        raise Exception("Login failed: password field not visible or redirect missing. Screenshot saved.") from e

def scrape_and_update(creds=None):
    print(f"💾 Memory available before launch: {psutil.virtual_memory().available / 1024 ** 2:.2f} MB")
    if creds is None:
        raise ValueError("❌ No credentials provided to scrape_and_update.")

    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)

    def has_next_page(page):
        next_buttons = page.query_selector_all('div.MuiGrid-container button[data-test="button"]')
        if len(next_buttons) >= 2:
            next_button = next_buttons[1]
            class_attr = next_button.get_attribute("class") or ""
            is_disabled = "Mui-disabled" in class_attr
            return not is_disabled, next_button
        return False, None

    try:
        sheet.resize(rows=1)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=250)
            context = browser.new_context()
            page = context.new_page()

            login(page)
            page.goto(CAMPAIGN_URL)
            page.wait_for_selector('div[data-test="table-row"]', timeout=120000)

            page_number = 1
            max_pages = 10

            while page_number <= max_pages:
                participant_rows = page.query_selector_all('div[data-test="table-row"]')
                print(f"✅ Found {len(participant_rows)} participants on page {page_number}")

                for idx, row in enumerate(participant_rows, start=1):
                    try:
                        # ... [your row processing logic remains unchanged] ...
                        pass  # Replace this line with your full row logic

                    except Exception as e:
                        print(f"⚠️ Error processing row {idx}: {e}")
                        traceback.print_exc()
                        continue

                has_more, next_button = has_next_page(page)
                if has_more:
                    print(f"➡️ Page {page_number} complete. Moving to next page…")
                    try:
                        next_button.scroll_into_view_if_needed()
                        time.sleep(0.3)
                        next_button.click()
                        page.wait_for_selector('div[data-test="table-row"]', timeout=8000)
                        time.sleep(1)
                        page_number += 1
                    except Exception as e:
                        print(f"❌ Failed to click next page: {e}")
                        break
                else:
                    print("⛔ No more pages available.")
                    break

            context.close()
            browser.close()

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(
        "/etc/secrets/google-credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    try:
        scrape_and_update(creds)
    except Exception as e:
        print("Error running directly:", e)
    finally:
        try:
            print("📡 Triggering shim Apps Script (waits until it finishes)...")
            response = requests.get(WEB_APP_URL)
            if response.status_code == 200:
                print("✅ Apps Script finished: " + response.text)
            else:
                print(f"⚠️ Apps Script failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Error calling Apps Script shim: {e}")

