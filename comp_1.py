# %% [KONTROL] - TAKIM GÜN VARDİYA DAĞILIMI HAM TABLO

tmp = work_roster.copy()

tmp["special_flg"] = (
    (tmp["sabah_calisir_flg"].fillna(0).astype(int) == 1) |
    (tmp["hamile_flg"].fillna(0).astype(int) == 1) |
    (tmp["sut_izni_flg"].fillna(0).astype(int) == 1)
).astype(int)

team_day_shift_raw = (
    tmp
    .groupby(["takim", "tarih", "vardiya"])
    .agg(
        total_agents=("agent", "nunique"),
        normal_agents=("special_flg", lambda x: (x == 0).sum()),
        special_agents=("special_flg", lambda x: (x == 1).sum()),
        agent_list=("agent", lambda x: list(x))
    )
    .reset_index()
    .sort_values(["takim", "tarih", "vardiya"])
)

display(team_day_shift_raw.head(100))

# Aynı takım-günde kaç vardiya var?
split_count_check = (
    team_day_shift_raw
    .groupby(["takim", "tarih"])
    .size()
    .reset_index(name="shift_count")
)

display(split_count_check[split_count_check["shift_count"] > 1])

print("Bölünen takım-gün sayısı:", len(split_count_check[split_count_check["shift_count"] > 1]))
