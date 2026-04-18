"""
profile_refresher.py
Bumps your Naukri profile to the top of recruiter searches by toggling
a dot in the profile summary. Run this as a cron job / scheduled task.
"""
import time
import json
import random
import schedule
from datetime import datetime
from scraper import get_driver, slow_delay
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from db import log_profile_refresh, init_profile_log

def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)

def refresh_profile(email, password, headless=True):
    print("[*] Starting profile refresh...")
    driver = get_driver(headless=headless)
    try:
        wait = WebDriverWait(driver, 15)

        # --- Login ---
        driver.get("https://www.naukri.com/nlogin/login")
        wait.until(EC.presence_of_element_located((By.ID, "usernameField"))).send_keys(email)
        slow_delay(1, 2)
        driver.find_element(By.ID, "passwordField").send_keys(password)
        slow_delay(1, 2)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        slow_delay(3, 5)
        print("[+] Logged in.")

        # --- Go to profile edit page ---
        driver.get("https://www.naukri.com/mnjuser/profile")
        slow_delay(3, 5)

        # --- Open resume summary edit ---
        try:
            edit_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'resumeHeadline')]//span[contains(@class,'edit') or contains(@class,'pencil') or @title='Edit']")
            ))
            edit_btn.click()
        except:
            # fallback: click the headline section itself
            edit_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#resumeHeadline .edit, .widgetHead .edit, [data-ga-track*='headline'] .edit")
            ))
            edit_btn.click()
        slow_delay(2, 3)

        # --- Find the textarea ---
        textarea = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "textarea#resumeHeadlineTxt, textarea[name='resumeHeadline'], textarea.headlineTextarea, textarea")
        ))
        current_text = textarea.get_attribute("value") or textarea.text or ""
        print(f"[*] Current summary length: {len(current_text)} chars")

        # Toggle dot at end: add if missing, remove if present
        if current_text.endswith(" ."):
            new_text = current_text[:-2]
        else:
            new_text = current_text + " ."

        # Clear and type new text
        textarea.click()
        slow_delay(0.5, 1)
        driver.execute_script("arguments[0].value = '';", textarea)
        driver.execute_script("arguments[0].value = arguments[1];", textarea, new_text)
        # Trigger input event so Naukri's React/Angular detects the change
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", textarea
        )
        slow_delay(1, 2)

        # --- Save ---
        try:
            save_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Save') or contains(text(),'save') or contains(text(),'UPDATE') or contains(text(),'Update')]")
            ))
            driver.execute_script("arguments[0].click();", save_btn)
        except:
            # fallback: any submit button in the open modal/form
            btns = driver.find_elements(By.XPATH,
                "//div[contains(@class,'modal') or contains(@class,'form') or contains(@class,'edit')]//button[@type='submit' or contains(@class,'save') or contains(@class,'primary') or contains(@class,'btn')]"
            )
            if btns:
                driver.execute_script("arguments[0].click();", btns[0])
            else:
                raise Exception("Save button not found")
        slow_delay(2, 3)

        print("[+] Profile refreshed successfully. Summary updated.")
        log_profile_refresh("success", "Summary dot toggled and saved successfully.")

    except Exception as e:
        msg = str(e).splitlines()[0]
        print(f"[!] Profile refresh failed: {msg}")
        log_profile_refresh("failed", msg)
    finally:
        driver.quit()

def run(headless=True):
    config = load_config()
    init_profile_log()  # ensure table exists
    refresh_profile(config["naukri"]["email"], config["naukri"]["password"], headless=headless)

if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        # --once --visible to watch the browser
        headless = "--visible" not in sys.argv
        run(headless=headless)
    else:
        print("[*] Profile refresher started — runs every 30 min between 08:30 and 19:30.")
        print("    Press Ctrl+C to stop. Use --once to run immediately and exit.")

        def job_within_hours():
            now = datetime.now().time()
            start = datetime.strptime("08:30", "%H:%M").time()
            end   = datetime.strptime("19:30", "%H:%M").time()
            if start <= now <= end:
                run()
            else:
                print(f"[~] Outside active hours ({now.strftime('%H:%M')}), skipping.")

        schedule.every(30).minutes.do(job_within_hours)

        # Run immediately if within hours
        job_within_hours()

        while True:
            schedule.run_pending()
            time.sleep(30)
