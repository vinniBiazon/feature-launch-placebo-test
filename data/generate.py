"""Generate the synthetic data for the feature launch case study.

A workout tracking app with a social feed. Three things happened in the second half of 2025:
  1. A redesigned home feed (2025-09-01)
  2. "Century" badges for 100 logged workouts (2025-10-06), backfilled to everyone already past 100
  3. A 50/50 A/B test of a new onboarding email for signups from Sep to Nov 2025

The true effects are planted below, so the analysis can be checked against them.
Run from the repository root: python data/generate.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(11)
OUT = Path("data/raw")
OUT.mkdir(parents=True, exist_ok=True)

# ---- Planted effects -------------------------------------------------------
FEED_LAUNCH = pd.Timestamp("2025-09-01")
BADGE_LAUNCH = pd.Timestamp("2025-10-06")
FEED_SESSION_LIFT = 0.06   # redesign: +6% sessions
FEED_WORKOUT_LIFT = 0.00   # redesign does not change workouts
FEED_PARTNER_LIFT = 0.00   # redesign does not change partner views per session
BADGE_KUDOS_LIFT = 0.03    # holding a badge: +3% kudos given
BADGE_THRESHOLD = 100
EMAIL_CONTROL_RATE = 0.30  # first workout within 7 days
EMAIL_TREATMENT_LIFT_PP = 0.035

# ---- Members ---------------------------------------------------------------
N = 15_000
weeks = pd.date_range("2024-01-01", "2025-12-29", freq="7D")  # Mondays
W = len(weeks)

joined = pd.to_datetime("2022-01-01") + pd.to_timedelta(
    rng.integers(0, (pd.Timestamp("2025-06-30") - pd.Timestamp("2022-01-01")).days, N), unit="D"
)
engagement = rng.lognormal(-0.2, 0.7, N)  # stable member trait
lifetime_weeks = rng.exponential(130, N)  # churn is independent of engagement

join_week = np.clip(np.asarray((joined - weeks[0]).days // 7), 0, None)
first_week_alive = np.where(joined < weeks[0], 0, join_week)
weeks_since_join = (np.arange(W)[None, :] - np.asarray((joined - weeks[0]).days // 7)[:, None])
alive = (np.arange(W)[None, :] >= first_week_alive[:, None]) & (weeks_since_join < lifetime_weeks[:, None])

# ---- Calendar effects ------------------------------------------------------
doy = np.asarray(weeks.dayofyear)
season = 1 + 0.15 * np.cos(2 * np.pi * (doy - 10) / 365) - 0.12 * np.exp(-(((doy - 222) / 22) ** 2))

def campaign(peak, width_weeks, height):
    t = np.asarray((weeks - pd.Timestamp(peak)).days) / 7
    return height * np.exp(-((t / width_weeks) ** 2))

# Partner challenges (sponsored content) come in campaigns that differ every year
partner_rate = 0.30 + campaign("2024-05-13", 4, 0.35) + campaign("2025-07-07", 5, 0.55) + campaign("2025-12-01", 3, 0.25)

feed_on = np.asarray(weeks >= FEED_LAUNCH)

# ---- Weekly activity -------------------------------------------------------
base = engagement[:, None] * season[None, :] * alive
lam_sessions = 2.2 * base * np.where(feed_on, 1 + FEED_SESSION_LIFT, 1)[None, :]
lam_workouts = 1.4 * base * np.where(feed_on, 1 + FEED_WORKOUT_LIFT, 1)[None, :]
sessions = rng.poisson(lam_sessions)
workouts = rng.poisson(lam_workouts)
partner_views = rng.poisson(sessions * partner_rate[None, :] * np.where(feed_on, 1 + FEED_PARTNER_LIFT, 1)[None, :])

# Workouts logged before 2024, so lifetime totals can be computed
prior_weeks = np.clip(np.asarray((weeks[0] - joined).days) / 7, 0, None)
prior_weeks = np.minimum(prior_weeks, lifetime_weeks)
workouts_before_2024 = rng.poisson(1.4 * engagement * prior_weeks)

# ---- Badges ----------------------------------------------------------------
cum = workouts_before_2024[:, None] + np.cumsum(workouts, axis=1)
crossed = cum >= BADGE_THRESHOLD
cross_week = np.where(crossed.any(axis=1), crossed.argmax(axis=1), -1)
launch_idx = int(np.searchsorted(weeks, BADGE_LAUNCH))
already = workouts_before_2024 >= BADGE_THRESHOLD
cross_date = np.where(already, -2, cross_week)

award_week = np.full(N, -1)
award_type = np.full(N, "", dtype=object)
backfill = already | ((cross_date >= 0) & (cross_date < launch_idx))  # every account past 100, churned or not
organic = (cross_date >= launch_idx) & ~backfill
award_week[backfill] = launch_idx
award_type[backfill] = "backfill"
award_week[organic] = cross_date[organic]
award_type[organic] = "organic"

has_badge = (award_week[:, None] >= 0) & (np.arange(W)[None, :] >= award_week[:, None])
lam_kudos = 1.1 * engagement[:, None] ** 1.2 * season[None, :] * alive * np.where(has_badge, 1 + BADGE_KUDOS_LIFT, 1)
kudos = rng.poisson(lam_kudos)

# ---- Write tables ----------------------------------------------------------
member_ids = np.array([f"m{100000 + i}" for i in range(N)])
pd.DataFrame({"member_id": member_ids, "joined_on": joined.date, "workouts_before_2024": workouts_before_2024}).to_csv(
    OUT / "members.csv", index=False
)

i_idx, w_idx = np.nonzero(sessions + workouts + kudos > 0)
pd.DataFrame(
    {
        "member_id": member_ids[i_idx],
        "week_start": weeks[w_idx].date,
        "sessions": sessions[i_idx, w_idx],
        "workouts_logged": workouts[i_idx, w_idx],
        "kudos_given": kudos[i_idx, w_idx],
        "partner_challenge_views": partner_views[i_idx, w_idx],
    }
).to_csv(OUT / "weekly_activity.csv", index=False)

got = award_week >= 0
pd.DataFrame(
    {
        "member_id": member_ids[got],
        "badge": "century",
        "awarded_on": weeks[award_week[got]].date,
        "award_type": award_type[got],
    }
).to_csv(OUT / "badge_awards.csv", index=False)

# ---- Onboarding email A/B test --------------------------------------------
M = 12_000
ab_rng = np.random.default_rng(24)  # the test gets its own random stream
signed_up = pd.Timestamp("2025-09-01") + pd.to_timedelta(ab_rng.integers(0, 91, M), unit="D")
variant = np.where(ab_rng.random(M) < 0.5, "control", "new_email")
p_first = EMAIL_CONTROL_RATE + np.where(variant == "new_email", EMAIL_TREATMENT_LIFT_PP, 0)
first_workout = ab_rng.random(M) < p_first
active_day_30 = ab_rng.random(M) < np.where(first_workout, 0.55, 0.18)
pd.DataFrame(
    {
        "member_id": [f"n{200000 + i}" for i in range(M)],
        "signed_up_on": signed_up.date,
        "variant": variant,
        "first_workout_7d": first_workout.astype(int),
        "active_day_30": active_day_30.astype(int),
    }
).to_csv(OUT / "onboarding_email_test.csv", index=False)

# Planted truth, for checking the analysis
json.dump(
    {
        "feed_sessions": FEED_SESSION_LIFT,
        "feed_workouts": FEED_WORKOUT_LIFT,
        "feed_partner_views_per_session": FEED_PARTNER_LIFT,
        "badge_kudos": BADGE_KUDOS_LIFT,
        "email_first_workout_pp": EMAIL_TREATMENT_LIFT_PP,
    },
    open(OUT / "planted_effects.json", "w"),
    indent=2,
)
print(f"members: {N:,}  activity rows: {len(i_idx):,}  badges: {got.sum():,} "
      f"(backfill {backfill.sum():,}, organic {organic.sum():,})  email test: {M:,}")
