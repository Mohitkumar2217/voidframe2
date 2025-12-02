# src/boq_parser.py
import re
from typing import List, Dict, Any
import math

BOQ_ITEM_PATTERNS = [
    # common patterns: "Item description - qty unit @ rate = amount"
    re.compile(r'(?P<desc>[\w\W]+?)\s*-\s*(?P<qty>[\d,\.]+)\s*(?P<unit>[a-zA-Z/%]+)\s*@\s*(?P<rate>[\d,.,]+)\s*(?:=|₹)?\s*(?P<amount>[\d,.,]+)?'),
    # "1. Earthwork: 200 m3 @ 150.00 = 30000"
    re.compile(r'(?P<index>\d+)\.\s*(?P<desc>[\w\W]+?):\s*(?P<qty>[\d,\.]+)\s*(?P<unit>[a-zA-Z/%]+)\s*@\s*(?P<rate>[\d,.,]+)\s*(?:=|₹)?\s*(?P<amount>[\d,.,]+)?'),
    # fallback numeric rows: "Earthwork 200 m3 150 30000"
    re.compile(r'(?P<desc>[A-Za-z][\w\W]+?)\s+(?P<qty>[\d,\.]+)\s+(?P<unit>[a-zA-Z/%]+)\s+(?P<rate>[\d,.,]+)\s+(?P<amount>[\d,.,]+)')
]

def _clean_num(s: str) -> float:
    if s is None:
        return math.nan
    s = s.replace(',', '').strip()
    try:
        return float(s)
    except:
        return math.nan

def parse_boq_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse BOQ-like lines from free text into structured items.
    Returns list of items: {desc, qty, unit, rate, amount}
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    items = []
    for ln in lines:
        matched = False
        for pat in BOQ_ITEM_PATTERNS:
            m = pat.search(ln)
            if m:
                gd = m.groupdict()
                item = {
                    "desc": (gd.get("desc") or "").strip(),
                    "qty": _clean_num(gd.get("qty")),
                    "unit": (gd.get("unit") or "").strip(),
                    "rate": _clean_num(gd.get("rate")),
                    "amount": _clean_num(gd.get("amount"))
                }
                # If amount missing but qty & rate exist compute it
                if math.isnan(item["amount"]) and not math.isnan(item["qty"]) and not math.isnan(item["rate"]):
                    item["amount"] = round(item["qty"] * item["rate"], 2)
                items.append(item)
                matched = True
                break
        # Optionally try to capture "Description : Rs xxx" style lines
        if not matched:
            # try "desc : amount" style
            m2 = re.match(r'(?P<desc>.+?)\s*[:\-]\s*₹?\s*(?P<amount>[\d,\.]+)', ln)
            if m2:
                gd = m2.groupdict()
                amt = _clean_num(gd.get("amount"))
                items.append({"desc": gd.get("desc").strip(), "qty": math.nan, "unit": "", "rate": math.nan, "amount": amt})
    return items

def boq_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Return totals and basic flags.
    """
    total = 0.0
    missing_rate_count = 0
    missing_qty_count = 0
    for it in items:
        amt = it.get("amount", float('nan'))
        if not (isinstance(amt, float) and math.isnan(amt)):
            total += float(amt)
        if math.isnan(it.get("rate", float('nan'))):
            missing_rate_count += 1
        if math.isnan(it.get("qty", float('nan'))):
            missing_qty_count += 1

    return {
        "items_count": len(items),
        "total_estimated_cost": round(total, 2),
        "missing_rate_count": missing_rate_count,
        "missing_qty_count": missing_qty_count
    }

# Example helper to extract BOQ sections heuristically
def extract_boq_sections(text: str, section_headers=None) -> str:
    """
    Attempt to find a BOQ / Bill of Quantities block in the DPR text.
    Searches for common headers and returns that block as plain text.
    """
    if section_headers is None:
        section_headers = ["bill of quantities", "boq", "bill of items", "schedule of quantities", "bill of quantities (boq)"]
    low = text.lower()
    for header in section_headers:
        idx = low.find(header)
        if idx != -1:
            # return next ~2000 chars after header
            return text[idx: idx + 20000]
    # fallback: return whole text
    return text
