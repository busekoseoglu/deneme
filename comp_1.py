# -------------------------------------------------
# ARİFE PARAMETRELERİ
# -------------------------------------------------

# Arife günü:
# - 13:00 öncesi başlayan vardiyalar normal sayılır.
# - 13:00 ve sonrası başlayan vardiyalar arife mesaisi sayılır.
# - Hamile / süt izni / mesai yapamaz agentlar 13:00 sonrasına sarkan vardiyalarda çalışamaz.
# - Bu agentlar arife günü 09:00-13:00 vardiyasına yazılır.
"ARIFE_GUNLERI": {
    "2026-06-16": {
        "mesai_baslangic": "13:00",
        "kisitli_agent_normal_vardiya": ("09:00", "13:00"),
    }
},

# Şimdilik 0 bırakıyoruz.
# Amaç arife mesaisini Excel'de etiketlemek; coverage'ı bozacak ceza vermemek.
"ARIFE_MESAI_W": 0,


ARIFE_GUNLERI = CONFIG["ARIFE_GUNLERI"]
ARIFE_MESAI_W = CONFIG["ARIFE_MESAI_W"]



# %% [HÜCRE] - ARİFE VARDİYA SINIFLANDIRMA YARDIMCILARI

def arife_dakika(s):
    """
    '09:00' veya '9:00' gibi saatleri dakikaya çevirir.
    """
    hh, mm = str(s).split(":")
    return int(hh) * 60 + int(mm)


def arife_vardiya_abs_aralik(ds, v):
    """
    Vardiyanın başlangıç/bitiş dakikasını döndürür.
    Geceye sarkan vardiyalarda bitişe +24 saat ekler.
    """
    bas, bit = saat[(ds, v)]

    bas_dk = arife_dakika(bas)
    bit_dk = arife_dakika(bit)

    # Örn: 17:00-01:00 gibi geceye sarkan vardiya
    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    return bas, bit, bas_dk, bit_dk


def arife_mesai_vardiyasi_mi_func(ds, v):
    """
    Arife günü hangi vardiyanın mesaili plan sayılacağını belirler.

    Kural:
    - 13:00 öncesinde başlayan vardiyalar normal sayılır.
      Örn: 09-13, 10-19, 12-21 normal.
    - 13:00 ve sonrası başlayan vardiyalar arife mesaisi sayılır.
      Örn: 13-22, 15-00 mesaili.
    """

    ds = str(ds)

    if ds not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)

    limit_dk = arife_dakika(ARIFE_GUNLERI[ds]["mesai_baslangic"])

    # 13:00 öncesi başlayan vardiyalar normal.
    if bas_dk < limit_dk:
        return False

    # 13:00 ve sonrası başlayan vardiyalar mesaili.
    return True


def arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v):
    """
    Hamile / süt izni / mesai yapamaz agentlar için yasak vardiyayı belirler.

    Bu kişiler arife günü 13:00 sonrasına sarkan hiçbir vardiyada çalışamaz.
    Bu nedenle 12-21 normal plan sayılsa bile bu kişiler için yasaktır.
    """

    ds = str(ds)

    if ds not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)

    limit_dk = arife_dakika(ARIFE_GUNLERI[ds]["mesai_baslangic"])

    # 13:00 sonrasına sarkıyorsa kısıtlı agent için yasak.
    # 09-13 gibi tam 13:00'te biten vardiya yasak değildir.
    return bit_dk > limit_dk


arife_mesai_vardiyasi_mi = {}
arife_kisitli_yasak_vardiya_mi = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        arife_mesai_vardiyasi_mi[(ds, v)] = arife_mesai_vardiyasi_mi_func(ds, v)
        arife_kisitli_yasak_vardiya_mi[(ds, v)] = arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v)


print("Arife günleri:", list(ARIFE_GUNLERI.keys()))
print("Arife mesaili vardiya sayısı:", sum(arife_mesai_vardiyasi_mi.values()))
print("Arife kısıtlı agent için yasak vardiya sayısı:", sum(arife_kisitli_yasak_vardiya_mi.values()))



# %% KONTROL - ARİFE VARDİYA SINIFLANDIRMASI

arife_vardiya_check_rows = []

for ds in PLAN_GUNLER:
    if str(ds) not in ARIFE_GUNLERI:
        continue

    for v in gun_vardiyalari.get(ds, []):
        bas, bit = saat[(ds, v)]

        arife_vardiya_check_rows.append({
            "date": ds,
            "shift": v,
            "start": bas,
            "end": bit,
            "arife_mesai_vardiyasi_mi": arife_mesai_vardiyasi_mi.get((ds, v), False),
            "kisitli_agent_icin_yasak_mi": arife_kisitli_yasak_vardiya_mi.get((ds, v), False),
            "required": int(talep[(ds, v)])
        })

arife_vardiya_check_df = pd.DataFrame(arife_vardiya_check_rows)

display(
    arife_vardiya_check_df
    .sort_values(["start", "end"])
)


# %% [HÜCRE] - ARİFE ÇALIŞMA KURALLARI

# Arifede 13 sonrası çalışamayacak agentlar:
# - hamile
# - süt izni
# - mesaiye kalamaz
arife_kisitli_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

# Arife mesaisi değişkenleri:
# Kısıtlı olmayan agentlar 13:00 ve sonrası başlayan vardiyalarda çalışırsa 1 olur.
arife_mesai = {}

arife_constraints = 0
arife_09_13_zorunlu_constraints = 0
arife_skip_rows = []

arife_plan_gunleri = [
    ds for ds in PLAN_GUNLER
    if str(ds) in ARIFE_GUNLERI
]

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        ds_key = str(ds)

        # -------------------------------------------------
        # 1) Kısıtlı agentlar 13:00 sonrasına sarkan vardiyada çalışamaz
        # -------------------------------------------------
        if a in arife_kisitli_agents:

            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    arife_constraints += 1

            # -------------------------------------------------
            # 2) Kısıtlı agentlar arife günü 09:00-13:00 çalışır
            # -------------------------------------------------
            # Agent izinliyse zorlamıyoruz.
            if ds in izin_map.get(a, set()):
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "izinli"
                })
                continue

            hedef_bas, hedef_bit = ARIFE_GUNLERI[ds_key]["kisitli_agent_normal_vardiya"]
            hedef_bas_dk = arife_dakika(hedef_bas)
            hedef_bit_dk = arife_dakika(hedef_bit)

            hedef_vardiya_vars = []

            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if (ds, v) not in saat:
                    continue

                bas, bit = saat[(ds, v)]
                bas_dk = arife_dakika(bas)
                bit_dk = arife_dakika(bit)

                if bas_dk == hedef_bas_dk and bit_dk == hedef_bit_dk:
                    hedef_vardiya_vars.append(x[(a, ds, v)])

            # 09-13 vardiyası varsa hard çalıştırıyoruz.
            # Yoksa infeasible olmasın diye zorlamıyoruz, skip raporuna yazıyoruz.
            if hedef_vardiya_vars:
                model.Add(sum(hedef_vardiya_vars) == 1)
                arife_09_13_zorunlu_constraints += 1
            else:
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "09-13_vardiyasi_yok"
                })

        # -------------------------------------------------
        # 3) Kısıtlı olmayan agentlar arife mesaili vardiyada çalışırsa işaretle
        # -------------------------------------------------
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                # Kısıtlı agentlarda zaten 13 sonrası yasak olduğu için
                # onlar adına arife_mesai değişkeni açmıyoruz.
                if a not in arife_kisitli_agents:

                    arife_mesai[(a, ds, v)] = model.NewBoolVar(
                        f"arife_mesai_{a}_{ds}_{v}"
                    )

                    model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                    arife_constraints += 1


print("Arife günleri:", arife_plan_gunleri)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife 13 sonrası yasak/mesai kısıt sayısı:", arife_constraints)
print("Arife 09-13 zorunlu çalışma kısıtı:", arife_09_13_zorunlu_constraints)
print("Arife mesai değişken sayısı:", len(arife_mesai))

if arife_skip_rows:
    arife_skip_df = pd.DataFrame(arife_skip_rows)
    print("Arife 09-13 zorunlu çalışma skip sayısı:", len(arife_skip_df))
    display(arife_skip_df.head(100))


# -------------------------------------------------
# ARİFE MESAİ CEZASI
# -------------------------------------------------
# ARIFE_MESAI_W şu an 0.
# Yani coverage bozulmasın diye arife mesaisine ceza vermiyoruz.
# Sadece Excel / kontrol tarafında arife mesaisi olarak etiketliyoruz.

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)



# %% KONTROL - ARİFE KURALLARI

arife_kontrol_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            assigned = solver.Value(x[(a, ds, v)])

            if assigned == 0:
                continue

            bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

            arife_kontrol_rows.append({
                "agent_user_code": a,
                "date": ds,
                "shift": v,
                "shift_start": bas,
                "shift_end": bit,
                "arife_mesai_vardiyasi_mi": arife_mesai_vardiyasi_mi.get((ds, v), False),
                "arife_kisitli_agent": a in arife_kisitli_agents,
                "arife_kisitli_icin_yasak_vardiya_mi": arife_kisitli_yasak_vardiya_mi.get((ds, v), False),
                "arife_mesai": (
                    solver.Value(arife_mesai[(a, ds, v)])
                    if "arife_mesai" in globals() and (a, ds, v) in arife_mesai
                    else 0
                )
            })

arife_kontrol_df = pd.DataFrame(arife_kontrol_rows)

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

arife_kontrol_df = arife_kontrol_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Arife çalışan özet:")
display(
    arife_kontrol_df
    .groupby(["date", "shift_start", "shift_end", "arife_mesai_vardiyasi_mi"], as_index=False)
    .agg(
        calisan_agent_sayisi=("agent_user_code", "nunique"),
        arife_mesai_sayisi=("arife_mesai", "sum")
    )
    .sort_values(["date", "shift_start", "shift_end"])
)

ihlal_df = arife_kontrol_df[
    (arife_kontrol_df["arife_kisitli_agent"] == True) &
    (arife_kontrol_df["arife_kisitli_icin_yasak_vardiya_mi"] == True)
]

print("Kısıtlı agent 13 sonrası ihlal sayısı:", len(ihlal_df))
display(ihlal_df)

print("Kısıtlı agentların arife vardiyaları:")
display(
    arife_kontrol_df[
        arife_kontrol_df["arife_kisitli_agent"] == True
    ]
    .sort_values(["takim", "agent_user_code"])
)
