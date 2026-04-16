import requests
from bs4 import BeautifulSoup
import json
import os
import time
import hashlib
from datetime import datetime

class ViviendaScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        self.properties = {} # Keyed by fingerprint to avoid duplicates

    def get_fingerprint(self, title, price_val, chars):
        # Create a unique ID based on normalized data
        # Normalize title: lowercase and remove spaces
        norm_title = "".join(title.lower().split())
        
        # Look for m2 in chars to add to fingerprint (more precise)
        m2 = ""
        for c in chars:
            if "m²" in c:
                m2 = c
                break
        
        raw_id = f"{norm_title}-{price_val}-{m2}"
        return hashlib.mdsafe_hex(raw_id.encode()) if hasattr(hashlib, 'mdsafe_hex') else hashlib.md5(raw_id.encode()).hexdigest()

    def scrape_pisos_com(self, max_pages=10):
        print(f"Scraping Pisos.com (Target: {max_pages} pages)...")
        for page in range(1, max_pages + 1):
            url = f"https://www.pisos.com/venta/pisos-merida/{page}/"
            if page == 1:
                url = "https://www.pisos.com/venta/pisos-merida/"
            
            print(f"  Fetching page {page}: {url}")
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    print(f"  Error {response.status_code}")
                    break # Stop if we hit a block
                
                soup = BeautifulSoup(response.text, 'html.parser')
                listings = soup.select('.p-property-card, .ad-preview')
                
                if not listings:
                    print("  No more listings found.")
                    break

                for item in listings:
                    try:
                        title_node = item.select_one('.p-property-card__title, .ad-preview__title')
                        price_node = item.select_one('.p-property-card__price, .ad-preview__price')
                        img_node = item.select_one('img') 
                        
                        img_url = ""
                        if img_node:
                            img_url = img_node.get('data-src') or img_node.get('src') or img_node.get('data-original') or ""
                        
                        # Characteristics
                        char_nodes = item.select('.p-property-card__features-item, .ad-preview__char')
                        chars = [c.get_text(strip=True) for c in char_nodes]
                        
                        # Agency
                        agency_node = item.select_one('.p-property-card__logo img, .ad-preview__logo img')
                        agency = agency_node.get('alt') if agency_node else "Particular"

                        price_text = price_node.get_text(strip=True) if price_node else "0"
                        price_val = 0
                        price_clean = ''.join(filter(str.isdigit, price_text))
                        if price_clean:
                            price_val = int(price_clean)

                        if title_node and price_val > 0:
                            title = title_node.get_text(strip=True)
                            
                            # Check for duplicates via Fingerprint
                            fingerprint = self.get_fingerprint(title, price_val, chars)
                            
                            if fingerprint not in self.properties:
                                self.properties[fingerprint] = {
                                    "title": title,
                                    "link": "https://www.pisos.com" + title_node['href'] if title_node['href'].startswith('/') else title_node['href'],
                                    "price": price_text,
                                    "price_val": price_val,
                                    "img": img_url,
                                    "chars": chars,
                                    "agency": agency,
                                    "source": "Pisos.com"
                                }
                    except Exception as e:
                        print(f"  Error parsing item: {e}")
                
                time.sleep(1.5) # Increased delay for safety
            except Exception as e:
                print(f"  Request error: {e}")
                break

    def save_results(self, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        results_list = list(self.properties.values())
        # Sort by price (cheapest first)
        results_list.sort(key=lambda x: x['price_val'])
        
        data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(results_list),
            "properties": results_list
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(results_list)} unique properties to {output_path}")

if __name__ == "__main__":
    scraper = ViviendaScraper()
    # Scrape 10 pages as requested
    scraper.scrape_pisos_com(max_pages=10)
    
    # Intelligent path detection for Local vs GitHub Actions
    output = 'docs/data/vivienda.json'
    if not os.path.exists('docs') and os.path.exists('ViviendaMerida/docs'):
        output = 'ViviendaMerida/docs/data/vivienda.json'
        
    scraper.save_results(output)
