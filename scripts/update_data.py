#!/usr/bin/env python3
"""Fetch Starbucks facts from SEC and publish annual, half-year and quarter data."""
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import os

CIK = "0000829224"
URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
OUT = Path(__file__).resolve().parents[1] / "data" / "financials.json"
RAW_OUT = Path(__file__).resolve().parents[1] / "data" / "companyfacts.json"
TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
    "gross_profit": ["GrossProfit"], "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"], "eps_diluted": ["EarningsPerShareDiluted"],
    "eps_basic": ["EarningsPerShareBasic"], "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "assets": ["Assets"], "liabilities": ["Liabilities"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "research_and_development": ["ResearchAndDevelopmentExpense"],
    "selling_general_admin": ["SellingGeneralAndAdministrativeExpense"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
}
INSTANT = {"cash", "assets", "liabilities", "current_assets", "current_liabilities"}

def normalize(value, metric):
    """Store money in USD millions and per-share facts in USD."""
    return value if metric.startswith("eps_") else round(value / 1_000_000, 3)

def get_facts(payload):
    facts = payload.get("facts", {}).get("us-gaap", {})
    return {name: next((facts[tag] for tag in tags if tag in facts), None) for name, tags in TAGS.items()}

def unit_rows(fact, key):
    if not fact:
        return []
    units = fact.get("units", {})
    unit = "USD/shares" if key.startswith("eps_") else "USD"
    return units.get(unit, [])

def main():
    contact = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if not contact:
        raise RuntimeError("Set the SEC_CONTACT_EMAIL Actions secret to a monitored contact email before running the SEC refresh.")
    req = Request(URL, headers={
        "User-Agent": f"Starbucks SEC Dashboard/1.0 {contact}",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    })
    try:
        with urlopen(req, timeout=45) as response:
            raw = response.read()
            if response.info().get("Content-Encoding") == "gzip":
                import gzip
                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
            RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
            RAW_OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            facts = get_facts(payload)
    except HTTPError as error:
        body = error.read()
        if error.headers.get("Content-Encoding") == "gzip":
            import gzip
            body = gzip.decompress(body)
        detail = body.decode("utf-8", errors="replace")
        raise RuntimeError(f"SEC Company Facts returned HTTP {error.code}: {detail}") from error
    result = {"annual": {}, "half_year": {}, "quarterly": {}, "nine_month": {}}
    instant = {}
    for metric, fact in facts.items():
        for row in unit_rows(fact, metric):
            if row.get("form") not in ("10-K", "10-Q") or not row.get("end"):
                continue
            end = date.fromisoformat(row["end"])
            start = date.fromisoformat(row["start"]) if row.get("start") else None
            filed = row.get("filed", "")
            if metric in INSTANT:
                point = instant.setdefault(end.isoformat(), {})
                if filed >= point.get(f"_filed_{metric}", ""):
                    point[metric] = normalize(row["val"], metric)
                    point[f"_filed_{metric}"] = filed
                continue
            if not start:
                continue
            days = (end - start).days + 1
            if row["form"] == "10-K" and 330 <= days <= 380:
                kind = "annual"
            elif row["form"] == "10-Q" and 150 <= days <= 200:
                kind = "half_year"
            elif row["form"] == "10-Q" and 240 <= days <= 300:
                kind = "nine_month"
            elif row["form"] == "10-Q" and 70 <= days <= 110:
                kind = "quarterly"
            else:
                continue
            key = (end.isoformat(), start.isoformat())
            current = result[kind].setdefault(key, {"end": end.isoformat(), "period": f"{row.get('fy', '')} {row.get('fp', '')}".strip()})
            if filed >= current.get(f"_filed_{metric}", ""):
                current[metric] = normalize(row["val"], metric)
                current[f"_filed_{metric}"] = filed
    for kind, periods in result.items():
        cleaned = []
        for item in periods.values():
            for key in list(item):
                if key.startswith("_filed_"):
                    item.pop(key)
            item.update({k: v for k, v in instant.get(item["end"], {}).items() if not k.startswith("_filed_")})
            if item.get("capex") is not None:
                item["capex"] = abs(item["capex"])
            if item.get("operating_cash_flow") is not None and item.get("capex") is not None:
                item["free_cash_flow"] = item["operating_cash_flow"] - item["capex"]
            cleaned.append(item)
        result[kind] = sorted(cleaned, key=lambda x: x["end"], reverse=True)
    for cumulative_kind, previous_kind, label in (("half_year", "quarterly", "Q2"), ("nine_month", "half_year", "Q3")):
        for cumulative in result[cumulative_kind]:
            candidates = [x for x in result[previous_kind] if 70 <= (date.fromisoformat(cumulative["end"]) - date.fromisoformat(x["end"])).days <= 110]
            if not candidates:
                continue
            previous = min(candidates, key=lambda x: abs((date.fromisoformat(cumulative["end"]) - date.fromisoformat(x["end"])).days - 91))
            quarter = next((x for x in result["quarterly"] if x["end"] == cumulative["end"]), None)
            if quarter is None:
                quarter = {"end": cumulative["end"], "period": f"{cumulative.get('period', '')} {label}".strip()}
                result["quarterly"].append(quarter)
            for metric in TAGS:
                if metric in INSTANT and metric in cumulative:
                    quarter.setdefault(metric, cumulative[metric])
                elif metric not in INSTANT and not metric.startswith("eps_") and metric in cumulative and metric in previous:
                    quarter.setdefault(metric, round(cumulative[metric] - previous[metric], 3))
            if quarter.get("operating_cash_flow") is not None and quarter.get("capex") is not None:
                quarter["free_cash_flow"] = round(quarter["operating_cash_flow"] - quarter["capex"], 3)
    for year in result["annual"]:
        candidates = [x for x in result["nine_month"] if 70 <= (date.fromisoformat(year["end"]) - date.fromisoformat(x["end"])).days <= 110]
        if not candidates:
            continue
        prior = min(candidates, key=lambda x: abs((date.fromisoformat(year["end"]) - date.fromisoformat(x["end"])).days - 91))
        quarter = {"end": year["end"], "period": f"{year.get('period', '')} Q4".strip()}
        for metric in TAGS:
            if metric in INSTANT and metric in year:
                quarter[metric] = year[metric]
            elif metric not in INSTANT and not metric.startswith("eps_") and metric in year and metric in prior:
                quarter[metric] = round(year[metric] - prior[metric], 3)
        if quarter.get("operating_cash_flow") is not None and quarter.get("capex") is not None:
            quarter["free_cash_flow"] = round(quarter["operating_cash_flow"] - quarter["capex"], 3)
        if any(k in quarter for k in ("revenue", "net_income")):
            result["quarterly"].append(quarter)
    result["quarterly"].sort(key=lambda x: x["end"], reverse=True)
    result.pop("nine_month")
    if not result["annual"] or not result["quarterly"]:
        raise RuntimeError("SEC response contained no annual or quarterly Starbucks facts; keeping the existing dataset unchanged.")
    result["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    result["source"] = URL
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated SEC financial dataset")

if __name__ == "__main__":
    main()
