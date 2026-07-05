"ARIFE_GUNLERI": {
    "2026-06-16": {
        "mesai_baslangic": "13:00",
        "kisitli_agent_normal_vardiya": ("09:00", "13:00"),
    }
},

"ARIFE_MESAI_W": 0,
"ARIFE_09_13_ATANAMADI_W": 100000,
"ARIFE_13_SONRASI_IHLAL_W": 1000000,

ARIFE_GUNLERI = CONFIG["ARIFE_GUNLERI"]
ARIFE_MESAI_W = CONFIG["ARIFE_MESAI_W"]
ARIFE_09_13_ATANAMADI_W = CONFIG["ARIFE_09_13_ATANAMADI_W"]
ARIFE_13_SONRASI_IHLAL_W = CONFIG["ARIFE_13_SONRASI_IHLAL_W"]


# %% [HÜCRE] - ARİFE HELPER

def arife_ds_key(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


def arife_dakika(s):
    hh, mm = str(s).split(":")
    return int(hh) * 60 + int(mm)


def arife_vardiya_abs_aralik(ds, v):
    bas, bit = saat[(ds, v)]

    bas_dk = arife_dakika(bas)
    bit_dk = arife_dakika(bit)

    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    return bas, bit, bas_dk, bit_dk


def arife_mesai_vardiyasi_mi_func(ds, v):
    ds_key = arife_ds_key(ds)

    if ds_key not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)
    limit_dk = arife_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    # 13:00 ve sonrası başlayan vardiyalar arife mesaisi.
    return bas_dk >= limit_dk


def arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v):
    ds_key = arife_ds_key(ds)

    if ds_key not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)
    limit_dk = arife_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    # 13 sonrasına sarkıyorsa kısıtlı agent için normalde yasak.
    return bit_dk > limit_dk


arife_mesai_vardiyasi_mi = {}
arife_kisitli_yasak_vardiya_mi = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        arife_mesai_vardiyasi_mi[(ds, v)] = arife_mesai_vardiyasi_mi_func(ds, v)
        arife_kisitli_yasak_vardiya_mi[(ds, v)] = arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v)


arife_plan_gunleri = [
    ds for ds in PLAN_GUNLER
    if arife_ds_key(ds) in ARIFE_GUNLERI
]

arife_kisitli_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

print("Arife günleri:", arife_plan_gunleri)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife mesaili vardiya sayısı:", sum(arife_mesai_vardiyasi_mi.values()))
print("Arife kısıtlı agent için yasak vardiya sayısı:", sum(arife_kisitli_yasak_vardiya_mi.values()))



# %% [HÜCRE] - ARİFE SOFT DEBUG KURALLARI

arife_mesai = {}
arife_09_13_atanamadi = {}
arife_13_sonrasi_ihlal = {}

arife_mesai_link_constraints = 0
arife_09_13_soft_constraints = 0
arife_13_sonrasi_soft_constraints = 0
arife_skip_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        ds_key = arife_ds_key(ds)

        if a in arife_kisitli_agents:

            # -------------------------------------------------
            # 1) 13 sonrası yasak normalde hard olacaktı.
            # Şimdilik soft ihlal olarak takip ediyoruz.
            # -------------------------------------------------
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):

                    arife_13_sonrasi_ihlal[(a, ds, v)] = model.NewBoolVar(
                        f"arife_13_sonrasi_ihlal_{a}_{ds}_{v}"
                    )

                    model.Add(
                        arife_13_sonrasi_ihlal[(a, ds, v)] >= x[(a, ds, v)]
                    )

                    arife_13_sonrasi_soft_constraints += 1

            # -------------------------------------------------
            # 2) Kısıtlı agent mümkünse 09-13'e yazılsın.
            # Bu da soft.
            # -------------------------------------------------
            if ds in izin_map.get(a, set()):
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "izinli"
                })
                continue

            hedef_bas, hedef_bit = ARIFE_GUNLERI[ds_key]["kisitli_agent_normal_vardiya"]

            hedef_vardiya_vars = []

            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if (ds, v) not in saat:
                    continue

                bas, bit = saat[(ds, v)]

                if bas == hedef_bas and bit == hedef_bit:
                    hedef_vardiya_vars.append(x[(a, ds, v)])

            if hedef_vardiya_vars:

                arife_09_13_atanamadi[(a, ds)] = model.NewBoolVar(
                    f"arife_09_13_atanamadi_{a}_{ds}"
                )

                model.Add(
                    sum(hedef_vardiya_vars) + arife_09_13_atanamadi[(a, ds)] >= 1
                )

                arife_09_13_soft_constraints += 1

            else:
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "09-13_vardiyasi_yok"
                })

        # -------------------------------------------------
        # 3) Arife mesaisi etiketi
        # -------------------------------------------------
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                arife_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"arife_mesai_{a}_{ds}_{v}"
                )

                model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                arife_mesai_link_constraints += 1


print("Arife mesai değişken sayısı:", len(arife_mesai))
print("Arife mesai link kısıtı:", arife_mesai_link_constraints)
print("Arife 09-13 atanamadı değişken sayısı:", len(arife_09_13_atanamadi))
print("Arife 09-13 soft kısıtı:", arife_09_13_soft_constraints)
print("Arife 13 sonrası ihlal değişken sayısı:", len(arife_13_sonrasi_ihlal))
print("Arife 13 sonrası soft kısıtı:", arife_13_sonrasi_soft_constraints)

if arife_skip_rows:
    arife_skip_df = pd.DataFrame(arife_skip_rows)
    print("Arife skip sayısı:", len(arife_skip_df))
    display(arife_skip_df.head(100))



# -------------------------------------------------
# ARİFE MESAİ CEZASI
# -------------------------------------------------

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)


# -------------------------------------------------
# ARİFE 09-13 ATANAMADI CEZASI
# -------------------------------------------------

if "arife_09_13_atanamadi" in globals():
    for (a, ds), var in arife_09_13_atanamadi.items():
        objective_terms.append(
            ARIFE_09_13_ATANAMADI_W * var
        )

print("ARIFE_09_13_ATANAMADI_W:", ARIFE_09_13_ATANAMADI_W)


# -------------------------------------------------
# ARİFE 13 SONRASI İHLAL CEZASI
# -------------------------------------------------

if "arife_13_sonrasi_ihlal" in globals():
    for (a, ds, v), var in arife_13_sonrasi_ihlal.items():
        objective_terms.append(
            ARIFE_13_SONRASI_IHLAL_W * var
        )

print("ARIFE_13_SONRASI_IHLAL_W:", ARIFE_13_SONRASI_IHLAL_W)


print("Arife 13 sonrası ihlal toplam:", sum(
    solver.Value(var)
    for var in arife_13_sonrasi_ihlal.values()
))

print("Arife 09-13 atanamadı toplam:", sum(
    solver.Value(var)
    for var in arife_09_13_atanamadi.values()
))
