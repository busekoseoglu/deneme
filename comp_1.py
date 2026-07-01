# -------------------------------------------------
# HAFTA SONU ÇALIŞMA ADİL DAĞITIM PARAMETRELERİ
# -------------------------------------------------

# Bir agent için ay içinde cezasız kabul edilen maksimum hafta sonu çalışma günü.
# 4 güne kadar sorun yok, 5 ve üzeri cezalı.
"HAFTA_SONU_CEZA_BASLANGIC_GUN": 4,

# 4 günden fazla hafta sonu çalışmaya verilen ceza.
# Örn:
# 5 gün çalışırsa 1 birim ceza
# 6 gün çalışırsa 2 birim ceza
"HAFTA_SONU_FAZLA_CALISMA_W": 30000,

HAFTA_SONU_CEZA_BASLANGIC_GUN = CONFIG["HAFTA_SONU_CEZA_BASLANGIC_GUN"]
HAFTA_SONU_FAZLA_CALISMA_W = CONFIG["HAFTA_SONU_FAZLA_CALISMA_W"]


# %% [HÜCRE] - HAFTA SONU ÇALIŞMA ADİL DAĞITIMI
# Amaç:
# Her agentın hafta sonu çalışma yükü aşırı yükselmesin.
#
# Mevcut hard kural devam ediyor:
# Her agent ayda en az 1 Cumartesi-Pazar peş peşe OFF almak zorunda.
#
# Yeni soft mantık:
# - 0-4 hafta sonu çalışma günü cezasız.
# - 5 ve üzeri hafta sonu çalışma günü cezalı.
#
# Böylece model coverage'ı bozmadan, sadece aşırı hafta sonu çalışanları azaltmaya çalışır.
#
# Hamile / süt izni olan agentlar hafta sonu çalışamadığı için
# bu fairness cezasından hariç tutulur.

hafta_sonu_gunleri = sorted(
    set(
        [sat_ds for sat_ds, sun_ds in weekend_pairs] +
        [sun_ds for sat_ds, sun_ds in weekend_pairs]
    )
)

hafta_sonu_calisamaz_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

hafta_sonu_calisma_sayisi = {}
fazla_hafta_sonu_calisma = {}

hafta_sonu_adalet_constraints = 0

max_hafta_sonu_gun_sayisi = len(hafta_sonu_gunleri)

for a in AGENTS:
    a = str(a).strip()

    if a in hafta_sonu_calisamaz_agents:
        continue

    # Agentın ay içindeki toplam hafta sonu çalışma günü
    hafta_sonu_calisma_sayisi[a] = model.NewIntVar(
        0,
        max_hafta_sonu_gun_sayisi,
        f"hafta_sonu_calisma_sayisi_{a}"
    )

    # 4 günden fazla hafta sonu çalışırsa burada sapma oluşur.
    # Örn:
    # 4 gün çalışırsa 0
    # 5 gün çalışırsa 1
    # 6 gün çalışırsa 2
    fazla_hafta_sonu_calisma[a] = model.NewIntVar(
        0,
        max_hafta_sonu_gun_sayisi,
        f"fazla_hafta_sonu_calisma_{a}"
    )

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

    model.Add(
        fazla_hafta_sonu_calisma[a]
        >=
        hafta_sonu_calisma_sayisi[a] - HAFTA_SONU_CEZA_BASLANGIC_GUN
    )
    hafta_sonu_adalet_constraints += 1

print("Hafta sonu gün sayısı:", len(hafta_sonu_gunleri))
print("Hafta sonu çalışamaz agent sayısı:", len(hafta_sonu_calisamaz_agents))
print("Hafta sonu adalet değişkeni olan agent sayısı:", len(hafta_sonu_calisma_sayisi))
print("Hafta sonu adalet kısıtı:", hafta_sonu_adalet_constraints)
print("Hafta sonu ceza başlangıç günü:", HAFTA_SONU_CEZA_BASLANGIC_GUN)


# -------------------------------------------------
# HAFTA SONU ÇALIŞMA ADİL DAĞITIM CEZASI
# -------------------------------------------------
# 0-4 hafta sonu çalışma günü cezasız.
# 5 ve üzeri hafta sonu çalışma günü cezalı.
#
# Amaç:
# Coverage'ı bozmadan, aynı agentın çok fazla hafta sonu çalışmasını azaltmak.

for a in hafta_sonu_calisma_sayisi.keys():
    objective_terms.append(
        HAFTA_SONU_FAZLA_CALISMA_W * fazla_hafta_sonu_calisma[a]
    )

print("HAFTA_SONU_CEZA_BASLANGIC_GUN:", HAFTA_SONU_CEZA_BASLANGIC_GUN)
print("HAFTA_SONU_FAZLA_CALISMA_W:", HAFTA_SONU_FAZLA_CALISMA_W)
