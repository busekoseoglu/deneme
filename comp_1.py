# %% [KONTROL] - GÜNLÜK TAKIM BÖLÜNMESİ
# Amaç:
# Her takım aynı gün mümkün olduğunca tek vardiyada olmalı.
# Özel durumlu kişiler ayrılabilir:
# sabah_calisir_flg / hamile_flg / sut_izni_flg = 1 olanlar.

team_col = "takim"   # sende takım kolonu bu isimde

check_df = work_roster.copy()

# Gerekli flag kolonları yoksa 0 kabul et
special_flag_cols = [
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg"
]

for col in special_flag_cols:
    if col not in check_df.columns:
        check_df[col] = 0

for col in special_flag_cols:
    check_df[col] = check_df[col].fillna(0).astype(int)

# Özel durumlu kişi flag'i
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
        agent_list=("agent", lambda x: list(x))
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
    [[team_col, "tarih", "vardiya", "total_agents"]]
    .rename(columns={
        "vardiya": "main_vardiya",
        "total_agents": "main_vardiya_agent_count"
    })
)

team_day_detail = team_day_shift.merge(
    main_shift,
    on=[team_col, "tarih"],
    how="left"
)

team_day_detail["is_main_vardiya"] = (
    team_day_detail["vardiya"] == team_day_detail["main_vardiya"]
).astype(int)

# Takım-gün özet
team_day_split_summary = (
    team_day_detail
    .groupby([team_col, "tarih", "main_vardiya", "main_vardiya_agent_count"])
    .agg(
        total_agents=("total_agents", "sum"),
        distinct_shift_count=("vardiya", "nunique"),
        normal_split_agents=(
            "normal_agents",
            lambda x: x[team_day_detail.loc[x.index, "is_main_vardiya"] == 0].sum()
        ),
        special_split_agents=(
            "special_agents",
            lambda x: x[team_day_detail.loc[x.index, "is_main_vardiya"] == 0].sum()
        ),
        shifts_used=("vardiya", lambda x: sorted(x.unique()))
    )
    .reset_index()
)

# Normal ekip bölünmüş mü?
# Ana vardiya dışına çıkan normal agent varsa asıl problem bu.
team_day_split_summary["normal_team_split_problem"] = (
    team_day_split_summary["normal_split_agents"] > 0
).astype(int)

# Özel durum nedeniyle ayrılma var mı?
team_day_split_summary["only_special_split"] = (
    (team_day_split_summary["normal_split_agents"] == 0) &
    (team_day_split_summary["special_split_agents"] > 0)
).astype(int)

# Problemli olanları üste al
team_day_split_summary = team_day_split_summary.sort_values(
    [
        "normal_team_split_problem",
        "normal_split_agents",
        "distinct_shift_count",
        "total_agents"
    ],
    ascending=[False, False, False, False]
)

display(team_day_split_summary)

print("Toplam takım-gün sayısı:", len(team_day_split_summary))
print(
    "Normal ekip bölünmesi olan takım-gün sayısı:",
    team_day_split_summary["normal_team_split_problem"].sum()
)
print(
    "Sadece özel durum nedeniyle ayrılan takım-gün sayısı:",
    team_day_split_summary["only_special_split"].sum()
)
