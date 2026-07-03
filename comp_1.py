# -------------------------------------------------
# RESMİ TATİL / ARİFE PARAMETRELERİ
# -------------------------------------------------

# Tam gün resmi tatiller.
# Bu günlerde çalışan uygun agentlar resmi tatil mesaisi yapmış sayılır.
"RESMI_TATIL_TAM_GUNLER": [
    "2026-06-17"
],

# Yarım gün resmi tatiller.
# Bu günlerde belirlenen saatten sonrası resmi tatil mesaisi sayılır.
"RESMI_TATIL_YARIM_GUNLER": {
    "2026-06-16": "13:00"
},

# Resmi tatil mesai cezası.
# Coverage gerekiyorsa model çalıştırır ama gereksiz çalıştırmayı azaltır.
"RESMI_TATIL_MESAI_W": 30000,


RESMI_TATIL_TAM_GUNLER = set(CONFIG["RESMI_TATIL_TAM_GUNLER"])
RESMI_TATIL_YARIM_GUNLER = CONFIG["RESMI_TATIL_YARIM_GUNLER"]
RESMI_TATIL_MESAI_W = CONFIG["RESMI_TATIL_MESAI_W"]


# %% [HÜCRE] - RESMİ TATİL / ARİFE YARDIMCI HESAPLARI

def saat_to_dakika_resmi_tatil(s):
    hh, mm = str(s).split(":")
    return int(hh) * 60 + int(mm)


def vardiya_resmi_tatil_mesai_mi(ds, v):
    """
    Vardiyanın resmi tatil mesaisi sayılıp sayılmadığını döndürür.

    Tam resmi tatil:
    - O günkü tüm vardiyalar resmi tatil mesaisi.

    Yarım gün resmi tatil:
    - Kesim saatinden sonra başlayan veya kesim saatini aşan vardiyalar resmi tatil mesaisi.
    - Örn 16 Haziran için kesim 13:00 ise:
        07:00-13:00 -> mesai değil
        08:00-16:00 -> mesai
        13:00-21:00 -> mesai
        17:00-01:00 -> mesai
        00:00-08:00 -> mesai değil
    """

    ds = str(ds)

    if ds in RESMI_TATIL_TAM_GUNLER:
        return True

    if ds not in RESMI_TATIL_YARIM_GUNLER:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit = saat[(ds, v)]

    bas_dk = saat_to_dakika_resmi_tatil(bas)
    bit_dk = saat_to_dakika_resmi_tatil(bit)
    limit_dk = saat_to_dakika_resmi_tatil(RESMI_TATIL_YARIM_GUNLER[ds])

    # Geceye sarkan vardiya: 17:00-01:00 gibi
    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    # 00:00-08:00 gibi vardiyalar sabah bitiyorsa,
    # arife öğleden sonra mesaisi sayılmasın.
    # Çünkü bitiş 08:00 < 13:00.
    if bas_dk == 0 and bit_dk <= limit_dk:
        return False

    # Yarım gün resmi tatilde, vardiya limit saatini aşıyorsa mesai sayılır.
    return bit_dk > limit_dk


resmi_tatil_mesai_vardiyasi_mi = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        resmi_tatil_mesai_vardiyasi_mi[(ds, v)] = vardiya_resmi_tatil_mesai_mi(ds, v)


print("Tam gün resmi tatiller:", RESMI_TATIL_TAM_GUNLER)
print("Yarım gün resmi tatiller:", RESMI_TATIL_YARIM_GUNLER)

print("Resmi tatil mesaisi sayılan vardiya sayısı:",
      sum(1 for val in resmi_tatil_mesai_vardiyasi_mi.values() if val))
    
    
    
# %% [HÜCRE] - RESMİ TATİL / ARİFE ÇALIŞMA KURALLARI

# Resmi tatilde çalışamayacak agentlar:
# - hamile
# - süt izni
# - mesaiye kalamaz
resmi_tatil_calisamaz_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

# Hamile / süt izni olanlar:
# 16 Haziran öğleden önceki normal saatlerde çalıştırılmak isteniyor.
arife_oncesi_calisacak_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

resmi_tatil_mesai = {}
resmi_tatil_constraints = 0

resmi_tatil_plan_gunleri = set(RESMI_TATIL_TAM_GUNLER) | set(RESMI_TATIL_YARIM_GUNLER.keys())
resmi_tatil_plan_gunleri = [
    ds for ds in PLAN_GUNLER
    if ds in resmi_tatil_plan_gunleri
]

for a in AGENTS:
    a = str(a).strip()

    for ds in resmi_tatil_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            mesai_vardiyasi = resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False)

            # Tam gün resmi tatilde veya arife öğleden sonra mesai sayılan vardiyalarda:
            # hamile / süt izni / mesaiye kalamaz çalışamaz.
            if mesai_vardiyasi and a in resmi_tatil_calisamaz_agents:
                model.Add(x[(a, ds, v)] == 0)
                resmi_tatil_constraints += 1

            # Diğer uygun agentlar bu vardiyada çalışırsa resmi tatil mesaisi sayılır.
            elif mesai_vardiyasi and a not in resmi_tatil_calisamaz_agents:
                resmi_tatil_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"resmi_tatil_mesai_{a}_{ds}_{v}"
                )

                model.Add(resmi_tatil_mesai[(a, ds, v)] == x[(a, ds, v)])
                resmi_tatil_constraints += 1


print("Resmi tatil plan günleri:", resmi_tatil_plan_gunleri)
print("Resmi tatilde çalışamaz agent sayısı:", len(resmi_tatil_calisamaz_agents))
print("Arife öncesi çalışması istenen hamile/süt izni agent sayısı:", len(arife_oncesi_calisacak_agents))
print("Resmi tatil mesai değişken sayısı:", len(resmi_tatil_mesai))
print("Resmi tatil kısıtı:", resmi_tatil_constraints)


# %% [HÜCRE] - ARİFE ÖĞLEDEN ÖNCE HAMİLE / SÜT İZNİ ÇALIŞTIRMA

# 16 Haziran arife.
# Hamile / süt izni olanlar resmi tatil mesaisi başlamadan önceki vardiyalarda çalıştırılmak isteniyor.
# Burada sadece mesai sayılmayan vardiyaları uygun kabul ediyoruz.

arife_normal_calisma_constraints = 0
arife_normal_calisma_skip_rows = []

for ds, limit_saat in RESMI_TATIL_YARIM_GUNLER.items():

    if ds not in PLAN_GUNLER:
        continue

    for a in arife_oncesi_calisacak_agents:
        a = str(a).strip()

        # Eğer izinliyse zorlamayalım.
        if ds in izin_map.get(a, set()):
            arife_normal_calisma_skip_rows.append({
                "agent_user_code": a,
                "date": ds,
                "reason": "izinli"
            })
            continue

        uygun_mesai_olmayan_vardiyalar = [
            x[(a, ds, v)]
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
            and resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False) == False
        ]

        # Uygun sabah / öğleden önce vardiya varsa çalışmasını zorla.
        if uygun_mesai_olmayan_vardiyalar:
            model.Add(sum(uygun_mesai_olmayan_vardiyalar) == 1)
            arife_normal_calisma_constraints += 1

        else:
            # Uygun vardiya yoksa zorlamıyoruz, yoksa model infeasible olabilir.
            arife_normal_calisma_skip_rows.append({
                "agent_user_code": a,
                "date": ds,
                "reason": "uygun_mesai_olmayan_vardiya_yok"
            })

print("Arife öğleden önce hamile/süt izni çalıştırma kısıtı:", arife_normal_calisma_constraints)

if arife_normal_calisma_skip_rows:
    arife_normal_calisma_skip_df = pd.DataFrame(arife_normal_calisma_skip_rows)
    print("Arife normal çalışma zorlanamayan kayıt sayısı:", len(arife_normal_calisma_skip_df))
    display(arife_normal_calisma_skip_df.head(50))
    
    
    
# -------------------------------------------------
# RESMİ TATİL MESAİ CEZASI
# -------------------------------------------------

if "resmi_tatil_mesai" in globals():
    for (a, ds, v), var in resmi_tatil_mesai.items():
        objective_terms.append(
            RESMI_TATIL_MESAI_W * var
        )

print("RESMI_TATIL_MESAI_W:", RESMI_TATIL_MESAI_W)


# %% KONTROL - RESMİ TATİL / ARİFE

resmi_tatil_kontrol_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in resmi_tatil_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            assigned = solver.Value(x[(a, ds, v)])

            if assigned == 0:
                continue

            resmi_tatil_kontrol_rows.append({
                "agent_user_code": a,
                "date": ds,
                "shift": v,
                "work": assigned,
                "resmi_tatil_mesai_vardiyasi_mi": resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False),
                "resmi_tatilde_calisamaz_agent": a in resmi_tatil_calisamaz_agents,
                "arife_oncesi_calisacak_agent": a in arife_oncesi_calisacak_agents,
                "resmi_tatil_mesai": (
                    solver.Value(resmi_tatil_mesai[(a, ds, v)])
                    if "resmi_tatil_mesai" in globals() and (a, ds, v) in resmi_tatil_mesai
                    else 0
                )
            })

resmi_tatil_kontrol_df = pd.DataFrame(resmi_tatil_kontrol_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

resmi_tatil_kontrol_df = resmi_tatil_kontrol_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Resmi tatil / arife çalışan özet:")
display(
    resmi_tatil_kontrol_df
    .groupby(["date", "resmi_tatil_mesai_vardiyasi_mi"], as_index=False)
    .agg(
        calisan_agent_sayisi=("agent_user_code", "nunique"),
        resmi_tatil_mesai_sayisi=("resmi_tatil_mesai", "sum")
    )
)

print("Resmi tatil mesai saatinde çalışamaz olup çalışan ihlal sayısı:")
ihlal_df = resmi_tatil_kontrol_df[
    (resmi_tatil_kontrol_df["resmi_tatil_mesai_vardiyasi_mi"] == True) &
    (resmi_tatil_kontrol_df["resmi_tatilde_calisamaz_agent"] == True)
]

print(len(ihlal_df))
display(ihlal_df)

print("16 Haziran öğleden önce hamile/süt izni çalışanlar:")
display(
    resmi_tatil_kontrol_df[
        (resmi_tatil_kontrol_df["date"] == "2026-06-16") &
        (resmi_tatil_kontrol_df["arife_oncesi_calisacak_agent"] == True)
    ]
    .sort_values(["takim", "agent_user_code"])
)




