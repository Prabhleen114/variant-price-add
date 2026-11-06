"""
WooCommerce Variations Scraper.
Scrapes product variation tables, attribute sizes, display prices, SKUs, and stock statuses.
"""

import urllib.request
import json
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def scrape_jindeal_product(url: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Fetches and parses a single product page from Jindeal.
    Extracts WooCommerce data-product_variations JSON payload or falls back to simple product price.
    """
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            form = soup.find('form', class_='variations_form')
            variations = []
            simple_price: Optional[float] = None
            
            if form and form.get('data-product_variations'):
                try:
                    raw_vars = json.loads(form['data-product_variations'])
                    for v in raw_vars:
                        p = v.get('display_price')
                        attrs = v.get('attributes', {})
                        variations.append({
                            'price': float(p) if p is not None else None,
                            'attributes': attrs,
                            'sku': v.get('sku'),
                            'is_in_stock': v.get('is_in_stock', True)
                        })
                except Exception as e:
                    pass
            else:
                price_elem = soup.find('p', class_='price')
                if price_elem:
                    p_text = price_elem.get_text(strip=True)
                    m = re.findall(r'[\d,.]+', p_text)
                    if m:
                        clean_num = m[-1].replace(',', '')
                        try:
                            simple_price = float(clean_num)
                        except:
                            pass
                            
            return {
                'url': url,
                'title': title,
                'variations': variations,
                'simple_price': simple_price
            }
    except Exception as e:
        return {
            'url': url,
            'title': '',
            'variations': [],
            'simple_price': None,
            'error': str(e)
        }
