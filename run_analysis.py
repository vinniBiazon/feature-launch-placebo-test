"""Build the dbt project, add uncertainty to the estimates and print the readouts.

Run from the repository root after `python data/generate.py`:
    python run_analysis.py
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

DB = "feature_launch.duckdb"
REPS = 500
CONFIDENCE_Z = 1.96


def build():
    """dbt build: runs every model and every data test, and stops if a test fails."""
    dbt = shutil.which("dbt") or str(Path(sys.executable).with_name("dbt"))
    result = subprocess.run([dbt, "build", "--profiles-dir", "."], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout[-3000:])
        sys.exit("dbt build failed")


def bootstrap_weights(n, reps, seed):
    """Resampling members with replacement, as a matrix of counts (reps x members)."""
    rng = np.random.default_rng(seed)
    return rng.multinomial(n, np.full(n, 1 / n), size=reps)


def interval(values):
    return np.percentile(values, [2.5, 97.5])


# ---- 1. Feed redesign: before/after, adjusted by the same weeks one year earlier --------------
def feed_intervals(con, scenario, seed=7):
    df = con.sql(f"select * from feed_member_windows where scenario = '{scenario}'").df()
    wide = df.pivot_table(
        index="member_id", columns=["year_label", "period"],
        values=["sessions_per_week", "workouts_per_week", "sessions", "partner_views"],
    )
    w = bootstrap_weights(len(wide), REPS, seed)

    def adjusted(num, den=None):
        def agg(year, period):
            top = w @ wide[(num, year, period)].to_numpy()
            return top / (w @ wide[(den, year, period)].to_numpy()) if den else top
        this = agg("this_year", "after") / agg("this_year", "before")
        prior = agg("prior_year", "after") / agg("prior_year", "before")
        return this / prior - 1

    return {
        "sessions_per_member_week": interval(adjusted("sessions_per_week")),
        "workouts_per_member_week": interval(adjusted("workouts_per_week")),
        "partner_views_per_session": interval(adjusted("partner_views", "sessions")),
    }


# ---- 2. Badges: difference-in-differences between holders and non-holders ---------------------
def badge_intervals(con, seed=5):
    df = con.sql("select * from badge_member_periods").df()
    out = {}
    for metric in ["kudos_per_week", "sessions_per_week"]:
        means = {}
        for group, g in df.groupby("badge_group"):
            wide = g.pivot(index="member_id", columns="period", values=metric)
            w = bootstrap_weights(len(wide), REPS, seed)
            means[group] = (w @ wide["after"].to_numpy()) / (w @ wide["before"].to_numpy())
        out[metric] = interval(means["holder"] / means["non_holder"] - 1)
    return out


# ---- 3. Onboarding email: a proper A/B test readout -----------------------------------------
def ab_readout(con):
    s = con.sql("select * from email_test_summary").df().set_index("variant")
    n_c, n_t = s.loc["control", "members"], s.loc["new_email", "members"]

    # Sample ratio mismatch: did the 50/50 split actually come out 50/50?
    expected = (n_c + n_t) / 2
    chi2 = ((n_c - expected) ** 2 + (n_t - expected) ** 2) / expected
    srm_p = math.erfc(math.sqrt(chi2 / 2))  # chi-square with 1 degree of freedom

    rows = []
    for metric in ["first_workout_7d", "active_day_30"]:
        p_c, p_t = s.loc["control", f"{metric}_rate"], s.loc["new_email", f"{metric}_rate"]
        diff = p_t - p_c
        pooled = (s.loc["control", metric] + s.loc["new_email", metric]) / (n_c + n_t)
        z = diff / math.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_t))
        p_value = math.erfc(abs(z) / math.sqrt(2))
        se = math.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
        rows.append({
            "metric": metric, "control": p_c, "new_email": p_t, "diff_pp": diff * 100,
            "ci_low_pp": (diff - CONFIDENCE_Z * se) * 100, "ci_high_pp": (diff + CONFIDENCE_Z * se) * 100,
            "p_value": p_value,
        })

    # Minimum detectable effect planned before the test: 6,000 per arm, 30% baseline, 80% power
    base, n_arm = 0.30, 6000
    mde = (CONFIDENCE_Z + 0.84) * math.sqrt(2 * base * (1 - base) / n_arm)
    return pd.DataFrame(rows), n_c, n_t, srm_p, mde


def main():
    build()
    con = duckdb.connect(DB, read_only=True)
    truth = json.load(open("data/raw/planted_effects.json"))
    pd.set_option("display.width", 160)

    print("\n=== 1. Home feed redesign (launch 2025-09-01) ===")
    est = con.sql("select * from feed_estimates").df()
    for scenario in ["launch", "placebo"]:
        ci = feed_intervals(con, scenario)
        part = est[est.scenario == scenario].copy()
        part["ci_95"] = part.metric.map(lambda m: f"{ci[m][0]:+.1%} to {ci[m][1]:+.1%}")
        for col in ["change_this_year", "change_prior_year", "change_adjusted"]:
            part[col] = part[col].map("{:+.1%}".format)
        print(f"\n{scenario}:")
        print(part[["metric", "change_this_year", "change_prior_year", "change_adjusted", "ci_95"]].to_string(index=False))
    print(f"\nTrue effect: sessions {truth['feed_sessions']:+.0%}, workouts {truth['feed_workouts']:+.0%}, "
          f"partner views per session {truth['feed_partner_views_per_session']:+.0%}")

    print("\n=== 2. Century badge (launch 2025-10-06) ===")
    b = con.sql("select * from badge_estimates").df()
    ci = badge_intervals(con)
    b["ci_95"] = b.metric.map(lambda m: f"{ci[m + '_per_week'][0]:+.1%} to {ci[m + '_per_week'][1]:+.1%}")
    for col in ["gap_after_launch", "gap_before_launch", "did_relative"]:
        b[col] = b[col].map("{:+.1%}".format)
    print(b.to_string(index=False))
    print(con.sql("select * from badge_award_mix").df().to_string(index=False))
    print(f"True effect: kudos {truth['badge_kudos']:+.0%}, sessions +0%")

    print("\n=== 3. Onboarding email A/B test ===")
    ab, n_c, n_t, srm_p, mde = ab_readout(con)
    print(f"Split: control {n_c:,} / new email {n_t:,}, sample ratio check p = {srm_p:.2f}")
    print(f"Planned minimum detectable effect: {mde * 100:.1f} pp")
    print(ab.round(4).to_string(index=False))
    print(f"True effect on first workout: +{truth['email_first_workout_pp'] * 100:.1f} pp")


if __name__ == "__main__":
    main()
