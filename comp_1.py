# Arife günü hamile / süt izni / mesai yapamaz agentların
# 09:00-13:00 vardiyasına yazılamaması durumunda alınacak ceza.
# Yüksek tutuyoruz ama hard yapmıyoruz.
"ARIFE_09_13_ATANAMADI_W": 100000,


ARIFE_09_13_ATANAMADI_W = CONFIG["ARIFE_09_13_ATANAMADI_W"]


# %% [HÜCRE] - ARİFE ÇALIŞMA KURALLARI

arife_mesai = {}

# 09-13'e atanamama soft değişkeni
arife_09_13_atanamadi = {}

arife_constraints = 0
arife_09_13_soft_constraints = 0
arife_skip_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        ds_key = arife_ds_key(ds)

        # -------------------------------------------------
        # 1) Kısıtlı agentlar 13:00 sonrasına sarkan vardiyada çalışamaz
        # -------------------------------------------------
        # Bu hard kalıyor.
        # Hamile / süt izni / mesaiye kalamaz agentlar 13 sonrası çalışamaz.
        if a in arife_kisitli_agents:

            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    arife_constraints += 1

            # -------------------------------------------------
            # 2) Kısıtlı agentlar mümkünse 09:00-13:00 çalışsın
            # -------------------------------------------------
            # Bu artık hard değil, soft.
            # Çünkü hard olunca 11 saat / haftalık çalışma / diğer kısıtlarla çakışıp infeasible yapıyor.

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

                # Eğer 09-13'e atanmazsa arife_09_13_atanamadi = 1 olabilir.
                # Objective'te yüksek ceza alacak.
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
        # 3) Kısıtlı olmayan agentlar arife mesaili vardiyada çalışırsa işaretle
        # -------------------------------------------------
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                if a not in arife_kisitli_agents:

                    arife_mesai[(a, ds, v)] = model.NewBoolVar(
                        f"arife_mesai_{a}_{ds}_{v}"
                    )

                    model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                    arife_constraints += 1


print("Arife günleri:", arife_plan_gunleri)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife 13 sonrası yasak/mesai kısıt sayısı:", arife_constraints)
print("Arife 09-13 soft öncelik kısıtı:", arife_09_13_soft_constraints)
print("Arife 09-13 atanamadı değişken sayısı:", len(arife_09_13_atanamadi))
print("Arife mesai değişken sayısı:", len(arife_mesai))

if arife_skip_rows:
    arife_skip_df = pd.DataFrame(arife_skip_rows)
    print("Arife 09-13 soft öncelik skip sayısı:", len(arife_skip_df))
    display(arife_skip_df.head(100))



# -------------------------------------------------
# ARİFE MESAİ CEZASI
# -------------------------------------------------
# ARIFE_MESAI_W şu an 0.
# Arife mesaisi sadece etiketlenir, coverage bozulmasın diye cezalandırılmaz.

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)


# -------------------------------------------------
# ARİFE 09-13 ATANAMADI CEZASI
# -------------------------------------------------
# Hamile / süt izni / mesaiye kalamaz agentlar mümkünse 09-13 çalışsın.
# Hard değil; atanamazsa yüksek ceza alır.
# Böylece model infeasible olmaz.

if "arife_09_13_atanamadi" in globals():
    for (a, ds), var in arife_09_13_atanamadi.items():
        objective_terms.append(
            ARIFE_09_13_ATANAMADI_W * var
        )

print("ARIFE_09_13_ATANAMADI_W:", ARIFE_09_13_ATANAMADI_W)



# %% KONTROL - ARİFE 09-13 ATANAMAYANLAR

arife_09_13_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        if a not in arife_kisitli_agents:
            continue

        ds_key = arife_ds_key(ds)

        hedef_bas, hedef_bit = ARIFE_GUNLERI[ds_key]["kisitli_agent_normal_vardiya"]

        assigned_shift = None
        assigned_start = None
        assigned_end = None

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                assigned_start, assigned_end = saat[(ds, v)]
                break

        is_leave = ds in izin_map.get(a, set())
        is_work = solver.Value(work[(a, ds)]) if (a, ds) in work else 0

        hedef_09_13 = (
            assigned_start == hedef_bas and
            assigned_end == hedef_bit
        )

        arife_09_13_rows.append({
            "agent_user_code": a,
            "date": ds,
            "is_leave": is_leave,
            "work": is_work,
            "assigned_shift": assigned_shift,
            "shift_start": assigned_start,
            "shift_end": assigned_end,
            "hedef_09_13_atandi": hedef_09_13,
            "arife_09_13_atanamadi": (
                solver.Value(arife_09_13_atanamadi[(a, ds)])
                if "arife_09_13_atanamadi" in globals() and (a, ds) in arife_09_13_atanamadi
                else None
            )
        })

arife_09_13_df = pd.DataFrame(arife_09_13_rows)

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

arife_09_13_df = arife_09_13_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Kısıtlı agent sayısı:", len(arife_09_13_df))
print("09-13 atanan kısıtlı agent sayısı:", len(arife_09_13_df[arife_09_13_df["hedef_09_13_atandi"] == True]))
print("09-13 atanamayan kısıtlı agent sayısı:", len(arife_09_13_df[
    (arife_09_13_df["is_leave"] == False) &
    (arife_09_13_df["hedef_09_13_atandi"] == False)
]))

display(
    arife_09_13_df
    .sort_values(["hedef_09_13_atandi", "takim", "agent_user_code"])
)
