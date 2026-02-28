import json
import os
import time
import random
import sys
from datetime import datetime
from scraper import NekretnineScraper
from notifier import Notifier, format_change_message

# Ensure working directory is the script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

DATA_FILE = os.path.join(BASE_DIR, 'apartments.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
LOG_FILE = os.path.join(BASE_DIR, 'log.txt')

def setup_logging():
    try:
        f = open(LOG_FILE, 'w', encoding='utf-8')
        sys.stdout = f
        sys.stderr = f
        print(f"--- Izvršavanje skripte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        print(f"Radni direktorijum: {BASE_DIR}")
        return f
    except Exception as e:
        print(f"CRITICAL ERROR: Could not open log file: {str(e)}")
        return None

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Greska pri ucitavanju podataka: {e}")
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Greska pri cuvanju podataka: {e}")

def main():
    log_f = setup_logging()
    try:
        notifier = Notifier(config_path=CONFIG_FILE)
        config = notifier.config
        urls = config.get('urls', [])
        
        if not urls:
            print("GRESKA: Nema URL-ova u config.json!")
            return

        existing_data = load_data()
        current_apartments = []
        nekretnine_scraper = NekretnineScraper()

        for url in urls:
            if 'nekretnine.rs' in url:
                print(f"Scraping: {url}")
                html = nekretnine_scraper.fetch(url)
                if html:
                    results = nekretnine_scraper.parse(html)
                    current_apartments.extend(results)
                    print(f"Found {len(results)} items.")
                else:
                    print(f"Failed to fetch {url}")

        # Compare
        new_apartments = []
        price_changes = []
        
        for apt in current_apartments:
            apt_id = apt['id']
            if apt_id not in existing_data:
                new_apartments.append(apt)
                existing_data[apt_id] = apt
            else:
                old_apt = existing_data[apt_id]
                if apt['price'] != old_apt['price'] and apt['price'] > 0:
                    price_changes.append({
                        'apartment': apt,
                        'old_price': old_apt['price']
                    })
                    existing_data[apt_id] = apt

        if new_apartments or price_changes:
            msg = format_change_message(new_apartments, price_changes)
            print("Changes found!")
            print(msg)
            
            recipients = config.get('email', {}).get('recipients', [])
            subject = f"OBEVEŠTENJE: Promene na tržištu stanova ({len(new_apartments)} novi, {len(price_changes)} cena)"
            notifier.send_email(subject, msg)
            
            all_apartments = list(existing_data.values())
            notifier.export_to_excel(all_apartments)
            save_data(existing_data)
        else:
            print("No new changes found.")
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
    finally:
        print(f"--- Završeno u {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        if log_f:
            sys.stdout.flush()
            log_f.close()

if __name__ == "__main__":
    main()
