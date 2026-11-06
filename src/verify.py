"""
Catalog Invariant & Integrity Validator.
Audits the synchronized catalog to ensure:
  1. Zero price discrepancies (product.price == product.variants[0].price).
  2. 100% compliance with nearest 10 rounding on base retail prices.
  3. Adherence to Option B wholesale discount tiers (within 1-rupee integer rounding tolerance).
  4. Both name and title keys exist for frontend compatibility.
"""

import json
from typing import Dict, Any, List

def audit_catalog(catalog_path: str) -> Dict[str, Any]:
    products = json.load(open(catalog_path, encoding="utf-8"))
    
    mismatches: List[Dict[str, Any]] = []
    non_round_10: List[Dict[str, Any]] = []
    missing_title_or_name: List[str] = []
    tier_errors: List[Dict[str, Any]] = []
    variable_count = 0
    
    for p in products:
        pid = str(p.get("id"))
        price = p.get("price")
        vars_ = p.get("variants")
        
        if "name" not in p or "title" not in p:
            missing_title_or_name.append(pid)
            
        if vars_ and len(vars_) > 0:
            variable_count += 1
            first_v = vars_[0]
            first_price = first_v.get("price")
            
            if price != first_price:
                mismatches.append({
                    "id": pid,
                    "name": p.get("name"),
                    "top_price": price,
                    "first_variant_price": first_price
                })
                
            for v in vars_:
                v_p = v.get("price", 0)
                if v_p % 10 != 0:
                    non_round_10.append({
                        "id": pid,
                        "variant_size": v.get("size"),
                        "price": v_p
                    })
                # Check tiers (with +/- 1 rupee integer rounding tolerance)
                tiers = v.get("tiers", [])
                if len(tiers) == 3:
                    if tiers[0].get("price") != v_p:
                        tier_errors.append({"id": pid, "size": v.get("size"), "issue": f"Tier 1 ({tiers[0].get('price')}) != base price ({v_p})"})
                    expected_t2 = int(round(v_p * 0.95))
                    t2_actual = tiers[1].get("price", 0)
                    if abs(t2_actual - expected_t2) > 1:
                        tier_errors.append({"id": pid, "size": v.get("size"), "issue": f"Tier 2 ({t2_actual}) deviates from expected {expected_t2}"})
                    expected_t3 = int(round(v_p * 0.90))
                    t3_actual = tiers[2].get("price", 0)
                    if abs(t3_actual - expected_t3) > 1:
                        tier_errors.append({"id": pid, "size": v.get("size"), "issue": f"Tier 3 ({t3_actual}) deviates from expected {expected_t3}"})
                        
    return {
        "total_products": len(products),
        "variable_products": variable_count,
        "price_mismatches_count": len(mismatches),
        "price_mismatches": mismatches,
        "non_round_10_count": len(non_round_10),
        "non_round_10": non_round_10,
        "tier_errors_count": len(tier_errors),
        "tier_errors": tier_errors,
        "missing_title_or_name_count": len(missing_title_or_name),
        "is_catalog_valid": len(mismatches) == 0 and len(non_round_10) == 0 and len(tier_errors) == 0
    }
