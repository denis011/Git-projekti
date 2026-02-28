import requests
from bs4 import BeautifulSoup
import json
import time
import random

class Scraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def fetch(self, url):
        try:
            # Add a small random delay to avoid bot detection
            time.sleep(random.uniform(1, 3))
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

class NekretnineScraper(Scraper):
    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        listings = soup.select('.offer')
        results = []
        for item in listings:
            try:
                title_elem = item.select_one('.offer-title a')
                if not title_elem: continue
                title = title_elem.get_text(strip=True)
                url = "https://www.nekretnine.rs" + title_elem['href'] if title_elem['href'].startswith('/') else title_elem['href']
                price_elem = item.select_one('.offer-price span')
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                price = int(''.join(filter(str.isdigit, price_text))) if any(c.isdigit() for c in price_text) else 0
                size_elem = item.select_one('div.offer-main-info span')
                size = size_elem.get_text(strip=True) if size_elem else ""
                results.append({'id': url, 'title': title, 'price': price, 'price_text': price_text, 'size': size, 'url': url, 'source': 'nekretnine.rs'})
            except: pass
        return results

class Zida4Scraper(Scraper):
    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        listings = soup.select('article, .ad-card')
        results = []
        for item in listings:
            try:
                title_elem = item.select_one('h2, .title')
                if not title_elem: continue
                title = title_elem.get_text(strip=True)
                link_elem = item.select_one('a')
                if not link_elem: continue
                url = link_elem['href'] if link_elem['href'].startswith('http') else "https://www.4zida.rs" + link_elem['href']
                price_elem = item.select_one('.price')
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                price = int(''.join(filter(str.isdigit, price_text))) if any(c.isdigit() for c in price_text) else 0
                size = ""
                for span in item.find_all(['span', 'div']):
                    if 'm²' in span.get_text() or 'm2' in span.get_text():
                        size = span.get_text(strip=True)
                        break
                results.append({'id': url, 'title': title, 'price': price, 'price_text': price_text, 'size': size, 'url': url, 'source': '4zida.rs'})
            except: pass
        return results

class CityExpertScraper(Scraper):
    def fetch_api(self, url):
        # Fallback to a simplified API call that sometimes bypasses strict checks
        api_url = "https://cityexpert.rs/api/Search"
        payload = {
            "cityId": 1,
            "rentOrSale": "s",
            "propertyType": [1],
            "polygons": [37],
            "numShow": 20,
            "page": 1
        }
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/json'
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def parse(self, data):
        if not data or 'result' not in data:
            return []
        results = []
        for item in data['result']:
            try:
                prop_id = item.get('propId')
                title = f"{item.get('structure')} soban stan, {item.get('street')}"
                price = item.get('price', 0)
                price_text = f"{price:,} €"
                size = f"{item.get('size')} m²"
                url = f"https://cityexpert.rs/prodaja-nekretnina/beograd/{prop_id}"
                results.append({'id': str(prop_id), 'title': title, 'price': price, 'price_text': price_text, 'size': size, 'url': url, 'source': 'cityexpert.rs'})
            except: pass
        return results

class SrbijaNekretnineScraper(Scraper):
    def parse(self, html):
        if not html: return []
        print(f"DEBUG: srbija-nekretnine.org HTML length: {len(html)}")
        soup = BeautifulSoup(html, 'lxml')
        # Srbija-nekretnine often uses .property-list or .items-container
        # Individual items are usually inside .property-item or .item
        listings = soup.select('.property-item, .item, .product-item, article')
        if not listings:
            # Fallback: find all links that look like property links
            listings = [a.find_parent('div') for a in soup.select('a[href*="/stan-"]') if a.find_parent('div')]
            
        results = []
        # Remove duplicates from fallback
        seen_ids = set()
        
        for item in listings:
            if not item: continue
            try:
                title_elem = item.select_one('h2, h3, .title, .item-title, a[href*="/stan-"]')
                if not title_elem: continue
                
                title = title_elem.get_text(strip=True)
                # If title_elem is just the link
                if title_elem.name == 'a':
                    url = title_elem['href']
                else:
                    link = title_elem.select_one('a')
                    if not link: continue
                    url = link['href']
                
                if not url.startswith('http'):
                    url = "https://www.srbija-nekretnine.org" + url
                
                if url in seen_ids: continue
                seen_ids.add(url)
                
                price_elem = item.select_one('.price, .item-price, span:contains("€")')
                if not price_elem:
                    # Search text for Euro symbol
                    for span in item.find_all(['span', 'div', 'p', 'b']):
                        if '€' in span.get_text():
                            price_elem = span
                            break
                            
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                price = int(''.join(filter(str.isdigit, price_text))) if any(c.isdigit() for c in price_text) else 0
                
                size = ""
                # Search for m2
                for span in item.find_all(['span', 'div', 'li', 'p']):
                    txt = span.get_text()
                    if 'm2' in txt or 'm²' in txt:
                        size = txt.strip()
                        break
                
                results.append({
                    'id': url,
                    'title': title,
                    'price': price,
                    'price_text': price_text,
                    'size': size,
                    'url': url,
                    'source': 'srbija-nekretnine.org'
                })
            except: pass
        return results
