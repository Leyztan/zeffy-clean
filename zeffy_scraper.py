from playwright.sync_api import sync_playwright
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


scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

CREDENTIALS_PATH = "/var/render/secrets/google-credentials.json"
creds_json = os.environ.get("GOOGLE_CREDS_JSON")

if creds_json:
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict)
elif os.path.exists(CREDENTIALS_PATH):
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
else:
    raise ValueError("❌ Missing GOOGLE_CREDS_JSON and google-credentials.json not found.")


client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)

def login(page):
    print("🔐 Logging in…")
    page.goto("https://www.zeffy.com/login")
    page.fill("input[name='email']", EMAIL)
    page.click("button:has-text('Next')")
    page.wait_for_selector("input[name='password']", timeout=60000)
    page.fill("input[name='password']", PASSWORD)
    page.click("button:has-text('Confirm')")
    page.wait_for_url("**/o/fundraising/**", timeout=60000)
    time.sleep(2)

def scrape_and_update():
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
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            login(page)
            page.goto(CAMPAIGN_URL)
            page.wait_for_selector('div[data-test="table-row"]', timeout=120000)

            while True:
                participant_rows = page.query_selector_all('div[data-test="table-row"]')
                print(f"✅ Found {len(participant_rows)} participants on this page")

                for idx, row in enumerate(participant_rows, start=1):
                    try:
                        cells = row.query_selector_all("td")
                        name = cells[2].inner_text().strip()
                        email = ""
                        for line in cells[2].inner_text().split("\n"):
                            if "@" in line:
                                email = line.strip().lower()
                                break
                            if not email:
                                print(f"⚠️ Could not find email for row {idx}, skipping.")
                                log_to_zeffy_logs(client, name, "", "Missing email")
                                continue


                        print(f"📄 Row {idx}: name='{name}', email='{email}'")
                        row.click()
                        page.wait_for_selector(".MuiDrawer-root.MuiDrawer-modal", timeout=10000)
                        time.sleep(1)

                        ticket_tier, amount = "", ""

                        # Retry ticket tier
                        for attempt in range(5):
                            tier_blocks = page.query_selector_all(".MuiDrawer-root .css-15j76c0")
                            for block in tier_blocks:
                                h6s = block.query_selector_all("h6")
                                for h6 in h6s:
                                    text = h6.inner_text().strip()
                                    if text in KNOWN_TIERS:
                                        ticket_tier = text
                                        break
                                if ticket_tier:
                                    break
                            if ticket_tier:
                                break
                            print(f"🔁 Retry {attempt + 1}: Ticket tier not found yet, waiting…")
                            time.sleep(1)

                        # Retry amount
                        for attempt in range(5):
                            for block in tier_blocks:
                                h3_el = block.query_selector("h3")
                                if h3_el:
                                    amount = h3_el.inner_text().strip()
                                    break
                            if amount:
                                break
                            print(f"🔁 Retry {attempt + 1}: Amount not found yet, waiting…")
                            time.sleep(1)

                        print(f"🎟️ Ticket Tier: {ticket_tier if ticket_tier else 'N/A'}")
                        print(f"💵 Amount: {amount if amount else 'N/A'}")

                        qa_blocks = []
                        for attempt in range(5):
                            qa_blocks = page.query_selector_all('p[data-test="product-answer-label"]')
                            if qa_blocks:
                                break
                            print(f"🔄 Q&A not loaded yet (attempt {attempt+1})")
                            time.sleep(1)

                        if not qa_blocks:
                            print(f"⚠️ No Q&A found for {name}, skipping.")
                            log_to_zeffy_logs(client, name, email, "Missing Q&A section")
                            page.query_selector(".MuiDrawer-root button[data-test='drawer-close-button']").click()
                            page.wait_for_selector(".MuiDrawer-root.MuiDrawer-modal", state="detached", timeout=10000)
                            continue

                        answers_map = {}
                        for block in qa_blocks:
                            question_el = block
                            question = question_el.inner_text().strip()
                            parent = question_el.evaluate_handle("el => el.parentElement")
                            answer = ""
                            input_el = parent.query_selector('input.MuiInputBase-input')
                            if input_el:
                                answer = input_el.get_attribute("value").strip()
                            if not answer:
                                dropdown_el = parent.query_selector('div[role="combobox"]')
                                if dropdown_el:
                                    answer = dropdown_el.inner_text().strip()
                            if not answer:
                                editor_el = parent.query_selector('div[data-test="answer-editor-simple-answer"]')
                                if editor_el:
                                    answer = " ".join(child.inner_text().strip() for child in editor_el.query_selector_all("div") if child.inner_text().strip())

                            match = get_close_matches(question, COLUMNS[1:-1], n=1, cutoff=0.6)
                            if match:
                                answers_map[match[0]] = answer
                                print(f"📝 Mapped: {match[0]} → {answer}")

                        row_data = [ticket_tier] + [answers_map.get(col, "") for col in COLUMNS[1:-1]] + [amount]
                        sheet.append_row(row_data)
                        print(f"✅ Added {name} to Google Sheet")

                        page.query_selector(".MuiDrawer-root button[data-test='drawer-close-button']").click()
                        page.wait_for_selector(".MuiDrawer-root.MuiDrawer-modal", state="detached", timeout=10000)
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"⚠️ Error processing {name if 'name' in locals() else idx}: {e}")
                        traceback.print_exc()
                        continue

                has_more, next_button = has_next_page(page)
                if has_more:
                    print("➡️ Moving to next page…")
                    try:
                        print("➡️ Clicking next page…")
                        next_button.scroll_into_view_if_needed()
                        time.sleep(0.3)
                        next_button.click()
                        page.wait_for_selector('div[data-test="table-row"]', timeout=8000)
                        time.sleep(1)
                    except Exception as e:
                        print(f"❌ Failed to click next page: {e}")
                        break

                    else:
                        print("⛔ No more pages")
                    break

            browser.close()

    except Exception:
        traceback.print_exc()


# ✅ Call the new shim which blocks until complete
if __name__ == "__main__":
    try:
        scrape_and_update()
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

