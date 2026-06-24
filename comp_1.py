# %% [KONTROL] - TAKIM HAFTA BOYUNCA AYNI VARDİYADA MI?

team_col = "takim"

week_df = work_roster.copy()

week_df["tarih_dt"] = pd.to_datetime(week_df["tarih"])
week_df["iso_year"] = week_df["tarih_dt"].dt.isocalendar().year
week_df["iso_week"] = week_df["tarih_dt"].dt.isocalendar().week

week_df["week_key"] = (
    week_df["iso_year"].astype(str)
    + "-W"
    + week_df["iso_week"].astype(str).str.zfill(2)
)

# Takım-gün ana vardiyasını bul
team_day_shift_count = (
    week_df
    .groupby([team_col, "week_key", "tarih", "vardiya"])
    .agg(agent_count=("agent", "nunique"))
    .reset_index()
)

team_day_main_shift = (
    team_day_shift_count
    .sort_values(
        [team_col, "week_key", "tarih", "agent_count"],
        ascending=[True, True, True, False]
    )
    .groupby([team_col, "week_key", "tarih"])
    .head(1)
    .rename(columns={"vardiya": "day_main_vardiya"})
)

# Takım-hafta içinde günlük ana vardiyalar kaç farklı?
team_week_stability = (
    team_day_main_shift
    .groupby([team_col, "week_key"])
    .agg(
        distinct_weekly_main_shift_count=("day_main_vardiya", "nunique"),
        working_day_count=("tarih", "nunique"),
        weekly_main_shifts=("day_main_vardiya", lambda x: sorted(x.unique()))
    )
    .reset_index()
)

team_week_stability_problem_df = (
    team_week_stability[
        team_week_stability["distinct_weekly_main_shift_count"] > 1
    ]
    .sort_values(
        ["distinct_weekly_main_shift_count", "working_day_count"],
        ascending=False
    )
)

display(team_week_stability_problem_df)

print("Toplam takım-hafta sayısı:", len(team_week_stability))
print(
    "Hafta içinde ana vardiyası değişen takım-hafta sayısı:",
    len(team_week_stability_problem_df)
)
