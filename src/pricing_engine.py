"""
Pricing Engine & Wholesale Tier Calculator.
Calculates retail markup (+30%, nearest 10) and Option B wholesale discount tiers.
"""

from typing import List, Dict, Any

def round_to_nearest_10(val: float) -> int:
    """
    Rounds a monetary value to the nearest integer multiple of 10.
    Example: 128.7 -> 130, 258.7 -> 260, 843.7 -> 840.
    """
    return int(round(val / 10.0) * 10)

def apply_supplier_markup(supplier_price: float, markup_pct: float = 0.30) -> int:
    """
    Applies the supplier reference markup and rounds to the nearest 10.
    Formula: round((supplier_price * (1 + markup_pct)) / 10) * 10
    """
    if supplier_price <= 0:
        return 0
    raw_retail = supplier_price * (1.0 + markup_pct)
    return round_to_nearest_10(raw_retail)

def generate_wholesale_tiers(base_retail_price: int) -> List[Dict[str, Any]]:
    """
    Generates standard Option B volume discount tiers:
      - Tier 1 (1–9 units): Base retail price (0% discount)
      - Tier 2 (10–49 units): 5% wholesale discount, rounded to integer
      - Tier 3 (50+ units): 10% distributor discount, rounded to integer
    """
    t1 = base_retail_price
    t2 = int(round(base_retail_price * 0.95))
    t3 = int(round(base_retail_price * 0.90))
    return [
        {"minQty": 1, "maxQty": 9, "price": t1, "discountPct": 0},
        {"minQty": 10, "maxQty": 49, "price": t2, "discountPct": 5},
        {"minQty": 50, "maxQty": None, "price": t3, "discountPct": 10}
    ]
