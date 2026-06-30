# -------------------------------------------------
# HAFTA SONU OFF ADİL DAĞITIM PARAMETRELERİ
# -------------------------------------------------

# Her agent en az 1 Cumartesi-Pazar peş peşe OFF almak zorunda.
# 1. çift OFF zorunlu olduğu için cezalanmaz.
# 2., 3., 4. çift OFF için artan ceza uygulanır.
#
# Amaç:
# Aynı agentın ay içindeki tüm hafta sonlarını OFF almasını engellemek,
# hafta sonu çalışma yükünü daha adil dağıtmak.
#
# Liste sırası:
# 2. çift OFF cezası
# 3. çift OFF cezası
# 4. çift OFF cezası
# 5. çift OFF cezası, ayda 5 hafta sonu varsa
"EKSTRA_HAFTA_SONU_CIFT_OFF_W": [5000, 20000, 50000, 100000],


EKSTRA_HAFTA_SONU_CIFT_OFF_W = CONFIG["EKSTRA_HAFTA_SONU_CIFT_OFF_W"]


# -------------------------------------------------
# HAFTA SONU ÇİFT OFF ADİL DAĞITIMI - SOFT DEĞİŞKENLER
# -------------------------------------------------
# Mevcut hard kural:
# Her agent ayda en az 1 Cumartesi-Pazar peş peşe OFF almak zorunda.
#
# Yeni soft mantık:
# 1 çift OFF ücretsiz / zorunlu.
# 2. çift OFF, 3. çift OFF, 4. çift OFF için artan ceza verilecek.
#
# Böylece model aynı agenta çok fazla hafta sonu OFF vermekten kaçınacak.
# Ama gerekirse yine verebilir; sadece objective'te ceza alır.

# Hafta sonu çalışması zaten yasak olan agentları bu fairness cezasından çıkarıyoruz.
# Çünkü hamile / süt izni olanlar hafta sonu çalışamaz, dolayısıyla fazla çift OFF almaları kaçınılmazdır.
hafta_sonu_calisamaz_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

# ekstra_cift_off[(agent, k)]:
# k = 2 ise agentın 2. Cumartesi-Pazar çift OFF'u var mı?
# k = 3 ise agentın 3. Cumartesi-Pazar çift OFF'u var mı?
# k = 4 ise agentın 4. Cumartesi-Pazar çift OFF'u var mı?
ekstra_cift_off = {}

ekstra_cift_off_constraints = 0

max_cift_sayisi = len(weekend_pairs)

for a in AGENTS:
    a = str(a).strip()

    # Hafta sonu çalışamayan kişiler için fairness cezası oluşturmuyoruz.
    if a in hafta_sonu_calisamaz_agents:
        continue

    toplam_cift_off = sum(
        pair_off[(a, i)]
        for i in range(max_cift_sayisi)
        if (a, i) in pair_off
    )

    ekstra_vars = []

    # 2. çift OFF'tan itibaren ekstra ceza değişkenleri
    for k in range(2, max_cift_sayisi + 1):
        ekstra_cift_off[(a, k)] = model.NewBoolVar(
            f"ekstra_cift_off_{a}_{k}"
        )
        ekstra_vars.append(ekstra_cift_off[(a, k)])

    # Eğer toplam çift OFF sayısı 1'den büyükse,
    # ekstra_cift_off değişkenleri açılmak zorunda kalır.
    #
    # Örnek:
    # toplam_cift_off = 1 ise ekstra değişken gerekmez.
    # toplam_cift_off = 2 ise 1 ekstra değişken açılır.
    # toplam_cift_off = 3 ise 2 ekstra değişken açılır.
    model.Add(
        toplam_cift_off <= 1 + sum(ekstra_vars)
    )

    ekstra_cift_off_constraints += 1

print("Hafta sonu çalışamaz agent sayısı:", len(hafta_sonu_calisamaz_agents))
print("Ekstra çift hafta sonu OFF değişken sayısı:", len(ekstra_cift_off))
print("Ekstra çift hafta sonu OFF fairness kısıtı:", ekstra_cift_off_constraints)



# -------------------------------------------------
# HAFTA SONU ÇİFT OFF ADİL DAĞITIM CEZASI
# -------------------------------------------------
# 1 çift Cumartesi-Pazar OFF zaten zorunlu ve ücretsiz.
# 2., 3., 4. çift OFF için artan ceza veriyoruz.
#
# Amaç:
# Aynı agentın ay içindeki tüm hafta sonlarını OFF almasını engellemek.
# Hafta sonu çalışma yükünü daha adil dağıtmak.

for (a, k), var in ekstra_cift_off.items():
    # k = 2 için listenin 0. elemanı
    # k = 3 için listenin 1. elemanı
    # k = 4 için listenin 2. elemanı
    weight_idx = k - 2

    if weight_idx < len(EKSTRA_HAFTA_SONU_CIFT_OFF_W):
        ceza = EKSTRA_HAFTA_SONU_CIFT_OFF_W[weight_idx]
    else:
        # Ayda beklenenden fazla hafta sonu çifti varsa son ceza değerini kullan
        ceza = EKSTRA_HAFTA_SONU_CIFT_OFF_W[-1]

    objective_terms.append(
        ceza * var
    )

print("EKSTRA_HAFTA_SONU_CIFT_OFF_W:", EKSTRA_HAFTA_SONU_CIFT_OFF_W)

# %% KONTROL - HAFTA SONU OFF / HAFTA SONU ÇALIŞMA ADİL DAĞITIMI

hafta_sonu_adalet_rows = []

for a in AGENTS:
    a = str(a).strip()

    cift_off_sayisi = 0
    hafta_sonu_calisma_gunu = 0
    cumartesi_calisma = 0
    pazar_calisma = 0

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs):
        sat_work = solver.Value(work[(a, sat_ds)])
        sun_work = solver.Value(work[(a, sun_ds)])

        if sat_work == 0 and sun_work == 0:
            cift_off_sayisi += 1

        hafta_sonu_calisma_gunu += sat_work + sun_work
        cumartesi_calisma += sat_work
        pazar_calisma += sun_work

    hafta_sonu_adalet_rows.append({
        "agent_user_code": a,
        "toplam_cmt_paz_cift_off": cift_off_sayisi,
        "toplam_hafta_sonu_calisma_gunu": hafta_sonu_calisma_gunu,
        "cumartesi_calisma_gunu": cumartesi_calisma,
        "pazar_calisma_gunu": pazar_calisma,
        "min_1_cift_off_ok": cift_off_sayisi >= 1,
        "hafta_sonu_calisamaz_agent": a in hafta_sonu_calisamaz_agents
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

print("\nÇift hafta sonu OFF dağılımı:")
display(
    hafta_sonu_adalet_df
    .groupby("toplam_cmt_paz_cift_off", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("toplam_cmt_paz_cift_off")
)

print("\nHafta sonu çalışma günü dağılımı:")
display(
    hafta_sonu_adalet_df
    .groupby("toplam_hafta_sonu_calisma_gunu", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("toplam_hafta_sonu_calisma_gunu")
)

print("\nEn çok çift hafta sonu OFF alan agentlar:")
display(
    hafta_sonu_adalet_df
    .sort_values(
        ["toplam_cmt_paz_cift_off", "toplam_hafta_sonu_calisma_gunu"],
        ascending=[False, True]
    )
    .head(100)
)

print("\nEn çok hafta sonu çalışan agentlar:")
display(
    hafta_sonu_adalet_df
    .sort_values(
        ["toplam_hafta_sonu_calisma_gunu", "toplam_cmt_paz_cift_off"],
        ascending=[False, True]
    )
    .head(100)
)
