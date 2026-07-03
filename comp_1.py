# -------------------------------------------------
# GEÇEN AY ADİLLİK PARAMETRELERİ
# -------------------------------------------------

# Geçen ay mesai sayısı yüksek olan agentlara bu ay mesai yazmayı pahalılaştırır.
"PM_MESAI_EXTRA_W": 5000,

# Geçen ay gece vardiyası sayısı yüksek olan agentlara bu ay gece yazmayı pahalılaştırır.
"PM_GECE_EXTRA_W": 3000,

# Geçen ay hafta sonu çalışma sayısı yüksek olan agentlara bu ay hafta sonu yazmayı pahalılaştırır.
"PM_HAFTA_SONU_EXTRA_W": 3000,


PM_MESAI_EXTRA_W = CONFIG["PM_MESAI_EXTRA_W"]
PM_GECE_EXTRA_W = CONFIG["PM_GECE_EXTRA_W"]
PM_HAFTA_SONU_EXTRA_W = CONFIG["PM_HAFTA_SONU_EXTRA_W"]


# %% [HÜCRE] - GEÇEN AY ADİLLİK VERİLERİ

# Kolon isimlerini normalize edelim.
# Eğer sende kolon isimleri farklıysa burada eşleştir.
rename_cols = {
    "pm-mesai sayisi": "pm_mesai_sayisi",
    "pm mesai sayisi": "pm_mesai_sayisi",
    "pm_mesai_sayisi": "pm_mesai_sayisi",

    "pm gece sayisi": "pm_gece_sayisi",
    "pm_gece_sayisi": "pm_gece_sayisi",

    "pm hafta sonu calisma sayısı": "pm_hafta_sonu_calisma_sayisi",
    "pm hafta sonu calisma sayisi": "pm_hafta_sonu_calisma_sayisi",
    "pm_hafta_sonu_calisma_sayisi": "pm_hafta_sonu_calisma_sayisi",
}

df_tam = df_tam.rename(columns={
    c: rename_cols[c]
    for c in df_tam.columns
    if c in rename_cols
})

pm_cols = [
    "pm_mesai_sayisi",
    "pm_gece_sayisi",
    "pm_hafta_sonu_calisma_sayisi"
]

for col in pm_cols:
    if col not in df_tam.columns:
        df_tam[col] = 0

    df_tam[col] = (
        pd.to_numeric(df_tam[col], errors="coerce")
        .fillna(0)
        .astype(int)
    )

pm_info = (
    df_tam[
        [
            "agent_user_code",
            "pm_mesai_sayisi",
            "pm_gece_sayisi",
            "pm_hafta_sonu_calisma_sayisi"
        ]
    ]
    .copy()
    .drop_duplicates("agent_user_code")
)

pm_info["agent_user_code"] = (
    pm_info["agent_user_code"]
    .astype(str)
    .str.strip()
)

pm_mesai_map = dict(zip(pm_info["agent_user_code"], pm_info["pm_mesai_sayisi"]))
pm_gece_map = dict(zip(pm_info["agent_user_code"], pm_info["pm_gece_sayisi"]))
pm_hafta_sonu_map = dict(zip(pm_info["agent_user_code"], pm_info["pm_hafta_sonu_calisma_sayisi"]))

print("PM mesai max:", max(pm_mesai_map.values()) if pm_mesai_map else 0)
print("PM gece max:", max(pm_gece_map.values()) if pm_gece_map else 0)
print("PM hafta sonu max:", max(pm_hafta_sonu_map.values()) if pm_hafta_sonu_map else 0)

display(pm_info.head())


# %% [HÜCRE] - BU AY ADİLLİK SAYIM DEĞİŞKENLERİ

# Bu ay kaç gece vardiyası aldı?
bu_ay_gece_sayisi = {}

# Bu ay kaç hafta sonu günü çalıştı?
bu_ay_hafta_sonu_calisma_sayisi = {}

pm_adillik_count_constraints = 0

hafta_sonu_gunleri = sorted([
    ds for ds in PLAN_GUNLER
    if pd.to_datetime(ds).weekday() >= 5
])

for a in AGENTS:
    a = str(a).strip()

    # -----------------------------
    # Bu ay gece vardiyası sayısı
    # -----------------------------
    gece_vars = []

    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if gece_aksam_vardiyasi_mi.get((ds, v), False):
                gece_vars.append(x[(a, ds, v)])

    bu_ay_gece_sayisi[a] = model.NewIntVar(
        0,
        len(gece_vars),
        f"bu_ay_gece_sayisi_{a}"
    )

    model.Add(
        bu_ay_gece_sayisi[a] == sum(gece_vars)
    )
    pm_adillik_count_constraints += 1

    # -----------------------------
    # Bu ay hafta sonu çalışma sayısı
    # -----------------------------
    hafta_sonu_vars = [
        work[(a, ds)]
        for ds in hafta_sonu_gunleri
        if (a, ds) in work
    ]

    bu_ay_hafta_sonu_calisma_sayisi[a] = model.NewIntVar(
        0,
        len(hafta_sonu_vars),
        f"bu_ay_hafta_sonu_calisma_sayisi_{a}"
    )

    model.Add(
        bu_ay_hafta_sonu_calisma_sayisi[a] == sum(hafta_sonu_vars)
    )
    pm_adillik_count_constraints += 1

print("PM adillik sayım kısıtı:", pm_adillik_count_constraints)
print("Hafta sonu gün sayısı:", len(hafta_sonu_gunleri))


# -------------------------------------------------
# GEÇEN AY ADİLLİK CEZALARI
# -------------------------------------------------
# Amaç:
# Geçen ay çok mesai / gece / hafta sonu çalışan agentlara
# bu ay aynı tip yükleri tekrar yazmayı daha pahalı yapmak.
#
# Bu hard kural değildir. Coverage gerekiyorsa model yine bu agentları kullanabilir.

for a in AGENTS:
    a = str(a).strip()

    pm_mesai = pm_mesai_map.get(a, 0)
    pm_gece = pm_gece_map.get(a, 0)
    pm_hafta_sonu = pm_hafta_sonu_map.get(a, 0)

    # -----------------------------
    # Mesai adilliği
    # -----------------------------
    # Geçen ay çok mesai yapan kişiye bu ay mesai yazmak daha pahalı.
    mevcut_ay_mesai_sayisi = sum(
        overtime_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in overtime_week
    )

    objective_terms.append(
        PM_MESAI_EXTRA_W * pm_mesai * mevcut_ay_mesai_sayisi
    )

    # -----------------------------
    # Gece vardiyası adilliği
    # -----------------------------
    # Geçen ay çok gece alan kişiye bu ay gece yazmak daha pahalı.
    if a in bu_ay_gece_sayisi:
        objective_terms.append(
            PM_GECE_EXTRA_W * pm_gece * bu_ay_gece_sayisi[a]
        )

    # -----------------------------
    # Hafta sonu adilliği
    # -----------------------------
    # Geçen ay çok hafta sonu çalışan kişiye bu ay hafta sonu yazmak daha pahalı.
    if a in bu_ay_hafta_sonu_calisma_sayisi:
        objective_terms.append(
            PM_HAFTA_SONU_EXTRA_W * pm_hafta_sonu * bu_ay_hafta_sonu_calisma_sayisi[a]
        )

print("PM_MESAI_EXTRA_W:", PM_MESAI_EXTRA_W)
print("PM_GECE_EXTRA_W:", PM_GECE_EXTRA_W)
print("PM_HAFTA_SONU_EXTRA_W:", PM_HAFTA_SONU_EXTRA_W)


# %% KONTROL - GEÇEN AY / BU AY ADİLLİK KARŞILAŞTIRMA

pm_adillik_rows = []

for a in AGENTS:
    a = str(a).strip()

    bu_ay_mesai = sum(
        solver.Value(overtime_week[(a, wk)])
        for wk in WEEKS
        if (a, wk) in overtime_week
    )

    bu_ay_gece = (
        solver.Value(bu_ay_gece_sayisi[a])
        if a in bu_ay_gece_sayisi
        else 0
    )

    bu_ay_hafta_sonu = (
        solver.Value(bu_ay_hafta_sonu_calisma_sayisi[a])
        if a in bu_ay_hafta_sonu_calisma_sayisi
        else 0
    )

    pm_adillik_rows.append({
        "agent_user_code": a,

        "pm_mesai_sayisi": pm_mesai_map.get(a, 0),
        "bu_ay_mesai_sayisi": bu_ay_mesai,
        "toplam_iki_ay_mesai": pm_mesai_map.get(a, 0) + bu_ay_mesai,

        "pm_gece_sayisi": pm_gece_map.get(a, 0),
        "bu_ay_gece_sayisi": bu_ay_gece,
        "toplam_iki_ay_gece": pm_gece_map.get(a, 0) + bu_ay_gece,

        "pm_hafta_sonu_calisma_sayisi": pm_hafta_sonu_map.get(a, 0),
        "bu_ay_hafta_sonu_calisma_sayisi": bu_ay_hafta_sonu,
        "toplam_iki_ay_hafta_sonu": pm_hafta_sonu_map.get(a, 0) + bu_ay_hafta_sonu,
    })

pm_adillik_df = pd.DataFrame(pm_adillik_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

pm_adillik_df = pm_adillik_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("PM / Bu ay mesai dağılımı:")
display(
    pm_adillik_df[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "pm_mesai_sayisi",
            "bu_ay_mesai_sayisi",
            "toplam_iki_ay_mesai"
        ]
    ]
    .sort_values(["toplam_iki_ay_mesai", "pm_mesai_sayisi"], ascending=False)
    .head(100)
)

print("PM / Bu ay gece dağılımı:")
display(
    pm_adillik_df[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "pm_gece_sayisi",
            "bu_ay_gece_sayisi",
            "toplam_iki_ay_gece"
        ]
    ]
    .sort_values(["toplam_iki_ay_gece", "pm_gece_sayisi"], ascending=False)
    .head(100)
)

print("PM / Bu ay hafta sonu dağılımı:")
display(
    pm_adillik_df[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "pm_hafta_sonu_calisma_sayisi",
            "bu_ay_hafta_sonu_calisma_sayisi",
            "toplam_iki_ay_hafta_sonu"
        ]
    ]
    .sort_values(["toplam_iki_ay_hafta_sonu", "pm_hafta_sonu_calisma_sayisi"], ascending=False)
    .head(100)
)