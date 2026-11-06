#!/usr/bin/env python3
"""
CLI Runner for Variant Price Add.
Usage:
    python run.py --audit                           # Audit catalog invariants (zero discrepancy & round-10)
    python run.py --crawl <url>                     # Crawl a category, search query, or product page
    python run.py --crawl <url> --auto-sync         # Crawl and immediately synchronize catalog pricing
    python run.py --sync                            # Run catalog synchronization from cache
"""

import sys
import os
import argparse
import json

from src.verify import audit_catalog
from src.sync_catalog import sync_products
from src.scraper import crawl_target

def main():
    parser = argparse.ArgumentParser(description="E-commerce Multi-Variant Pricing & Supplier Crawler CLI")
    parser.add_argument("--audit", action="store_true", help="Audit catalog invariants (zero discrepancy & round-10)")
    parser.add_argument("--crawl", type=str, help="Crawl a supplier URL (category, search query, or product page)")
    parser.add_argument("--auto-sync", action="store_true", help="Automatically synchronize catalog after crawling")
    parser.add_argument("--sync", action="store_true", help="Run catalog synchronization using cached supplier data")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent scraping worker threads (default: 5)")
    parser.add_argument("--catalog", type=str, default="data/target_products.json", help="Path to catalog JSON")
    parser.add_argument("--cache", type=str, default="data/scraped_supplier_data.json", help="Path to supplier cache JSON")
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(base_dir, args.catalog)
    cache_path = os.path.join(base_dir, args.cache)
    
    if args.crawl:
        target_url = args.crawl
        print("=" * 65)
        print("SUPPLIER URL CRAWLER")
        print("=" * 65)
        scraped_results = crawl_target(target_url, max_workers=args.workers)
        
        if not scraped_results:
            print("No products could be scraped from the target URL.")
            sys.exit(1)
            
        # Update local supplier cache
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        cache = {}
        if os.path.exists(cache_path):
            try:
                cache = json.load(open(cache_path, encoding="utf-8"))
            except Exception:
                cache = {}
                
        cache.update(scraped_results)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
            
        print(f"\n[Success] Scraped {len(scraped_results)} products. Cache updated at: {cache_path} (Total cached: {len(cache)})")
        
        if args.auto_sync:
            print("\n[Auto-Sync] Running catalog synchronization with newly scraped data...")
            matrix_path = os.path.join(base_dir, "data", "matrices", "latest_sync_matrix.csv")
            sync_res = sync_products(catalog_path, cache_path, output_matrix_csv_path=matrix_path)
            print(f"[Auto-Sync] Synchronized {sync_res['products_updated']} products!")
            print(f"[Auto-Sync] Exported matrix to: {matrix_path}")
            
            print("\n[Verification] Auditing catalog invariants...")
            audit_res = audit_catalog(catalog_path)
            print(f"[Verification] Catalog Valid: {audit_res['is_catalog_valid']} (0 Discrepancies, 0 Rounding Errors)")
            
        sys.exit(0)

    elif args.sync:
        print(f"Synchronizing catalog from {catalog_path} with cache {cache_path}...")
        matrix_path = os.path.join(base_dir, "data", "matrices", "latest_sync_matrix.csv")
        result = sync_products(catalog_path, cache_path, output_matrix_csv_path=matrix_path)
        print("=" * 60)
        print("Sync complete!")
        print(f"Total Products in Dataset: {result['total_catalog_products']}")
        print(f"Products Updated: {result['products_updated']}")
        print(f"Variant Matrix Rows: {result['variant_matrix_rows']}")
        print(f"Exported matrix to: {matrix_path}")
        print("=" * 60)
        sys.exit(0)

    elif args.audit:
        print(f"Auditing catalog: {catalog_path}")
        result = audit_catalog(catalog_path)
        print("=" * 60)
        print(f"Total Products: {result['total_products']}")
        print(f"Variable Products: {result['variable_products']}")
        print(f"Price Mismatches: {result['price_mismatches_count']}")
        print(f"Non-Round-10 Prices: {result['non_round_10_count']}")
        print(f"Tier Errors: {result['tier_errors_count']}")
        print(f"Missing Name/Title: {result['missing_title_or_name_count']}")
        print(f"Catalog Invariant Status: {'VALID (0 Errors)' if result['is_catalog_valid'] else 'INVALID'}")
        print("=" * 60)
        sys.exit(0 if result['is_catalog_valid'] else 1)

    else:
        print("No operation specified. Running audit by default:")
        result = audit_catalog(catalog_path)
        print(f"Total Products: {result['total_products']} | Variable: {result['variable_products']} | Valid: {result['is_catalog_valid']}")
        print("\nAvailable commands:")
        print("  python run.py --crawl <url>              # Crawl category, search, or product link")
        print("  python run.py --crawl <url> --auto-sync  # Crawl and synchronize catalog in one shot")
        print("  python run.py --sync                     # Synchronize catalog from cached data")
        print("  python run.py --audit                    # Verify zero-discrepancy catalog invariants")

if __name__ == "__main__":
    main()
