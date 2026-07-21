# Ekiplerin geçmiş + mevcut ay 15:00 vardiya toplamları
# arasındaki farkı azaltma cezası
"TEAM_1500_DENGE_W": 10000,


TEAM_1500_DENGE_W = CONFIG["TEAM_1500_DENGE_W"]

# %% [HAZIRLIK] - EKİP BAZLI GEÇMİŞ 15:00 SAYISI

team_gecmis_1500 = (
    df_tam[
        ["takim", "gecmis_1500_base_hafta_sayisi"]
    ]
    .dropna(subset=["takim"])
    .drop_duplicates(subset=["takim"])
    .set_index("takim")["gecmis_1500_base_hafta_sayisi"]
    .astype(int)
    .to_dict()
)

print(team_gecmis_1500)


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



# %% [DUMMY DATA] - EKİP BAZLI GEÇMİŞ 15:00 VARDİYA SAYISI

import numpy as np
import pandas as pd

GECMIS_1500_KOLONU = "gecmis_1500_base_hafta_sayisi"

# Sonucun her çalıştırmada aynı gelmesi için
rng = np.random.default_rng(seed=42)

# Gerekli kolonları temizle
df_tam["takim"] = (
    df_tam["takim"]
    .astype(str)
    .str.strip()
)

df_tam["sabah_calisir_flg"] = (
    pd.to_numeric(
        df_tam["sabah_calisir_flg"],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)

# -------------------------------------------------
# Takım bazında sabah çalışan ekip kontrolü
# -------------------------------------------------
# Takımın bütün üyeleri sabah_calisir_flg=1 ise
# bu takım 15:00 vardiyasına uygun değildir.

takim_sabah_durumu = (
    df_tam
    .groupby("takim")["sabah_calisir_flg"]
    .agg(
        takim_agent_sayisi="size",
        sabah_calisan_sayisi="sum"
    )
    .reset_index()
)

takim_sabah_durumu["tamami_sabah_calisir"] = (
    takim_sabah_durumu["takim_agent_sayisi"]
    ==
    takim_sabah_durumu["sabah_calisan_sayisi"]
)

# -------------------------------------------------
# Takım bazlı dummy geçmiş değer oluştur
# -------------------------------------------------

team_gecmis_1500_dummy = {}

for _, row in takim_sabah_durumu.iterrows():

    takim = row["takim"]

    if row["tamami_sabah_calisir"]:
        # 15:00 vardiyasına uygun olmayan takım
        gecmis_sayi = 0
    else:
        # Dummy geçmiş sayı
        gecmis_sayi = int(rng.integers(2, 11))

    team_gecmis_1500_dummy[takim] = gecmis_sayi

# Aynı takımın tüm agentlarına aynı değeri yaz
df_tam[GECMIS_1500_KOLONU] = (
    df_tam["takim"]
    .map(team_gecmis_1500_dummy)
    .fillna(0)
    .astype(int)
)

# -------------------------------------------------
# Kontrol tablosu
# -------------------------------------------------

dummy_1500_kontrol_df = (
    df_tam[
        [
            "takim",
            "sabah_calisir_flg",
            GECMIS_1500_KOLONU
        ]
    ]
    .groupby("takim", as_index=False)
    .agg(
        takim_agent_sayisi=("sabah_calisir_flg", "size"),
        sabah_calisan_sayisi=("sabah_calisir_flg", "sum"),
        gecmis_1500_sayisi=(GECMIS_1500_KOLONU, "first"),
        takim_ici_farkli_deger_sayisi=(GECMIS_1500_KOLONU, "nunique")
    )
)

dummy_1500_kontrol_df["tamami_sabah_calisir"] = (
    dummy_1500_kontrol_df["takim_agent_sayisi"]
    ==
    dummy_1500_kontrol_df["sabah_calisan_sayisi"]
)

print("Dummy geçmiş 15:00 kolonu oluşturuldu:", GECMIS_1500_KOLONU)
print("Takım sayısı:", len(dummy_1500_kontrol_df))

display(
    dummy_1500_kontrol_df
    .sort_values(
        ["tamami_sabah_calisir", "gecmis_1500_sayisi", "takim"],
        ascending=[False, True, True]
    )
)


# -------------------------------------------------
# EKİP 15:00 TARİHSEL ADALET CEZASI
# -------------------------------------------------

# Ekiplerin geçmiş + bu ay toplam farkını azalt
objective_terms.append(
    TEAM_1500_DENGE_W
    * team_1500_spread
)

# Geçmişte çok alan ekibin bu ay tekrar seçilmesini azalt
for t in TAKIMLAR:

    t = str(t).strip()

    gecmis_sayi = int(
        team_gecmis_1500.get(t, 0)
    )

    objective_terms.append(
        TEAM_1500_DENGE_W
        * gecmis_sayi
        * team_1500_bu_ay[t]
    )

print("TEAM_1500_DENGE_W:", TEAM_1500_DENGE_W)
