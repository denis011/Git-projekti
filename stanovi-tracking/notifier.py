import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import json
import os

class Notifier:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            # Return default config template
            return {
                "email": {
                    "sender": "your_email@gmail.com",
                    "password": "your_app_password",
                    "recipient": "recipient_email@gmail.com",
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587
                },
                "export": {
                    "filename": "stanovi_karaburma.xlsx"
                }
            }

    def send_email(self, subject, body):
        email_cfg = self.config.get('email', {})
        if not email_cfg.get('sender') or 'your_email' in email_cfg.get('sender'):
            print("Email configuration not set. Skipping email.")
            return

        recipients = email_cfg.get('recipients', [])
        if not recipients:
            print("No recipients found. Skipping email.")
            return

        try:
            server = smtplib.SMTP(email_cfg['smtp_server'], email_cfg['smtp_port'])
            server.starttls()
            server.login(email_cfg['sender'], email_cfg['password'])
            
            for recipient in recipients:
                msg = MIMEMultipart()
                msg['From'] = email_cfg['sender']
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                server.send_message(msg)
                print(f"Email sent successfully to {recipient}!")
                
            server.quit()
        except Exception as e:
            print(f"Failed to send email: {e}")

    def export_to_excel(self, apartments):
        filename = self.config.get('export', {}).get('filename', 'stanovi.xlsx')
        df = pd.DataFrame(apartments)
        # Reorder columns for better readability
        cols = ['title', 'price_text', 'size', 'location', 'source', 'url']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        df.to_excel(filename, index=False)
        print(f"Exported {len(apartments)} apartments to {filename}")

def format_change_message(new_apartments, price_changes):
    msg = ""
    if new_apartments:
        msg += "--- NOVI STANOVI ---\n"
        for apt in new_apartments:
            msg += f"- {apt['title']} | {apt['price_text']} | {apt['size']} | {apt['url']}\n"
        msg += "\n"
    
    if price_changes:
        msg += "--- PROMENA CENE ---\n"
        for change in price_changes:
            apt = change['apartment']
            old_price = change['old_price']
            new_price = apt['price']
            direction = "POJEFTINILO" if new_price < old_price else "POSKUPELO"
            msg += f"- {direction}: {apt['title']} | Pre: {old_price} EUR | Sad: {apt['price_text']} | {apt['url']}\n"
    
    return msg
