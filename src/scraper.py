"""
WooCommerce Variations & Category Crawler.
Features:
  - Discovers all products from category pages (with automatic pagination /page/N/).
  - Discovers all products from search query results.
  - Concurrently scrapes variable product variation forms, sizes, prices, SKUs, and stock.
  - Automatically updates the local supplier cache.
"""

import urllib.request
import urllib.parse
import json
import re
from typing import Dict, Any, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def discover_product_links(target_url: str, max_pages: int = 20) -> List[str]:
    """
    Detects whether the URL is a single product, category page, or search query.
    If category or search, traverses pagination (/page/N/) and returns all unique product links.
    """
    clean_url = target_url.strip()
    
    # 1. Single product URL
    if "/product/" in clean_url and not any(k in clean_url for k in ["/product-category/", "?s="]):
        return [clean_url]

    discovered: List[str] = []
    seen: Set[str] = set()
    
    parsed = urllib.parse.urlparse(clean_url)
    is_search = bool(parsed.query and "s=" in parsed.query)
    
    for page in range(1, max_pages + 1):
        if is_search:
            # WooCommerce search pagination: https://domain/page/N/?s=query
            if page == 1:
                page_url = clean_url
            else:
                base = f"{parsed.scheme}://{parsed.netloc}/page/{page}/?{parsed.query}"
                page_url = base
        else:
            # WooCommerce category pagination: https://domain/product-category/slug/page/N/
            clean_base = clean_url.rstrip('/')
            clean_base = re.sub(r'/page/\d+/?$', '', clean_base)
            page_url = clean_base + '/' if page == 1 else f"{clean_base}/page/{page}/"

        print(f"  [Discovery] Checking page {page}: {page_url}")
        req = urllib.request.Request(page_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                
                page_products = []
                for a in soup.find_all('a', href=re.compile(r'/product/[^/]+/?$')):
                    href = a.get('href', '').split('#')[0].split('?')[0]
                    # Filter out non-product anchors
                    if href and '/product/' in href and '/product-category/' not in href:
                        if href not in seen:
                            seen.add(href)
                            page_products.append(href)
                            
                if not page_products:
                    print(f"  [Discovery] No new products found on page {page}. Stopping pagination.")
                    break
                    
                discovered.extend(page_products)
                print(f"  [Discovery] Found {len(page_products)} products on page {page} (Cumulative: {len(discovered)})")
                
        except urllib.error.HTTPError as he:
            if he.code == 404:
                print(f"  [Discovery] Reached end of pagination at page {page} (HTTP 404).")
                break
            else:
                print(f"  [Discovery] Warning: HTTP {he.code} on {page_url}: {he}")
                break
        except Exception as e:
            print(f"  [Discovery] Error on {page_url}: {e}")
            break

    return discovered

def crawl_target(target_url: str, max_workers: int = 5, max_pages: int = 20) -> Dict[str, Any]:
    """
    Crawls a target category, search query, or product URL,
    extracts all product variations and pricing concurrently,
    and returns a mapping of {url: product_details}.
    """
    print(f"\n[Crawler] Discovering product links from: {target_url}")
    product_links = discover_product_links(target_url, max_pages=max_pages)
    print(f"[Crawler] Discovered {len(product_links)} products to scrape.\n")
    
    if not product_links:
        return {}

    results: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_jindeal_product, url): url for url in product_links}
        completed = 0
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                results[url] = data
                completed += 1
                v_count = len(data.get("variations", []))
                s_price = data.get("simple_price")
                status = f"{v_count} variants" if v_count else f"Simple: Rs.{s_price}"
                print(f"  [{completed}/{len(product_links)}] Scraped: {data.get('title')[:45]} ({status})")
            except Exception as e:
                print(f"  Error scraping {url}: {e}")

    return results
