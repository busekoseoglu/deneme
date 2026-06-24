# %% [DEBUG] - HAFTALIK VARDİYA PATTERN BAZLI MINIMUM AGENT İHTİYACI

import math
import pandas as pd

WEEKLY_WORK_DAYS = 5

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"

def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"

rows = []

for wk in sorted({get_week_key(ds) for ds in PLAN_GUNLER}):
    days = [ds for ds in PLAN_GUNLER if get_week_key(ds) == wk]

    patterns = sorted({
        get_shift_pattern(ds, v)
        for ds in days
        for v in gun_vardiyalari.get(ds, [])
    })

    week_total_min_agents = 0

    for p in patterns:
        daily_reqs = []

        for ds in days:
            req_day = 0

            for v in gun_vardiyalari.get(ds, []):
                if get_shift_pattern(ds, v) == p:
                    req_day += int(talep[(ds, v)])

            daily_reqs.append(req_day)

        total_required = sum(daily_reqs)
        max_daily_required = max(daily_reqs)

        # Bir agent haftada max 5 gün bu pattern'de çalışabilir.
        # Ayrıca herhangi bir günde talep kaçsa, o gün o kadar agent gerekir.
        min_agents_by_total = math.ceil(total_required / WEEKLY_WORK_DAYS)
        min_agents_by_peak_day = max_daily_required

        min_agents_needed = max(min_agents_by_total, min_agents_by_peak_day)

        week_total_min_agents += min_agents_needed

        rows.append({
            "week_key": wk,
            "pattern": p,
            "days_in_week": len(days),
            "total_required": total_required,
            "max_daily_required": max_daily_required,
            "min_agents_by_total": min_agents_by_total,
            "min_agents_by_peak_day": min_agents_by_peak_day,
            "min_agents_needed": min_agents_needed
        })

pattern_need_df = pd.DataFrame(rows)

week_need_summary = (
    pattern_need_df
    .groupby("week_key")
    .agg(
        total_min_agents_needed=("min_agents_needed", "sum"),
        total_required=("total_required", "sum")
    )
    .reset_index()
)

week_need_summary["available_agents"] = len(AGENTS)
week_need_summary["agent_gap"] = (
    week_need_summary["available_agents"]
    - week_need_summary["total_min_agents_needed"]
)

display(pattern_need_df.sort_values(["week_key", "min_agents_needed"], ascending=[True, False]))
display(week_need_summary)

print("Agent yetmeyen hafta sayısı:", len(week_need_summary[week_need_summary["agent_gap"] < 0]))
