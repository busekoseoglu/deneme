# %% [KONTROL 10] - TEAM + HAFTA ANA VARDİYA VE SAPMALAR

pattern_counts = (
    team_week_check
    .groupby(["team", "week_key", "vardiya"])
    .size()
    .reset_index(name="assignment_count")
)

# Her team-week için en çok kullanılan vardiya = main pattern
main_patterns = (
    pattern_counts
    .sort_values(["team", "week_key", "assignment_count"], ascending=[True, True, False])
    .groupby(["team", "week_key"])
    .head(1)
    .rename(columns={
        "vardiya": "main_vardiya",
        "assignment_count": "main_assignment_count"
    })
)

team_week_detail = team_week_check.merge(
    main_patterns[["team", "week_key", "main_vardiya"]],
    on=["team", "week_key"],
    how="left"
)

team_week_detail["is_main_vardiya"] = (
    team_week_detail["vardiya"] == team_week_detail["main_vardiya"]
).astype(int)

team_week_split_summary = (
    team_week_detail
    .groupby(["team", "week_key", "main_vardiya"])
    .agg(
        total_assignment=("vardiya", "count"),
        main_assignment=("is_main_vardiya", "sum"),
        split_assignment=("is_main_vardiya", lambda x: (x == 0).sum()),
        agent_count=("agent", "nunique"),
        distinct_shift_count=("vardiya", "nunique")
    )
    .reset_index()
)

team_week_split_summary["split_rate"] = (
    team_week_split_summary["split_assignment"]
    / team_week_split_summary["total_assignment"]
)

team_week_split_summary = team_week_split_summary.sort_values(
    ["split_assignment", "split_rate"],
    ascending=False
)

display(team_week_split_summary.head(30))

print("Toplam team-week sayısı:", len(team_week_split_summary))
print("Split olan team-week sayısı:", len(team_week_split_summary[team_week_split_summary["split_assignment"] > 0]))


# %% [KONTROL 11] - TEAM HAFTALIK ANA VARDİYA DIŞINA ÇIKAN AGENT DETAYI

team_split_detail_df = team_week_detail[
    team_week_detail["is_main_vardiya"] == 0
].copy()

team_split_detail_df = team_split_detail_df[
    [
        "team",
        "week_key",
        "agent",
        "agent_name",
        "tarih",
        "vardiya",
        "main_vardiya",
        "sabah_calisir_flg",
        "hamile_flg",
        "sut_izni_flg"
    ]
].sort_values(
    ["team", "week_key", "tarih", "agent"]
)

display(team_split_detail_df.head(100))

print("Ana vardiya dışına çıkan toplam atama:", len(team_split_detail_df))


# %% [KONTROL 12] - TEAM + GÜN BAZINDA KAÇ FARKLI VARDİYA VAR?

team_day_summary = (
    work_roster
    .groupby(["team", "tarih"])
    .agg(
        distinct_shift_count=("vardiya", "nunique"),
        total_assignment=("vardiya", "count"),
        agent_count=("agent", "nunique")
    )
    .reset_index()
)

team_day_problem_df = team_day_summary[
    team_day_summary["distinct_shift_count"] > 1
].sort_values(
    ["distinct_shift_count", "total_assignment"],
    ascending=False
)

display(team_day_problem_df.head(50))

print("Aynı gün birden fazla vardiyaya bölünen team-day sayısı:", len(team_day_problem_df))
