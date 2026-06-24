# %% [KONTROL] - GÜNLÜK TAKIM BÖLÜNMESİ KONTROLÜ

team_col = "takim"

check_df = work_roster.copy()

# Özel durum flagleri yoksa 0 kabul et
special_cols = ["sabah_calisir_flg", "hamile_flg", "sut_izni_flg"]

for col in special_cols:
    if col not in check_df.columns:
        check_df[col] = 0

for col in special_cols:
    check_df[col] = check_df[col].fillna(0).astype(int)

check_df["special_flg"] = (
    (check_df["sabah_calisir_flg"] == 1) |
    (check_df["hamile_flg"] == 1) |
    (check_df["sut_izni_flg"] == 1)
).astype(int)

# Her takım-gün-vardiya kaç kişi var?
team_day_shift = (
    check_df
    .groupby([team_col, "tarih", "vardiya"])
    .agg(
        total_agents=("agent", "nunique"),
        normal_agents=("special_flg", lambda x: (x == 0).sum()),
        special_agents=("special_flg", lambda x: (x == 1).sum()),
        agents=("agent", lambda x: list(x))
    )
    .reset_index()
)

# Her takım-gün için ana vardiya = en çok kişinin olduğu vardiya
main_shift = (
    team_day_shift
    .sort_values(
        [team_col, "tarih", "total_agents"],
        ascending=[True, True, False]
    )
    .groupby([team_col, "tarih"])
    .head(1)
    [[team_col, "tarih", "vardiya"]]
    .rename(columns={"vardiya": "main_vardiya"})
)

team_day_shift = team_day_shift.merge(
    main_shift,
    on=[team_col, "tarih"],
    how="left"
)

team_day_shift["is_main_shift"] = (
    team_day_shift["vardiya"] == team_day_shift["main_vardiya"]
).astype(int)

# Takım-gün özet
team_day_summary = (
    team_day_shift
    .groupby([team_col, "tarih", "main_vardiya"])
    .agg(
        total_working_agents=("total_agents", "sum"),
        distinct_shift_count=("vardiya", "nunique"),
        normal_split_agents=(
            "normal_agents",
            lambda x: x[team_day_shift.loc[x.index, "is_main_shift"] == 0].sum()
        ),
        special_split_agents=(
            "special_agents",
            lambda x: x[team_day_shift.loc[x.index, "is_main_shift"] == 0].sum()
        ),
        shifts_used=("vardiya", lambda x: sorted(x.unique()))
    )
    .reset_index()
)

team_day_summary["normal_split_problem"] = (
    team_day_summary["normal_split_agents"] > 0
).astype(int)

team_day_summary["only_special_split"] = (
    (team_day_summary["normal_split_agents"] == 0) &
    (team_day_summary["special_split_agents"] > 0)
).astype(int)

# En problemli olanları üste al
team_day_summary = team_day_summary.sort_values(
    [
        "normal_split_problem",
        "normal_split_agents",
        "distinct_shift_count",
        "total_working_agents"
    ],
    ascending=[False, False, False, False]
)

display(team_day_summary)

print("Toplam takım-gün sayısı:", len(team_day_summary))
print("Bölünen takım-gün sayısı:", len(team_day_summary[team_day_summary["distinct_shift_count"] > 1]))
print("Normal ekip bölünmesi olan takım-gün sayısı:", team_day_summary["normal_split_problem"].sum())
print("Sadece özel durum nedeniyle ayrılan takım-gün sayısı:", team_day_summary["only_special_split"].sum())
