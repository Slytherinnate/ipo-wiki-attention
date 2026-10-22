"""Fails if any unsuppressed public aggregate row has a group smaller than 15 (Tiingo license)."""
import glob, sys
import pandas as pd
MIN = 15
bad = []
for p in sorted(glob.glob("data/public/*.csv")):
    df = pd.read_csv(p)
    live = df[~df["suppressed"].astype(str).str.lower().eq("true")] if "suppressed" in df else df
    for c in [c for c in df.columns if c == "n" or c.startswith("n_")]:
        s = pd.to_numeric(live[c], errors="coerce").dropna()
        if (s < MIN).any():
            bad.append(f"{p}:{c} min={int(s.min())}")
if bad:
    print("FAIL", *bad, sep="\n"); sys.exit(1)
print("MIN GROUP PASS")
