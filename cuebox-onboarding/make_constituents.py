import argparse
from pathlib import Path

import pandas as pd

from config import DEFAULT_CACHE_FILE, DEFAULT_TAG_MAPPING_URL
from helpers import (
    ALLOWED_TITLES,
    build_donation_aggregates,
    build_email_lookup,
    clean_str,
    dedupe_preserve_order,
    fetch_tag_mapping,
    fmt_currency,
    infer_constituent_type,
    parse_created_at,
    pick_email1_email2,
    normalize_salutation_to_cb_title,
    split_tags,
)


def validate_constituents(df_out: pd.DataFrame) -> pd.DataFrame:
    issues = []

    if df_out["CB Constituent ID"].duplicated().any():
        for pid in df_out[df_out["CB Constituent ID"].duplicated()]["CB Constituent ID"].unique():
            issues.append((pid, "DUPLICATE_ID", "Duplicate CB Constituent ID in output."))

    bad_created = df_out[df_out["CB Created At"].astype(str).str.strip() == ""]
    for pid in bad_created["CB Constituent ID"].tolist():
        issues.append((pid, "MISSING_CREATED_AT", "CB Created At missing/unparseable."))

    bad_title = df_out[~df_out["CB Title"].isin(ALLOWED_TITLES)]
    for _, r in bad_title.iterrows():
        issues.append((r["CB Constituent ID"], "BAD_TITLE", f"Invalid CB Title: {r['CB Title']}"))

    bad_email2 = df_out[
        (df_out["CB Email 1 (Standardized)"].astype(str).str.strip() == "")
        & (df_out["CB Email 2 (Standardized)"].astype(str).str.strip() != "")
    ]
    for pid in bad_email2["CB Constituent ID"].tolist():
        issues.append((pid, "EMAIL2_WITHOUT_EMAIL1", "Email 2 present but Email 1 missing."))

    eq = df_out[
        (df_out["CB Email 1 (Standardized)"].astype(str).str.strip() != "")
        & (df_out["CB Email 1 (Standardized)"] == df_out["CB Email 2 (Standardized)"])
    ]
    for pid in eq["CB Constituent ID"].tolist():
        issues.append((pid, "EMAIL_DUP", "Email 2 equals Email 1."))

    return pd.DataFrame(issues, columns=["CB Constituent ID", "Issue Code", "Message"])


def main():
    parser = argparse.ArgumentParser(description="Generate CueBox Constituents CSV (Output #1).")
    parser.add_argument("--constituents", required=True, help="Input Constituents CSV")
    parser.add_argument("--emails", required=True, help="Input Emails CSV")
    parser.add_argument("--donations", required=True, help="Input Donation History CSV")
    parser.add_argument("--out", default="output/CueBox_Constituents.csv")
    parser.add_argument("--qa", default="output/qa_constituents.csv")
    parser.add_argument("--tag-mapping-url", default=DEFAULT_TAG_MAPPING_URL)
    parser.add_argument("--cache", default=str(DEFAULT_CACHE_FILE))
    args = parser.parse_args()

    out_path = Path(args.out)
    qa_path = Path(args.qa)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.parent.mkdir(parents=True, exist_ok=True)

    df_c = pd.read_csv(args.constituents)
    df_e = pd.read_csv(args.emails)
    df_d = pd.read_csv(args.donations)

    df_c["Patron ID"] = df_c["Patron ID"].astype(str).str.strip()
    df_c = df_c.drop_duplicates(subset=["Patron ID"], keep="first")

    emails_lookup = build_email_lookup(df_e)
    lifetime_lookup, recent_lookup = build_donation_aggregates(df_d)

    tag_map = fetch_tag_mapping(args.tag_mapping_url, Path(args.cache))
    map_tag = lambda t: tag_map.get(t, t)

    rows = []
    for _, r in df_c.iterrows():
        pid = clean_str(r.get("Patron ID"))
        fn = clean_str(r.get("First Name"))
        ln = clean_str(r.get("Last Name"))
        company = clean_str(r.get("Company"))

        ctype = infer_constituent_type(fn, ln, company)

        created_at = parse_created_at(r.get("Date Entered"))
        cb_title = normalize_salutation_to_cb_title(r.get("Salutation"))
        email1, email2 = pick_email1_email2(pid, r.get("Primary Email"), emails_lookup)

        raw_tags = split_tags(r.get("Tags"))
        mapped_tags = [map_tag(t) for t in raw_tags]
        mapped_tags = [t for t in mapped_tags if t]
        mapped_tags = dedupe_preserve_order(mapped_tags)
        cb_tags = ", ".join(mapped_tags)

        # Background info: Job Title only (per your clarified gender rule)
        job_title = clean_str(r.get("Title"))
        background = f"Job Title: {job_title}" if job_title else ""

        lifetime = lifetime_lookup.get(pid, None)
        lifetime_str = fmt_currency(lifetime) if lifetime is not None else ""

        if pid in recent_lookup:
            mr = recent_lookup[pid]
            mr_date = mr.get("Date_dt")
            mr_amt = mr.get("Amount_num")
            mr_date_str = "" if pd.isna(mr_date) else pd.to_datetime(mr_date).strftime("%Y-%m-%d %H:%M:%S")
            mr_amt_str = fmt_currency(mr_amt) if mr_amt is not None and not pd.isna(mr_amt) else ""
        else:
            mr_date_str, mr_amt_str = "", ""

        rows.append(
            {
                "CB Constituent ID": pid,
                "CB Constituent Type": ctype,
                "CB First Name": fn if ctype == "Person" else "",
                "CB Last Name": ln if ctype == "Person" else "",
                "CB Company Name": company if ctype == "Company" else "",
                "CB Created At": created_at,
                "CB Email 1 (Standardized)": email1,
                "CB Email 2 (Standardized)": email2,
                "CB Title": cb_title,
                "CB Tags": cb_tags,
                "CB Background Information": background,
                "CB Lifetime Donation Amount": lifetime_str,
                "CB Most Recent Donation Date": mr_date_str,
                "CB Most Recent Donation Amount": mr_amt_str,
            }
        )

    df_out = pd.DataFrame(rows)
    df_out.to_csv(out_path, index=False)

    df_qa = validate_constituents(df_out)
    df_qa.to_csv(qa_path, index=False)

    print(f"✅ Wrote {out_path} ({len(df_out)} rows)")
    print(f"🧪 QA report {qa_path} ({len(df_qa)} issues)")


if __name__ == "__main__":
    main()
