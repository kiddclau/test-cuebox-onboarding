import argparse
from pathlib import Path

import pandas as pd

from config import DEFAULT_CACHE_FILE, DEFAULT_TAG_MAPPING_URL
from helpers import clean_str, dedupe_preserve_order, fetch_tag_mapping, split_tags


def main():
    parser = argparse.ArgumentParser(description="Generate CueBox Tags CSV (Output #2).")
    parser.add_argument("--constituents", required=True, help="Input Constituents CSV (has Tags column)")
    parser.add_argument("--out", default="output/CueBox_Tags.csv")
    parser.add_argument("--tag-mapping-url", default=DEFAULT_TAG_MAPPING_URL)
    parser.add_argument("--cache", default=str(DEFAULT_CACHE_FILE))
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df_c = pd.read_csv(args.constituents)
    df_c["Patron ID"] = df_c["Patron ID"].astype(str).str.strip()

    tag_map = fetch_tag_mapping(args.tag_mapping_url, Path(args.cache))
    map_tag = lambda t: tag_map.get(t, t)

    # Build (Patron ID, Tag) pairs
    pairs = []
    for _, r in df_c.iterrows():
        pid = clean_str(r.get("Patron ID"))
        raw_tags = split_tags(r.get("Tags"))
        mapped = [map_tag(t) for t in raw_tags]
        mapped = [t.strip() for t in mapped if t and t.strip()]
        mapped = dedupe_preserve_order(mapped)  # dedupe tags per constituent

        for t in mapped:
            pairs.append((pid, t))

    if not pairs:
        df_out = pd.DataFrame(columns=["CB Tag Name", "CB Tag Count"])
        df_out.to_csv(out_path, index=False)
        print(f"✅ Wrote {out_path} (0 tags)")
        return

    df_pairs = pd.DataFrame(pairs, columns=["Patron ID", "Tag"])
    # Dedupe any accidental duplicates
    df_pairs = df_pairs.drop_duplicates(subset=["Patron ID", "Tag"])

    # Count unique constituents per tag
    df_out = (
        df_pairs.groupby("Tag")["Patron ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Tag": "CB Tag Name", "Patron ID": "CB Tag Count"})
        .sort_values(by=["CB Tag Count", "CB Tag Name"], ascending=[False, True])
    )

    df_out.to_csv(out_path, index=False)
    print(f"✅ Wrote {out_path} ({len(df_out)} tags)")


if __name__ == "__main__":
    main()
