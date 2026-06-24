# %% [DEBUG] - TAKIM HAFTA TEK VARDİYA KAPASİTE KONTROLÜ

team_col = "takim"

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


# Haftalar
week_days = {}
for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


# Agent -> takım
agent_team_map = (
    df_tam
    .assign(agent_user_code=df_tam["agent_user_code"].astype(str).str.strip())
    .set_index("agent_user_code")[team_col]
    .to_dict()
)

team_members = (
    df_tam
    .assign(agent_user_code=df_tam["agent_user_code"].astype(str).str.strip())
    .groupby(team_col)["agent_user_code"]
    .apply(list)
    .to_dict()
)

debug_rows = []

for team, members in team_members.items():
    for wk, days in week_days.items():

        pattern_capacity = {}

        for p in sorted({
            get_shift_pattern(ds, v)
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
        }):
            total_possible_assignments = 0
            possible_agent_days = set()

            for a in members:
                for ds in days:
                    can_work_this_pattern_today = False

                    for v in gun_vardiyalari.get(ds, []):
                        if (a, ds, v) not in x:
                            continue

                        if get_shift_pattern(ds, v) == p:
                            can_work_this_pattern_today = True

                    if can_work_this_pattern_today:
                        total_possible_assignments += 1
                        possible_agent_days.add((a, ds))

            pattern_capacity[p] = {
                "total_possible_assignments": total_possible_assignments,
                "distinct_agent_days": len(possible_agent_days)
            }

        if not pattern_capacity:
            continue

        best_pattern = max(
            pattern_capacity,
            key=lambda p: pattern_capacity[p]["distinct_agent_days"]
        )

        debug_rows.append({
            "takim": team,
            "week_key": wk,
            "team_size": len(members),
            "best_pattern": best_pattern,
            "best_pattern_possible_agent_days": pattern_capacity[best_pattern]["distinct_agent_days"],
            "all_pattern_capacity": pattern_capacity
        })

team_week_capacity_debug = pd.DataFrame(debug_rows)

display(team_week_capacity_debug.head(50))
