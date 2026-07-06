# %% KONTROL - V01 00:00-08:00 İÇİN TAKIM BASE SEÇİMİ VE KAPASİTE

v01_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        if (ds, v) not in saat:
            continue

        bas, bit = saat[(ds, v)]

        if bas != "00:00" or bit != "08:00":
            continue

        wk = day_week[ds]
        required = int(talep[(ds, v)])

        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        # Bu vardiyaya x değişkeni olan agent sayısı
        x_agent_count = sum(
            1
            for a in AGENTS
            if (a, ds, v) in x
        )

        # Bu vardiyada base seçmiş takımlar
        selected_teams = []
        selected_team_agent_count = 0

        for t in TAKIMLAR:
            if (t, wk, v) in team_week_base and solver.Value(team_week_base[(t, wk, v)]) == 1:
                selected_teams.append(t)

                selected_team_agent_count += sum(
                    1
                    for a in AGENTS
                    if str(agent_team.get(str(a).strip(), "")).strip() == str(t).strip()
                )

        v01_rows.append({
            "date": ds,
            "week": wk,
            "shift": v,
            "start": bas,
            "end": bit,
            "required": required,
            "assigned": assigned,
            "gap": assigned - required,
            "x_agent_count": x_agent_count,
            "selected_team_count": len(selected_teams),
            "selected_team_agent_count": selected_team_agent_count,
            "selected_teams": selected_teams
        })

v01_debug_df = pd.DataFrame(v01_rows)

display(
    v01_debug_df
    .sort_values(["date"])
)


# %% KONTROL - HAFTALIK TAKIM BASE VARDİYA DAĞILIMI

team_base_rows = []

for t in TAKIMLAR:
    for wk in WEEKS:
        for v in week_vardiyalari[wk]:

            if (t, wk, v) not in team_week_base:
                continue

            if solver.Value(team_week_base[(t, wk, v)]) != 1:
                continue

            bas, bit = None, None

            for ds in week_days[wk]:
                if (ds, v) in saat:
                    bas, bit = saat[(ds, v)]
                    break

            team_size = sum(
                1
                for a in AGENTS
                if str(agent_team.get(str(a).strip(), "")).strip() == str(t).strip()
            )

            team_base_rows.append({
                "week": wk,
                "team": t,
                "base_shift": v,
                "start": bas,
                "end": bit,
                "team_size": team_size,
                "is_v01_night": bas == "00:00" and bit == "08:00"
            })

team_base_debug_df = pd.DataFrame(team_base_rows)

display(
    team_base_debug_df
    .groupby(["week", "base_shift", "start", "end"], as_index=False)
    .agg(
        team_count=("team", "nunique"),
        total_team_size=("team_size", "sum")
    )
    .sort_values(["week", "start", "end"])
)


