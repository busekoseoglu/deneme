"RESMI_TATIL_KISITLI_IHLAL_W": 1000000,


RESMI_TATIL_KISITLI_IHLAL_W = CONFIG["RESMI_TATIL_KISITLI_IHLAL_W"]



# %% [HÜCRE] - ARİFE / RESMİ TATİL ÇALIŞMA KURALLARI - RESMİ TATİL SOFT DEBUG

arife_mesai = {}
resmi_tatil_mesai = {}
resmi_tatil_kisitli_ihlal = {}

tatil_constraints = 0
arife_09_13_zorunlu_constraints = 0
arife_non_kisitli_ozel_vardiya_yasak_constraints = 0
resmi_tatil_kisitli_soft_constraints = 0
tatil_skip_rows = []


for a in AGENTS:
    a = str(a).strip()

    # -------------------------------------------------
    # 1) ARİFE KURALLARI
    # -------------------------------------------------
    for ds in arife_plan_gunleri:

        ds_key = tatil_ds_key(ds)
        ozel_v = ARIFE_GUNLERI[ds_key]["ozel_vardiya_kodu"]

        if a in tatil_kisitli_agents:

            # Kısıtlı agent izinliyse arife 09-13'e zorlamıyoruz.
            if ds in izin_map.get(a, set()):
                tatil_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "rule": "arife_09_13",
                    "reason": "izinli"
                })
            else:
                # Kısıtlı agent arife özel 09-13 vardiyasına atanır.
                if (a, ds, ozel_v) in x:
                    model.Add(x[(a, ds, ozel_v)] == 1)
                    arife_09_13_zorunlu_constraints += 1
                else:
                    tatil_skip_rows.append({
                        "agent_user_code": a,
                        "date": ds,
                        "rule": "arife_09_13",
                        "reason": "ozel_09_13_x_yok"
                    })

            # Kısıtlı agentlar arife günü 13 sonrasına sarkan vardiyalarda çalışamaz.
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    tatil_constraints += 1

        else:
            # Kısıtlı olmayan agentlar özel ARIFE_09_13 vardiyasına atanamaz.
            if (a, ds, ozel_v) in x:
                model.Add(x[(a, ds, ozel_v)] == 0)
                arife_non_kisitli_ozel_vardiya_yasak_constraints += 1

        # Arife mesai etiketi
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                arife_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"arife_mesai_{a}_{ds}_{v}"
                )

                model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                tatil_constraints += 1


    # -------------------------------------------------
    # 2) RESMİ TATİL KURALLARI - SOFT DEBUG
    # -------------------------------------------------
    for ds in resmi_tatil_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            # Kısıtlı agentlar resmi tatilde normalde çalışamaz.
            # Ama şimdilik hard yasak yerine soft ihlal koyuyoruz.
            if a in tatil_kisitli_agents:

                resmi_tatil_kisitli_ihlal[(a, ds, v)] = model.NewBoolVar(
                    f"resmi_tatil_kisitli_ihlal_{a}_{ds}_{v}"
                )

                model.Add(
                    resmi_tatil_kisitli_ihlal[(a, ds, v)] >= x[(a, ds, v)]
                )

                resmi_tatil_kisitli_soft_constraints += 1

            # Resmi tatilde çalışan herkes resmi tatil mesaisi olarak etiketlenir.
            if resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False):

                resmi_tatil_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"resmi_tatil_mesai_{a}_{ds}_{v}"
                )

                model.Add(resmi_tatil_mesai[(a, ds, v)] == x[(a, ds, v)])
                tatil_constraints += 1


print("Arife 09-13 zorunlu atama kısıtı:", arife_09_13_zorunlu_constraints)
print("Arife non-kısıtlı özel vardiya yasak kısıtı:", arife_non_kisitli_ozel_vardiya_yasak_constraints)
print("Arife mesai değişken sayısı:", len(arife_mesai))

print("Resmi tatil kısıtlı soft ihlal kısıtı:", resmi_tatil_kisitli_soft_constraints)
print("Resmi tatil kısıtlı ihlal değişken sayısı:", len(resmi_tatil_kisitli_ihlal))
print("Resmi tatil mesai değişken sayısı:", len(resmi_tatil_mesai))

print("Toplam tatil kısıtı:", tatil_constraints)

if tatil_skip_rows:
    tatil_skip_df = pd.DataFrame(tatil_skip_rows)
    print("Tatil skip sayısı:", len(tatil_skip_df))
    display(tatil_skip_df.head(100))



# -------------------------------------------------
# ARİFE / RESMİ TATİL MESAİ VE İHLAL CEZALARI
# -------------------------------------------------

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

if "resmi_tatil_mesai" in globals() and RESMI_TATIL_MESAI_W > 0:
    for (a, ds, v), var in resmi_tatil_mesai.items():
        objective_terms.append(
            RESMI_TATIL_MESAI_W * var
        )

if "resmi_tatil_kisitli_ihlal" in globals():
    for (a, ds, v), var in resmi_tatil_kisitli_ihlal.items():
        objective_terms.append(
            RESMI_TATIL_KISITLI_IHLAL_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)
print("RESMI_TATIL_MESAI_W:", RESMI_TATIL_MESAI_W)
print("RESMI_TATIL_KISITLI_IHLAL_W:", RESMI_TATIL_KISITLI_IHLAL_W)



# %% KONTROL - RESMİ TATİL KISITLI İHLAL DETAYI

resmi_tatil_ihlal_rows = []

if "resmi_tatil_kisitli_ihlal" in globals():

    for (a, ds, v), ihlal_var in resmi_tatil_kisitli_ihlal.items():

        if solver.Value(ihlal_var) != 1:
            continue

        bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

        wk = day_week[ds] if ds in day_week else None

        resmi_tatil_ihlal_rows.append({
            "agent_user_code": a,
            "date": ds,
            "week": wk,
            "assigned_shift": v,
            "shift_start": bas,
            "shift_end": bit,
            "work": solver.Value(work[(a, ds)]) if (a, ds) in work else None,
            "overtime_week": solver.Value(overtime_week[(a, wk)]) if wk is not None and (a, wk) in overtime_week else None,
        })

resmi_tatil_ihlal_df = pd.DataFrame(resmi_tatil_ihlal_rows)

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

if len(resmi_tatil_ihlal_df) > 0:
    resmi_tatil_ihlal_df = resmi_tatil_ihlal_df.merge(
        agent_info,
        on="agent_user_code",
        how="left"
    )

print("Resmi tatil kısıtlı ihlal sayısı:", len(resmi_tatil_ihlal_df))

display(
    resmi_tatil_ihlal_df
    .sort_values(["date", "shift_start", "takim", "agent_user_code"])
)
