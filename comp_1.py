# %% [KONTROL 9] - TEAM + HAFTA KAÇ FARKLI VARDİYA KULLANMIŞ?

team_week_check = work_roster.copy()

team_week_check["tarih_dt"] = pd.to_datetime(team_week_check["tarih"])
team_week_check["iso_year"] = team_week_check["tarih_dt"].dt.isocalendar().year
team_week_check["iso_week"] = team_week_check["tarih_dt"].dt.isocalendar().week
team_week_check["week_key"] = (
    team_week_check["iso_year"].astype(str)
    + "-W"
    + team_week_check["iso_week"].astype(str).str.zfill(2)
)

team_week_summary = (
    team_week_check
    .groupby(["team", "week_key"])
    .agg(
        distinct_shift_count=("vardiya", "nunique"),
        total_assignment=("vardiya", "count"),
        agent_count=("agent", "nunique")
    )
    .reset_index()
)

team_week_problem_df = team_week_summary[
    team_week_summary["distinct_shift_count"] > 1
].sort_values(
    ["distinct_shift_count", "total_assignment"],
    ascending=False
)

display(team_week_problem_df)

print("Bir haftada birden fazla vardiya kullanan team-week sayısı:", len(team_week_problem_df))
