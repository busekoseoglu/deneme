# %% [DEBUG] - WEEK + VARDİYA PATTERN TALEP / KAPASİTE KONTROLÜ

WEEKLY_WORK_DAYS = 5

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


# Talep tarafı: hafta + vardiya pattern bazında toplam required
demand_rows = []

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)

    for v in gun_vardiyalari.get(ds, []):
        p = get_shift_pattern(ds, v)

        demand_rows.append({
            "week_key": wk,
            "pattern": p,
            "tarih": ds,
            "required": int(talep[(ds, v)])
        })

demand_week_pattern = (
    pd.DataFrame(demand_rows)
    .groupby(["week_key", "pattern"])
    .agg(
        total_required=("required", "sum"),
        max_daily_required=("required", "max"),
        day_count=("tarih", "nunique")
    )
    .reset_index()
)


# Kapasite tarafı:
# Bir agent bir pattern'i seçerse o hafta max 5 gün o pattern'de çalışabilir.
capacity_rows = []

for wk in demand_week_pattern["week_key"].unique():
    days = [ds for ds in PLAN_GUNLER if get_week_key(ds) == wk]

    for p in demand_week_pattern[demand_week_pattern["week_key"] == wk]["pattern"].unique():
        candidate_agents = []

        for a in AGENTS:
            feasible_days = set()

            for ds in days:
                for v in gun_vardiyalari.get(ds, []):
                    if (a, ds, v) not in x:
                        continue

                    if get_shift_pattern(ds, v) == p:
                        feasible_days.add(ds)

            # Bu agent bu pattern'de haftalık çalışma kuralını sağlayabilir mi?
            required_days = min(WEEKLY_WORK_DAYS, len(days))

            if len(feasible_days) >= required_days:
                candidate_agents.append(a)

        capacity_rows.append({
            "week_key": wk,
            "pattern": p,
            "candidate_agent_count": len(candidate_agents),
            "max_weekly_capacity": len(candidate_agents) * min(WEEKLY_WORK_DAYS, len(days))
        })

capacity_week_pattern = pd.DataFrame(capacity_rows)

week_pattern_check = demand_week_pattern.merge(
    capacity_week_pattern,
    on=["week_key", "pattern"],
    how="left"
)

week_pattern_check["capacity_gap"] = (
    week_pattern_check["max_weekly_capacity"]
    - week_pattern_check["total_required"]
)

problem_week_pattern = week_pattern_check[
    week_pattern_check["capacity_gap"] < 0
].sort_values("capacity_gap")

display(problem_week_pattern)

print("Problemli week-pattern sayısı:", len(problem_week_pattern))
display(week_pattern_check.sort_values("capacity_gap").head(30))
