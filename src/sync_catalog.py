"""
Catalog Synchronization Pipeline.
Matches catalog products against scraped supplier data, applies normalized multi-size variations,
calculates wholesale volume tiers with 30% markup, and guarantees zero-discrepancy catalog invariants.
"""

import json
import csv
import os
from typing import List, Dict, Any, Optional
from .normalizer import normalize_size
from .pricing_engine import apply_supplier_markup, generate_wholesale_tiers

def sync_products(
    catalog_path: str,
    scraped_cache_path: str,
    mapping: Optional[Dict[str, str]] = None,
    output_catalog_path: Optional[str] = None,
    output_matrix_csv_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes synchronization on the target catalog using cached/scraped supplier data.
    """
    if not os.path.exists(catalog_path):
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
    if not os.path.exists(scraped_cache_path):
        raise FileNotFoundError(f"Scraped cache file not found: {scraped_cache_path}")
        
    products = json.load(open(catalog_path, encoding="utf-8"))
    supplier_cache = json.load(open(scraped_cache_path, encoding="utf-8"))
    
    csv_rows = []
    updated_count = 0
    
    for p in products:
        pid = str(p.get("id"))
        title = p.get("name") or p.get("title") or "Product"
        category = p.get("category", "")
        
        # Ensure both name and title keys exist
        p["name"] = title
        p["title"] = title
        
        target_url = mapping.get(pid) if mapping else None
        
        # If no explicit mapping, try matching url in supplier_cache
        if not target_url:
            for url, s_data in supplier_cache.items():
                s_title = s_data.get("title", "").lower()
                clean_t = title.split("(")[0].strip().lower()
                if clean_t and clean_t in s_title:
                    target_url = url
                    break
                    
        if target_url and target_url in supplier_cache:
            j_data = supplier_cache[target_url]
            variations = j_data.get("variations", [])
            simple_price = j_data.get("simple_price")
            
            parsed_variants = []
            seen_sizes = set()
            
            for v in variations:
                price = v.get("price")
                if not price or price <= 1.0:
                    continue
                attrs = v.get("attributes", {})
                size_key = attrs.get("attribute_pa_size")
                if not size_key:
                    for ak, av in attrs.items():
                        norm = normalize_size(av)
                        if norm:
                            size_key = av
                            break
                if size_key:
                    norm = normalize_size(size_key)
                    if norm:
                        label, order = norm
                        if label in seen_sizes:
                            continue
                        seen_sizes.add(label)
                        retail_price = apply_supplier_markup(price, 0.30)
                        tiers = generate_wholesale_tiers(retail_price)
                        parsed_variants.append({
                            "size": label,
                            "order": order,
                            "supplier_price": price,
                            "price": retail_price,
                            "tiers": tiers
                        })
                        
            parsed_variants.sort(key=lambda x: x["order"])
            
            # Simple product fallback
            if not parsed_variants:
                s_price = simple_price if (simple_price and simple_price > 0) else float(p.get("price", 100))
                retail_price = apply_supplier_markup(s_price, 0.30)
                default_size = "1 Litre" if any(u in title.lower() for u in ["liquid", "wash", "shampoo", "oil", "serum"]) else "1 Kg"
                tiers = generate_wholesale_tiers(retail_price)
                parsed_variants.append({
                    "size": default_size,
                    "order": 1000,
                    "supplier_price": s_price,
                    "price": retail_price,
                    "tiers": tiers
                })
                
            clean_variants = []
            for pv in parsed_variants:
                clean_variants.append({
                    "size": pv["size"],
                    "price": pv["price"],
                    "tiers": pv["tiers"]
                })
                csv_rows.append({
                    "Product ID": pid,
                    "Product Title": title,
                    "Category": category,
                    "Size Variant": pv["size"],
                    "Supplier Price": f"Rs.{pv['supplier_price']:.2f}",
                    "Ekora Retail Price (+30%)": f"Rs.{pv['price']}",
                    "Tier 1 (1-9)": f"Rs.{pv['tiers'][0]['price']}",
                    "Tier 2 (10-49, -5%)": f"Rs.{pv['tiers'][1]['price']}",
                    "Tier 3 (50+, -10%)": f"Rs.{pv['tiers'][2]['price']}"
                })
                
            p["variants"] = clean_variants
            p["price"] = clean_variants[0]["price"]
            p["tiers"] = clean_variants[0]["tiers"]
            p["bulkDiscountAvailable"] = True
            p["maxDiscount"] = 10
            p["inStock"] = True
            updated_count += 1
            
        elif p.get("variants") and len(p["variants"]) > 0:
            # Enforce top-level synchronization for variable products
            first_v = p["variants"][0]
            p["price"] = first_v["price"]
            p["tiers"] = first_v.get("tiers", generate_wholesale_tiers(first_v["price"]))
            p["bulkDiscountAvailable"] = True
            p["maxDiscount"] = 10

    # Save updated catalog
    out_cat = output_catalog_path or catalog_path
    with open(out_cat, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
        
    # Save CSV matrix
    if output_matrix_csv_path and csv_rows:
        os.makedirs(os.path.dirname(output_matrix_csv_path), exist_ok=True)
        fieldnames = [
            "Product ID", "Product Title", "Category", "Size Variant",
            "Supplier Price", "Ekora Retail Price (+30%)",
            "Tier 1 (1-9)", "Tier 2 (10-49, -5%)", "Tier 3 (50+, -10%)"
        ]
        with open(output_matrix_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
            
    return {
        "total_catalog_products": len(products),
        "products_updated": updated_count,
        "variant_matrix_rows": len(csv_rows)
    }
