# -------------------------------------------------
# HAFTA SONU ÇALIŞMA ADİL DAĞITIM PARAMETRELERİ
# -------------------------------------------------

# Bir agent için ay içinde ideal minimum hafta sonu çalışma günü.
# Amaç: Bazı agentların tüm hafta sonlarını OFF geçirmesini azaltmak.
"HAFTA_SONU_IDEAL_MIN_CALISMA": 2,

# Bir agent için ay içinde ideal maksimum hafta sonu çalışma günü.
# Amaç: Aynı agentın çok fazla hafta sonu çalışmasını azaltmak.
"HAFTA_SONU_IDEAL_MAX_CALISMA": 3,

# 3 günden fazla hafta sonu çalışmaya verilen ceza.
# Yüksek tutulur çünkü asıl istemediğimiz şey bu.
"HAFTA_SONU_FAZLA_CALISMA_W": 80000,

# 2 günden az hafta sonu çalışmaya verilen ceza.
# Daha düşük tutulur çünkü bazı agentların hafta sonu çalışmaması operasyonel olarak gerekebilir.
"HAFTA_SONU_AZ_CALISMA_W": 15000,


HAFTA_SONU_IDEAL_MIN_CALISMA = CONFIG["HAFTA_SONU_IDEAL_MIN_CALISMA"]
HAFTA_SONU_IDEAL_MAX_CALISMA = CONFIG["HAFTA_SONU_IDEAL_MAX_CALISMA"]
HAFTA_SONU_FAZLA_CALISMA_W = CONFIG["HAFTA_SONU_FAZLA_CALISMA_W"]
HAFTA_SONU_AZ_CALISMA_W = CONFIG["HAFTA_SONU_AZ_CALISMA_W"]


# %% [HÜCRE] - HAFTA SONU ÇALIŞMA ADİL DAĞITIMI
# Amaç:
# Her agentın ay içindeki hafta sonu çalışma günü sayısını dengeli tutmak.
#
# Mevcut hard kural devam ediyor:
# Her agent ayda en az 1 Cumartesi-Pazar peş peşe OFF almak zorunda.
#
# Yeni soft mantık:
# - İdeal hafta sonu çalışma günü: 2-3 gün
# - 3 günden fazla hafta sonu çalışırsa yüksek ceza
# - 2 günden az hafta sonu çalışırsa daha düşük ceza
#
# Hamile / süt izni olan agentlar hafta sonu çalışamadığı için
# bu fairness cezasından hariç tutulur.

# Hafta sonu günlerini tekilleştir
hafta_sonu_gunleri = sorted(
    set(
        [sat_ds for sat_ds, sun_ds in weekend_pairs] +
        [sun_ds for sat_ds, sun_ds in weekend_pairs]
    )
)

# Hafta sonu çalışması zaten yasak olan agentlar
hafta_sonu_calisamaz_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

# Agent bazlı hafta sonu çalışma sayısı ve sapma değişkenleri
hafta_sonu_calisma_sayisi = {}
fazla_hafta_sonu_calisma = {}
az_hafta_sonu_calisma = {}

hafta_sonu_adalet_constraints = 0

max_hafta_sonu_gun_sayisi = len(hafta_sonu_gunleri)

for a in AGENTS:
    a = str(a).strip()

    # Hamile / süt izni gibi hafta sonu çalışamayan agentları fairness cezasından çıkarıyoruz.
    if a in hafta_sonu_calisamaz_agents:
        continue

    hafta_sonu_calisma_sayisi[a] = model.NewIntVar(
        0,
        max_hafta_sonu_gun_sayisi,
        f"hafta_sonu_calisma_sayisi_{a}"
    )

    fazla_hafta_sonu_calisma[a] = model.NewIntVar(
        0,
        max_hafta_sonu_gun_sayisi,
        f"fazla_hafta_sonu_calisma_{a}"
    )

    az_hafta_sonu_calisma[a] = model.NewIntVar(
        0,
        max_hafta_sonu_gun_sayisi,
        f"az_hafta_sonu_calisma_{a}"
    )

    # Agentın ay içindeki toplam hafta sonu çalışma günü
    model.Add(
        hafta_sonu_calisma_sayisi[a]
        ==
        sum(
            work[(a, ds)]
            for ds in hafta_sonu_gunleri
            if (a, ds) in work
        )
    )
    hafta_sonu_adalet_constraints += 1

    # 3 günden fazla hafta sonu çalışırsa fazla_hafta_sonu_calisma pozitif olur.
    model.Add(
        fazla_hafta_sonu_calisma[a]
        >=
        hafta_sonu_calisma_sayisi[a] - HAFTA_SONU_IDEAL_MAX_CALISMA
    )
    hafta_sonu_adalet_constraints += 1

    # 2 günden az hafta sonu çalışırsa az_hafta_sonu_calisma pozitif olur.
    model.Add(
        az_hafta_sonu_calisma[a]
        >=
        HAFTA_SONU_IDEAL_MIN_CALISMA - hafta_sonu_calisma_sayisi[a]
    )
    hafta_sonu_adalet_constraints += 1

print("Hafta sonu gün sayısı:", len(hafta_sonu_gunleri))
print("Hafta sonu çalışamaz agent sayısı:", len(hafta_sonu_calisamaz_agents))
print("Hafta sonu adalet değişkeni olan agent sayısı:", len(hafta_sonu_calisma_sayisi))
print("Hafta sonu adalet kısıtı:", hafta_sonu_adalet_constraints)
print("İdeal hafta sonu çalışma aralığı:", HAFTA_SONU_IDEAL_MIN_CALISMA, "-", HAFTA_SONU_IDEAL_MAX_CALISMA)


# -------------------------------------------------
# HAFTA SONU ÇALIŞMA ADİL DAĞITIM CEZASI
# -------------------------------------------------
# Amaç:
# Hafta sonu çalışma yükü aynı agentlara yığılmasın.
#
# 3 günden fazla hafta sonu çalışma yüksek cezalı.
# 2 günden az hafta sonu çalışma daha düşük cezalı.
#
# Hamile / süt izni agentlar bu değişkenlere dahil edilmediği için
# burada otomatik olarak cezalanmaz.

for a in hafta_sonu_calisma_sayisi.keys():

    objective_terms.append(
        HAFTA_SONU_FAZLA_CALISMA_W * fazla_hafta_sonu_calisma[a]
    )

    objective_terms.append(
        HAFTA_SONU_AZ_CALISMA_W * az_hafta_sonu_calisma[a]
    )

print("HAFTA_SONU_FAZLA_CALISMA_W:", HAFTA_SONU_FAZLA_CALISMA_W)
print("HAFTA_SONU_AZ_CALISMA_W:", HAFTA_SONU_AZ_CALISMA_W)


# %% KONTROL - HAFTA SONU ÇALIŞMA ADİL DAĞITIM

hafta_sonu_adalet_rows = []

for a in AGENTS:
    a = str(a).strip()

    hafta_sonu_calisma_gunu = 0
    cumartesi_calisma = 0
    pazar_calisma = 0
    cift_off_sayisi = 0

    for sat_ds, sun_ds in weekend_pairs:
        sat_work = solver.Value(work[(a, sat_ds)])
        sun_work = solver.Value(work[(a, sun_ds)])

        cumartesi_calisma += sat_work
        pazar_calisma += sun_work
        hafta_sonu_calisma_gunu += sat_work + sun_work

        if sat_work == 0 and sun_work == 0:
            cift_off_sayisi += 1

    hafta_sonu_adalet_rows.append({
        "agent_user_code": a,
        "toplam_hafta_sonu_calisma_gunu": hafta_sonu_calisma_gunu,
        "cumartesi_calisma_gunu": cumartesi_calisma,
        "pazar_calisma_gunu": pazar_calisma,
        "toplam_cmt_paz_cift_off": cift_off_sayisi,
        "min_1_cift_off_ok": cift_off_sayisi >= 1,
        "hafta_sonu_calisamaz_agent": a in hafta_sonu_calisamaz_agents,
        "ideal_aralikta_mi": (
            (hafta_sonu_calisma_gunu >= HAFTA_SONU_IDEAL_MIN_CALISMA) and
            (hafta_sonu_calisma_gunu <= HAFTA_SONU_IDEAL_MAX_CALISMA)
        ),
        "fazla_hafta_sonu_calisma": max(0, hafta_sonu_calisma_gunu - HAFTA_SONU_IDEAL_MAX_CALISMA),
        "az_hafta_sonu_calisma": max(0, HAFTA_SONU_IDEAL_MIN_CALISMA - hafta_sonu_calisma_gunu)
    })

hafta_sonu_adalet_df = pd.DataFrame(hafta_sonu_adalet_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "hamile_flg",
    "sut_izni_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

hafta_sonu_adalet_df = hafta_sonu_adalet_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Min 1 çift hafta sonu OFF ihlali:", len(
    hafta_sonu_adalet_df[hafta_sonu_adalet_df["min_1_cift_off_ok"] == False]
))

print("3 günden fazla hafta sonu çalışan agent sayısı:", len(
    hafta_sonu_adalet_df[
        (hafta_sonu_adalet_df["hafta_sonu_calisamaz_agent"] == False) &
        (hafta_sonu_adalet_df["toplam_hafta_sonu_calisma_gunu"] > HAFTA_SONU_IDEAL_MAX_CALISMA)
    ]
))

print("İdeal aralıkta olmayan agent sayısı:", len(
    hafta_sonu_adalet_df[
        (hafta_sonu_adalet_df["hafta_sonu_calisamaz_agent"] == False) &
        (hafta_sonu_adalet_df["ideal_aralikta_mi"] == False)
    ]
))

print("\nHafta sonu çalışma günü dağılımı:")
display(
    hafta_sonu_adalet_df
    .groupby("toplam_hafta_sonu_calisma_gunu", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("toplam_hafta_sonu_calisma_gunu")
)

print("\nÇift hafta sonu OFF dağılımı:")
display(
    hafta_sonu_adalet_df
    .groupby("toplam_cmt_paz_cift_off", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("toplam_cmt_paz_cift_off")
)

print("\n3 günden fazla hafta sonu çalışan agentlar:")
display(
    hafta_sonu_adalet_df[
        (hafta_sonu_adalet_df["hafta_sonu_calisamaz_agent"] == False) &
        (hafta_sonu_adalet_df["toplam_hafta_sonu_calisma_gunu"] > HAFTA_SONU_IDEAL_MAX_CALISMA)
    ]
    .sort_values("toplam_hafta_sonu_calisma_gunu", ascending=False)
    .head(100)
)

print("\nHiç veya az hafta sonu çalışan agentlar:")
display(
    hafta_sonu_adalet_df[
        (hafta_sonu_adalet_df["hafta_sonu_calisamaz_agent"] == False) &
        (hafta_sonu_adalet_df["toplam_hafta_sonu_calisma_gunu"] < HAFTA_SONU_IDEAL_MIN_CALISMA)
    ]
    .sort_values("toplam_hafta_sonu_calisma_gunu")
    .head(100)
)
