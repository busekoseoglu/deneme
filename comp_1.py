# %% [HÜCRE] - ARİFE ÖZEL 09:00-13:00 VARDİYASINI EKLE
# Bu hücre karar değişkenlerinden önce çalışmalı.
#
# Amaç:
# Hamile / süt izni / mesaiye kalamaz agentların arife günü 09:00-13:00 çalışabilmesi için
# modele özel bir vardiya opsiyonu eklemek.
#
# Eğer 09-13 vardiyası orijinal talep datasında yoksa model zaten o vardiyaya atama yapamaz.
# Bu yüzden özel vardiya ekliyoruz.

def arife_ds_key_pre(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


arife_ozel_vardiyalar = set()

for ds in PLAN_GUNLER:

    ds_key = arife_ds_key_pre(ds)

    if ds_key not in ARIFE_GUNLERI:
        continue

    arife_cfg = ARIFE_GUNLERI[ds_key]

    ozel_v = arife_cfg["ozel_vardiya_kodu"]
    hedef_bas, hedef_bit = arife_cfg["kisitli_agent_normal_vardiya"]

    # gun_vardiyalari içine ekle
    if ds not in gun_vardiyalari:
        gun_vardiyalari[ds] = []

    if ozel_v not in gun_vardiyalari[ds]:
        gun_vardiyalari[ds].append(ozel_v)

    # saat sözlüğüne ekle
    saat[(ds, ozel_v)] = (hedef_bas, hedef_bit)

    # talep sözlüğüne ekle
    # Talep 0 veriyoruz çünkü bu vardiya operasyonel demand karşılamak için değil,
    # kısıtlı agentların arife normal çalışması için özel bir vardiya.
    talep[(ds, ozel_v)] = 0

    arife_ozel_vardiyalar.add((ds, ozel_v))

print("Eklenen arife özel vardiyalar:", arife_ozel_vardiyalar)


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
    """
    Arife mesaisi:
    - 13:00 öncesi başlayan vardiyalar normal.
    - 13:00 ve sonrası başlayan vardiyalar arife mesaisi.
    - Özel ARIFE_09_13 vardiyası normal.
    """

    ds_key = arife_ds_key(ds)

    if ds_key not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    # Özel 09-13 vardiyası mesai değildir.
    if (ds, v) in arife_ozel_vardiyalar:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)
    limit_dk = arife_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    return bas_dk >= limit_dk


def arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v):
    """
    Kısıtlı agent için yasak:
    - 13:00 sonrasına sarkan vardiyalar yasak.
    - Özel 09-13 vardiyası yasak değil.
    """

    ds_key = arife_ds_key(ds)

    if ds_key not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    # Özel 09-13 vardiyası kısıtlı agent için uygundur.
    if (ds, v) in arife_ozel_vardiyalar:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)
    limit_dk = arife_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

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
print("Arife özel vardiyalar:", arife_ozel_vardiyalar)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife mesaili vardiya sayısı:", sum(arife_mesai_vardiyasi_mi.values()))
print("Arife kısıtlı agent için yasak vardiya sayısı:", sum(arife_kisitli_yasak_vardiya_mi.values()))


# %% KONTROL - ARİFE VARDİYA SINIFLANDIRMASI

arife_vardiya_check_rows = []

for ds in arife_plan_gunleri:
    for v in gun_vardiyalari.get(ds, []):

        bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

        arife_vardiya_check_rows.append({
            "date": ds,
            "shift": v,
            "start": bas,
            "end": bit,
            "is_arife_ozel_vardiya": (ds, v) in arife_ozel_vardiyalar,
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

arife_mesai = {}

arife_constraints = 0
arife_09_13_zorunlu_constraints = 0
arife_non_kisitli_ozel_vardiya_yasak_constraints = 0
arife_skip_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        ds_key = arife_ds_key(ds)
        ozel_v = ARIFE_GUNLERI[ds_key]["ozel_vardiya_kodu"]

        # -------------------------------------------------
        # 1) Kısıtlı agentlar arife günü 09-13 özel vardiyasına atanır
        # -------------------------------------------------
        if a in arife_kisitli_agents:

            # İzinliyse zorlamıyoruz.
            if ds in izin_map.get(a, set()):
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "izinli"
                })
            else:
                if (a, ds, ozel_v) in x:
                    model.Add(x[(a, ds, ozel_v)] == 1)
                    arife_09_13_zorunlu_constraints += 1
                else:
                    arife_skip_rows.append({
                        "agent_user_code": a,
                        "date": ds,
                        "reason": "ozel_09_13_x_yok"
                    })

            # Kısıtlı agentlar 13 sonrasına sarkan vardiyalarda çalışamaz
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    arife_constraints += 1

        # -------------------------------------------------
        # 2) Kısıtlı olmayan agentlar özel ARIFE_09_13 vardiyasına atanamaz
        # -------------------------------------------------
        else:
            if (a, ds, ozel_v) in x:
                model.Add(x[(a, ds, ozel_v)] == 0)
                arife_non_kisitli_ozel_vardiya_yasak_constraints += 1

        # -------------------------------------------------
        # 3) Arife mesaili vardiya etiketi
        # -------------------------------------------------
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                arife_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"arife_mesai_{a}_{ds}_{v}"
                )

                model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                arife_constraints += 1


print("Arife günleri:", arife_plan_gunleri)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife 09-13 zorunlu atama kısıtı:", arife_09_13_zorunlu_constraints)
print("Arife kısıtlı 13 sonrası yasak / mesai link kısıtı:", arife_constraints)
print("Arife non-kısıtlı özel vardiya yasak kısıtı:", arife_non_kisitli_ozel_vardiya_yasak_constraints)
print("Arife mesai değişken sayısı:", len(arife_mesai))

if arife_skip_rows:
    arife_skip_df = pd.DataFrame(arife_skip_rows)
    print("Arife skip sayısı:", len(arife_skip_df))
    display(arife_skip_df.head(100))


------

if arife_ds_key(ds) in ARIFE_GUNLERI:
    arife_team_base_skip_count += 1
    continue



# %% [HÜCRE] - FAZLA ATAMA ÜST LİMİTİ

fazla_atama_cap_constraints = 0
arife_cap_relax_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        required = int(talep[(ds, v)])

        assigned = sum(
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        )

        max_fazla = fazla_atama_ust_limit.get((ds, v), GENEL_MAX_FAZLA_ATAMA)

        # -------------------------------------------------
        # ARİFE ÖZEL 09-13 VARDİYASI
        # -------------------------------------------------
        if (ds, v) in arife_ozel_vardiyalar:

            forced_count = 0

            for a in arife_kisitli_agents:
                a = str(a).strip()

                if ds in izin_map.get(a, set()):
                    continue

                if (a, ds, v) in x:
                    forced_count += 1

            min_needed_extra = max(0, forced_count - required)

            if min_needed_extra > max_fazla:
                arife_cap_relax_rows.append({
                    "date": ds,
                    "shift": v,
                    "required": required,
                    "old_max_fazla": max_fazla,
                    "forced_count": forced_count,
                    "new_max_fazla": min_needed_extra
                })

                max_fazla = min_needed_extra

        model.Add(
            assigned <= required + max_fazla
        )

        fazla_atama_cap_constraints += 1


print("Fazla atama üst limit kısıtı:", fazla_atama_cap_constraints)
print("Genel max fazla atama:", GENEL_MAX_FAZLA_ATAMA)
print("Gece/akşam max fazla atama:", GECE_MAX_FAZLA_ATAMA)

if arife_cap_relax_rows:
    arife_cap_relax_df = pd.DataFrame(arife_cap_relax_rows)
    print("Arife özel 09-13 cap esnetilen satır sayısı:", len(arife_cap_relax_df))
    display(arife_cap_relax_df)




# -------------------------------------------------
# ARİFE MESAİ CEZASI
# -------------------------------------------------
# ARIFE_MESAI_W = 0 olduğu için coverage bozmaz.
# Sadece arife mesaisi Excel/kontrol tarafında etiketlenir.

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)




# %% KONTROL - ARİFE KISITLI AGENTLARIN TAM DAĞILIMI

arife_kisitli_full_rows = []

for a in AGENTS:
    a = str(a).strip()

    if a not in arife_kisitli_agents:
        continue

    for ds in arife_plan_gunleri:

        assigned_shift = None
        assigned_start = None
        assigned_end = None
        assigned_is_yasak = False
        assigned_is_arife_mesai = False
        is_arife_ozel_vardiya = False

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if solver.Value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                assigned_start, assigned_end = saat[(ds, v)]
                assigned_is_yasak = arife_kisitli_yasak_vardiya_mi.get((ds, v), False)
                assigned_is_arife_mesai = arife_mesai_vardiyasi_mi.get((ds, v), False)
                is_arife_ozel_vardiya = (ds, v) in arife_ozel_vardiyalar
                break

        is_leave = ds in izin_map.get(a, set())
        is_work = solver.Value(work[(a, ds)]) if (a, ds) in work else 0

        arife_kisitli_full_rows.append({
            "agent_user_code": a,
            "date": ds,
            "is_leave": is_leave,
            "work": is_work,

            "assigned_shift": assigned_shift,
            "shift_start": assigned_start,
            "shift_end": assigned_end,

            "is_arife_ozel_09_13": is_arife_ozel_vardiya,
            "13_sonrasina_sarkiyor_mu": assigned_is_yasak,
            "arife_mesai_vardiyasi_mi": assigned_is_arife_mesai,
        })

arife_kisitli_full_df = pd.DataFrame(arife_kisitli_full_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg",
    "sabah_calisir_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

arife_kisitli_full_df = arife_kisitli_full_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Toplam kısıtlı agent:", len(arife_kisitli_full_df))
print("Arife özel 09-13 atanan:", len(arife_kisitli_full_df[arife_kisitli_full_df["is_arife_ozel_09_13"] == True]))
print("13 sonrasına sarkan vardiyaya atanan:", len(arife_kisitli_full_df[arife_kisitli_full_df["13_sonrasina_sarkiyor_mu"] == True]))
print("İzinli:", len(arife_kisitli_full_df[arife_kisitli_full_df["is_leave"] == True]))

display(
    arife_kisitli_full_df
    .sort_values(["13_sonrasina_sarkiyor_mu", "is_arife_ozel_09_13", "takim", "agent_user_code"], ascending=[False, False, True, True])
)
