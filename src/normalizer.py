"""
Variant Size Normalizer & Sorting Engine.
Standardizes heterogeneous e-commerce variation attribute strings into uniform labels
and calculates comparable metric weights/volumes for ascending sort order.
"""

from typing import Tuple, Optional, Dict

SIZE_LOOKUP: Dict[str, Tuple[str, int]] = {
    # Grams
    '50-gm': ('50 G', 50),
    '50gm': ('50 G', 50),
    '100gm': ('100 G', 100),
    '100-gm': ('100 G', 100),
    '200-gm': ('200 G', 200),
    '200gm': ('200 G', 200),
    '450gm': ('450 G', 450),
    '450-gm': ('450 G', 450),
    '500gm': ('500 G', 500),
    '500-gm': ('500 G', 500),
    '1-kg': ('1 Kg', 1000),
    '1kg': ('1 Kg', 1000),
    '5-kg': ('5 Kg', 5000),
    '5kg': ('5 Kg', 5000),
    '10kg': ('10 Kg', 10000),
    '10-kg': ('10 Kg', 10000),
    '25kg': ('25 Kg', 25000),
    '25-kg': ('25 Kg', 25000),
    '100-kg': ('100 Kg', 100000),

    # Millilitres & Litres
    '50-ml': ('50 ml', 50),
    '50ml': ('50 ml', 50),
    '100-ml': ('100 ml', 100),
    '100ml': ('100 ml', 100),
    '200-ml': ('200 ml', 200),
    '200ml': ('200 ml', 200),
    '300-ml': ('300 ml', 300),
    '300ml': ('300 ml', 300),
    '500-ml': ('500 ml', 500),
    '500ml': ('500 ml', 500),
    '1-litre': ('1 Litre', 1000),
    '1litre': ('1 Litre', 1000),
    '1-liter': ('1 Litre', 1000),
    '1liter': ('1 Litre', 1000),
    '5-liter': ('5 Litres', 5000),
    '5-litre': ('5 Litres', 5000),
    '5liter': ('5 Litres', 5000),
    '5litre': ('5 Litres', 5000),
}

def normalize_size(raw_size_key: str) -> Optional[Tuple[str, int]]:
    """
    Given a raw attribute slug (e.g. '100-ml', '500gm', '1-kg'),
    returns a normalized tuple: (display_label, sort_order).
    Returns None if the key is not a recognized size variant.
    """
    if not raw_size_key:
        return None
    cleaned = raw_size_key.strip().lower()
    return SIZE_LOOKUP.get(cleaned)
