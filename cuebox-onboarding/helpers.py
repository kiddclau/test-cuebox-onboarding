import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
ALLOWED_TITLES = {"Mr.", "Mrs.", "Ms.", "Dr.", ""}


def clean_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def normalize_email(x) -> str:
    s = clean_str(x).lower()
    if not s:
        return ""
    return s if EMAIL_RE.match(s) else ""


def normalize_salutation_to_cb_title(x) -> str:
    s = clean_str(x).replace(".", "").lower()
    mapping = {"mr": "Mr.", "mrs": "Mrs.", "ms": "Ms.", "dr": "Dr."}
    return mapping.get(s, "")


def parse_created_at(x) -> str:
    s = clean_str(x)
    if not s:
        return ""
    dt = pd.to_datetime(s, errors="coerce")
    if pd.isna(dt):
        return ""
    dt = dt.normalize()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def split_tags(x) -> List[str]:
    s = clean_str(x)
    if not s:
        return []
    return [t.strip() for t in s.split(",") if t.strip()]


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for i in items:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out


def parse_amount(x) -> Optional[float]:
    if pd.isna(x):
        return None
    s = clean_str(x).replace("$", "").replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt_currency(x: Optional[float]) -> str:
    if x is None or pd.isna(x):
        return ""
    return f"${x:,.2f}"


def infer_constituent_type(first_name: str, last_name: str, company: str) -> str:
    # Assumption: Company only if company filled and no person name
    if company and not first_name and not last_name:
        return "Company"
    return "Person"


def fetch_tag_mapping(url: str, cache_file: Path) -> Dict[str, str]:
    """
    Fetch mapping: name -> mapped_name
    Uses cache if present.
    If API fails, returns {} (fallback = keep original tag).
    """
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        mapping = {}
        for item in data:
            name = clean_str(item.get("name"))
            mapped = clean_str(item.get("mapped_name"))
            if name and mapped:
                mapping[name] = mapped

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
        return mapping
    except Exception:
        return {}


def build_email_lookup(df_emails: pd.DataFrame) -> Dict[str, List[str]]:
    df = df_emails.copy()
    df["Patron ID"] = df["Patron ID"].astype(str).str.strip()
    df["Email_norm"] = df["Email"].apply(normalize_email)
    df = df[df["Email_norm"] != ""]
    return df.groupby("Patron ID")["Email_norm"].apply(lambda s: sorted(set(s.tolist()))).to_dict()


def pick_email1_email2(patron_id: str, primary_email: str, emails_lookup: Dict[str, List[str]]) -> Tuple[str, str]:
    primary = normalize_email(primary_email)
    candidates = emails_lookup.get(patron_id, [])

    email1 = primary if primary else (candidates[0] if candidates else "")
    if not email1:
        return "", ""

    email2 = ""
    for e in candidates:
        if e != email1:
            email2 = e
            break
    return email1, email2


def build_donation_aggregates(df_don: pd.DataFrame):
    """
    Returns:
      lifetime_sum: dict[patron_id] -> float
      most_recent: dict[patron_id] -> {"Date_dt": Timestamp, "Amount_num": float}
    """
    df = df_don.copy()
    df["Patron ID"] = df["Patron ID"].astype(str).str.strip()
    df["Amount_num"] = df["Donation Amount"].apply(parse_amount)
    df["Date_dt"] = pd.to_datetime(df["Donation Date"], errors="coerce")

    if "Status" in df.columns:
        df = df[df["Status"].astype(str).str.strip().str.lower() == "paid"].copy()

    lifetime = (
        df.dropna(subset=["Amount_num"])
        .groupby("Patron ID")["Amount_num"]
        .sum()
        .to_dict()
    )

    df_recent = df.dropna(subset=["Date_dt"]).copy()
    if df_recent.empty:
        return lifetime, {}

    idx = df_recent.groupby("Patron ID")["Date_dt"].idxmax()
    recent = df_recent.loc[idx, ["Patron ID", "Date_dt", "Amount_num"]].set_index("Patron ID")
    return lifetime, recent.to_dict(orient="index")
