# %% KONTROL - EN BÜYÜK HAFTALIK UNDER SAPMALARI

weekly_deviation_rows = []

for (a, wk), under_var in weekly_under.items():

    under_val = solver.Value(under_var)
    over_val = solver.Value(weekly_over[(a, wk)])

    if under_val == 0 and over_val == 0:
        continue

    week_days_list = week_days[wk]

    actual_work_days = sum(
        solver.Value(work[(a, ds)])
        for ds in week_days_list
        if (a, ds) in work
    )

    overtime_val = (
        solver.Value(overtime_week[(a, wk)])
        if (a, wk) in overtime_week
        else None
    )

    weekly_deviation_rows.append({
        "agent_user_code": a,
        "week": wk,
        "actual_work_days": actual_work_days,
        "overtime_week": overtime_val,
        "weekly_under": under_val,
        "weekly_over": over_val,
    })

weekly_deviation_df = pd.DataFrame(weekly_deviation_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg",
    "sabah_calisir_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

weekly_deviation_df = weekly_deviation_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

display(
    weekly_deviation_df
    .sort_values(["weekly_under", "week", "takim"], ascending=[False, True, True])
    .head(100)
)