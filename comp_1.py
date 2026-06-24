# %% [DEBUG] - TAKIM HAFTA TEK VARDİYA MÜMKÜN MÜ? OKUNUR ÖZET

team_col = "takim"
WEEKLY_WORK_DAYS = 5

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


# Haftaları oluştur
week_days = {}
for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


team_members = (
    df_tam
    .assign(agent_user_code=df_tam["agent_user_code"].astype(str).str.strip())
    .groupby(team_col)["agent_user_code"]
    .apply(lambda x: [str(a).strip() for a in x])
    .to_dict()
)


debug_rows = []

for team, members in team_members.items():
    for wk, days in week_days.items():

        # O hafta kaç gün var?
        week_day_count = len(days)

        # Herkes 5 gün çalışacak ama hafta eksikse hafta gün sayısı kadar
        required_days_per_agent = min(WEEKLY_WORK_DAYS, week_day_count)
        required_agent_days = len(members) * required_days_per_agent

        pattern_capacity_rows = []

        patterns = sorted({
            get_shift_pattern(ds, v)
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
        })

        for p in patterns:
            possible_agent_days = set()

            for a in members:
                for ds in days:
                    can_work_pattern_that_day = False

                    for v in gun_vardiyalari.get(ds, []):
                        if (a, ds, v) not in x:
                            continue

                        if get_shift_pattern(ds, v) == p:
                            can_work_pattern_that_day = True

                    if can_work_pattern_that_day:
                        possible_agent_days.add((a, ds))

            pattern_capacity_rows.append({
                "pattern": p,
                "possible_agent_days": len(possible_agent_days)
            })

        if not pattern_capacity_rows:
            continue

        pattern_capacity_df = pd.DataFrame(pattern_capacity_rows)

        best_row = pattern_capacity_df.sort_values(
            "possible_agent_days",
            ascending=False
        ).iloc[0]

        best_pattern = best_row["pattern"]
        best_capacity = int(best_row["possible_agent_days"])

        debug_rows.append({
            "takim": team,
            "week_key": wk,
            "team_size": len(members),
            "week_day_count": week_day_count,
            "required_days_per_agent": required_days_per_agent,
            "required_agent_days": required_agent_days,
            "best_pattern": best_pattern,
            "best_pattern_possible_agent_days": best_capacity,
            "gap": best_capacity - required_agent_days,
            "feasible_team_week_same_shift": best_capacity >= required_agent_days
        })


team_week_feasibility_summary = pd.DataFrame(debug_rows)

problem_team_weeks = team_week_feasibility_summary[
    team_week_feasibility_summary["feasible_team_week_same_shift"] == False
].sort_values(
    ["gap", "required_agent_days"],
    ascending=[True, False]
)

display(problem_team_weeks)

print("Toplam takım-hafta:", len(team_week_feasibility_summary))
print("Tek vardiya hard kuralı kapasite olarak mümkün olmayan takım-hafta:", len(problem_team_weeks))
