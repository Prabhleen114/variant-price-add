#!/usr/bin/env python3
"""
CLI Runner for Variant Price Add.
Usage:
    python run.py --audit               # Run catalog integrity audit
    python run.py --sync                # Run full synchronization on target departments
    python run.py --scrape <url>        # Test scrape a Jindeal WooCommerce product page
"""

import sys
import os
import argparse
import json

from src.verify import audit_catalog
from src.sync_catalog import sync_products
from src.scraper import scrape_jindeal_product

def main():
    parser = argparse.ArgumentParser(description="E-commerce Multi-Variant Pricing & Supplier Sync CLI")
    parser.add_argument("--audit", action="store_true", help="Audit catalog invariants (zero discrepancy & round-10)")
    parser.add_argument("--sync", action="store_true", help="Run full catalog synchronization")
    parser.add_argument("--scrape", type=str, help="Scrape a single Jindeal URL")
    parser.add_argument("--catalog", type=str, default="data/target_products.json", help="Path to catalog JSON")
    parser.add_argument("--cache", type=str, default="data/scraped_supplier_data.json", help="Path to scraped supplier cache")
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(base_dir, args.catalog)
    cache_path = os.path.join(base_dir, args.cache)
    
    if args.audit:
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
        
    elif args.sync:
        print(f"Synchronizing catalog from {catalog_path} with cache {cache_path}...")
        matrix_path = os.path.join(base_dir, "data", "matrices", "latest_sync_matrix.csv")
        result = sync_products(catalog_path, cache_path, output_matrix_csv_path=matrix_path)
        print("=" * 60)
        print(f"Sync complete!")
        print(f"Total Products in Dataset: {result['total_catalog_products']}")
        print(f"Products Updated: {result['products_updated']}")
        print(f"Variant Matrix Rows: {result['variant_matrix_rows']}")
        print(f"Exported matrix to: {matrix_path}")
        print("=" * 60)
        
    elif args.scrape:
        print(f"Scraping URL: {args.scrape}...")
        data = scrape_jindeal_product(args.scrape)
        print(json.dumps(data, indent=2))
        
    else:
        # Default behavior: run audit
        print("No operation specified. Running audit by default:")
        result = audit_catalog(catalog_path)
        print(f"Total Products: {result['total_products']} | Variable: {result['variable_products']} | Valid: {result['is_catalog_valid']}")
        print("Use --help for available options.")

if __name__ == "__main__":
    main()
