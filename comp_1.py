# Ekiplerin geçmiş + mevcut ay 15:00 vardiya toplamları
# arasındaki farkı azaltma cezası
"TEAM_1500_DENGE_W": 10000,


TEAM_1500_DENGE_W = CONFIG["TEAM_1500_DENGE_W"]


# %% [HAZIRLIK] - EKİP BAZLI GEÇMİŞ 15:00 VARDİYA SAYISI

GECMIS_1500_KOLONU = "gecmis_1500_base_hafta_sayisi"

if GECMIS_1500_KOLONU not in df_tam.columns:
    raise ValueError(
        f"df_tam içinde '{GECMIS_1500_KOLONU}' kolonu bulunamadı."
    )

gecmis_1500_kontrol_df = (
    df_tam[
        [
            "takim",
            GECMIS_1500_KOLONU
        ]
    ]
    .dropna(subset=["takim"])
    .copy()
)

gecmis_1500_kontrol_df["takim"] = (
    gecmis_1500_kontrol_df["takim"]
    .astype(str)
    .str.strip()
)

gecmis_1500_kontrol_df[GECMIS_1500_KOLONU] = (
    pd.to_numeric(
        gecmis_1500_kontrol_df[GECMIS_1500_KOLONU],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)


# Aynı ekipte farklı geçmiş değer girilmiş mi kontrol et
takim_gecmis_deger_sayisi = (
    gecmis_1500_kontrol_df
    .groupby("takim")[GECMIS_1500_KOLONU]
    .nunique()
)

tutarsiz_takimlar = takim_gecmis_deger_sayisi[
    takim_gecmis_deger_sayisi > 1
]

if len(tutarsiz_takimlar) > 0:
    tutarsiz_detay = (
        gecmis_1500_kontrol_df[
            gecmis_1500_kontrol_df["takim"].isin(
                tutarsiz_takimlar.index
            )
        ]
        .drop_duplicates()
        .sort_values(
            ["takim", GECMIS_1500_KOLONU]
        )
    )

    display(tutarsiz_detay)

    raise ValueError(
        "Aynı ekipte farklı geçmiş 15:00 sayıları var. "
        "Bir ekibin bütün agentlarında aynı değer bulunmalı."
    )


team_gecmis_1500 = (
    gecmis_1500_kontrol_df
    .drop_duplicates(subset=["takim"])
    .set_index("takim")[GECMIS_1500_KOLONU]
    .to_dict()
)


print("Geçmiş 15:00 bilgisi olan ekip sayısı:", len(team_gecmis_1500))

display(
    pd.DataFrame(
        [
            {
                "takim": t,
                "gecmis_1500_sayisi": team_gecmis_1500[t]
            }
            for t in sorted(team_gecmis_1500)
        ]
    )
)


# %% [HAZIRLIK] - HAFTA BAZINDA 15:00 BAŞLANGIÇLI VARDİYALAR

week_days_1500 = {
    wk: [
        ds
        for ds in PLAN_GUNLER
        if day_week[ds] == wk
    ]
    for wk in WEEKS
}

week_1500_vardiyalari = {}

for wk in WEEKS:

    vardiyalar_1500 = set()

    for v in week_vardiyalari.get(wk, []):

        for ds in week_days_1500[wk]:

            if (ds, v) not in saat:
                continue

            baslangic, bitis = saat[(ds, v)]

            if str(baslangic).strip()[:5] == "15:00":
                vardiyalar_1500.add(v)
                break

    week_1500_vardiyalari[wk] = sorted(vardiyalar_1500)


print("Hafta bazlı 15:00 vardiyaları:")

for wk in WEEKS:
    print(wk, "->", week_1500_vardiyalari[wk])


# %% [KARAR DEĞİŞKENİ] - EKİP 15:00 GEÇMİŞ + BU AY TOPLAMI

team_1500_bu_ay = {}
team_1500_toplam = {}

team_1500_max_toplam_possible = (
    max(team_gecmis_1500.values(), default=0)
    + len(WEEKS)
)

team_1500_link_constraints = 0


for t in TAKIMLAR:

    t = str(t).strip()

    gecmis_sayi = int(
        team_gecmis_1500.get(t, 0)
    )

    bu_ay_1500_vars = []

    for wk in WEEKS:

        for v in week_1500_vardiyalari.get(wk, []):

            if (t, wk, v) in team_week_base:
                bu_ay_1500_vars.append(
                    team_week_base[(t, wk, v)]
                )

    team_1500_bu_ay[t] = model.NewIntVar(
        0,
        len(WEEKS),
        f"team_1500_bu_ay_{t}"
    )

    if bu_ay_1500_vars:
        model.Add(
            team_1500_bu_ay[t]
            ==
            sum(bu_ay_1500_vars)
        )
    else:
        model.Add(
            team_1500_bu_ay[t] == 0
        )

    team_1500_toplam[t] = model.NewIntVar(
        gecmis_sayi,
        gecmis_sayi + len(WEEKS),
        f"team_1500_toplam_{t}"
    )

    model.Add(
        team_1500_toplam[t]
        ==
        gecmis_sayi + team_1500_bu_ay[t]
    )

    team_1500_link_constraints += 2


print("Ekip 15:00 bağlantı kısıtı:", team_1500_link_constraints)
print("Ekip sayısı:", len(team_1500_toplam))



# %% [KISIT] - EKİPLER ARASI 15:00 TOPLAM FARKI

if not team_1500_toplam:
    raise ValueError(
        "team_1500_toplam boş. "
        "Önce ekip 15:00 karar değişkeni hücresini çalıştır."
    )

team_1500_max = model.NewIntVar(
    0,
    team_1500_max_toplam_possible,
    "team_1500_max"
)

team_1500_min = model.NewIntVar(
    0,
    team_1500_max_toplam_possible,
    "team_1500_min"
)

team_1500_spread = model.NewIntVar(
    0,
    team_1500_max_toplam_possible,
    "team_1500_spread"
)

model.AddMaxEquality(
    team_1500_max,
    list(team_1500_toplam.values())
)

model.AddMinEquality(
    team_1500_min,
    list(team_1500_toplam.values())
)

model.Add(
    team_1500_spread
    ==
    team_1500_max - team_1500_min
)

print("15:00 ekip denge değişkenleri oluşturuldu.")


# -------------------------------------------------
# EKİP 15:00 TARİHSEL ADALET CEZASI
# -------------------------------------------------

objective_terms.append(
    TEAM_1500_DENGE_W
    * team_1500_spread
)

print("TEAM_1500_DENGE_W:", TEAM_1500_DENGE_W)


# %% KONTROL - EKİP BAZLI 15:00 TARİHSEL ADALET

team_1500_kontrol_rows = []

for t in TAKIMLAR:

    t = str(t).strip()

    gecmis_sayi = int(
        team_gecmis_1500.get(t, 0)
    )

    bu_ay_sayi = solver.Value(
        team_1500_bu_ay[t]
    )

    toplam_sayi = solver.Value(
        team_1500_toplam[t]
    )

    secilen_haftalar = []

    for wk in WEEKS:

        for v in week_1500_vardiyalari.get(wk, []):

            if (t, wk, v) not in team_week_base:
                continue

            if solver.Value(
                team_week_base[(t, wk, v)]
            ) == 1:
                secilen_haftalar.append(
                    f"{wk}:{v}"
                )

    team_1500_kontrol_rows.append({
        "takim": t,
        "gecmis_1500_sayisi": gecmis_sayi,
        "bu_ay_1500_sayisi": bu_ay_sayi,
        "gecmis_artı_bu_ay_toplam": toplam_sayi,
        "bu_ay_1500_haftalari": " | ".join(secilen_haftalar)
    })


team_1500_kontrol_df = (
    pd.DataFrame(team_1500_kontrol_rows)
    .sort_values(
        [
            "gecmis_artı_bu_ay_toplam",
            "takim"
        ]
    )
    .reset_index(drop=True)
)

print(
    "Geçmiş + bu ay minimum:",
    solver.Value(team_1500_min)
)

print(
    "Geçmiş + bu ay maksimum:",
    solver.Value(team_1500_max)
)

print(
    "Ekipler arası toplam fark:",
    solver.Value(team_1500_spread)
)

display(team_1500_kontrol_df)
