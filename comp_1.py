# %% [KONTROL] - TAKIM BAZINDA BASE DIŞI ORANI

team_split_summary = (
    roster_base_detail
    .groupby(["hafta", "takim"], as_index=False)
    .agg(
        toplam_calisma=("agent_user_code", "count"),
        base_disi_sayi=("base_disi", "sum"),
        ozel_durumlu_base_disi=("ozel_durumlu", lambda x: x[roster_base_detail.loc[x.index, "base_disi"] == 1].sum())
    )
)

team_split_summary["base_disi_oran"] = (
    team_split_summary["base_disi_sayi"] / team_split_summary["toplam_calisma"]
)

display(
    team_split_summary
    .sort_values("base_disi_sayi", ascending=False)
    .head(50)
)

# %% [KONTROL] - TAKIM GÜN BAZINDA KAÇ VARDİYAYA BÖLÜNMÜŞ?

team_day_split = (
    roster_df
    .groupby(["hafta", "tarih", "gun", "takim"], as_index=False)
    .agg(
        calisan_sayi=("agent_user_code", "nunique"),
        vardiya_sayisi=("vardiya", "nunique")
    )
)

team_day_split["bolundu_mu"] = (team_day_split["vardiya_sayisi"] > 1).astype(int)

print("takım-gün toplam:", len(team_day_split))
print("bölünen takım-gün:", team_day_split["bolundu_mu"].sum())

display(
    team_day_split[team_day_split["bolundu_mu"] == 1]
    .sort_values(["hafta", "tarih", "vardiya_sayisi"], ascending=[True, True, False])
    .head(100)
)

# %% [KONTROL] - BÖLÜNEN TAKIMLARDA VARDİYA DAĞILIMI

split_detail = (
    roster_base_detail
    .groupby(
        [
            "hafta",
            "tarih",
            "gun",
            "takim",
            "base_vardiya",
            "vardiya"
        ],
        as_index=False
    )
    .agg(
        kisi_sayisi=("agent_user_code", "nunique"),
        ozel_durumlu_sayi=("ozel_durumlu", "sum"),
        base_disi_sayi=("base_disi", "sum")
    )
)

# Sadece bölünen takım-günleri al
split_team_days = team_day_split[
    team_day_split["bolundu_mu"] == 1
][["hafta", "tarih", "takim"]]

split_detail = split_detail.merge(
    split_team_days,
    on=["hafta", "tarih", "takim"],
    how="inner"
)

display(
    split_detail
    .sort_values(["hafta", "tarih", "takim", "kisi_sayisi"], ascending=[True, True, True, False])
    .head(150)
)

# %% [KONTROL] - NORMAL KİŞİLERİN BASE DIŞINA ÇIKMASI

normal_base_disi = base_disi_df[
    base_disi_df["ozel_durumlu"] == 0
].copy()

print("normal base dışı satır:", len(normal_base_disi))
print("normal base dışı unique agent:", normal_base_disi["agent_user_code"].nunique())

display(
    normal_base_disi[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "tarih",
            "gun",
            "hafta",
            "vardiya",
            "base_vardiya",
            "is_exception"
        ]
    ]
    .sort_values(["hafta", "takim", "agent_user_code", "tarih"])
    .head(100)
)

# %% [KONTROL] - BASE DIŞI GENEL ÖZET

print("Toplam çalışma satırı:", len(roster_base_detail))
print("Base dışı satır:", roster_base_detail["base_disi"].sum())
print("Base dışı oran:", round(roster_base_detail["base_disi"].mean(), 4))

print("\nBase dışı özel durumlu:", base_disi_df["ozel_durumlu"].sum())
print("Base dışı normal:", len(base_disi_df) - base_disi_df["ozel_durumlu"].sum())

print("\nBölünen takım-gün:", team_day_split["bolundu_mu"].sum())
print("Toplam takım-gün:", len(team_day_split))
print("Bölünme oranı:", round(team_day_split["bolundu_mu"].mean(), 4))
