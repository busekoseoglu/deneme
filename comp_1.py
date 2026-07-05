# %% KONTROL - ARİFE KISITLI AGENTLARIN TAM DAĞILIMI

arife_kisitli_full_rows = []

for a in AGENTS:
    a = str(a).strip()

    if a not in arife_kisitli_agents:
        continue

    for ds in arife_plan_gunleri:

        ds_key = arife_ds_key(ds)
        hedef_bas, hedef_bit = ARIFE_GUNLERI[ds_key]["kisitli_agent_normal_vardiya"]

        assigned_shift = None
        assigned_start = None
        assigned_end = None
        assigned_is_yasak = False
        assigned_is_arife_mesai = False

        hedef_09_13_var_mi = False
        hedef_09_13_atandi_mi = False

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if (ds, v) not in saat:
                continue

            bas, bit = saat[(ds, v)]

            # Bu agent için 09-13 opsiyonu var mı?
            if bas == hedef_bas and bit == hedef_bit:
                hedef_09_13_var_mi = True

                if solver.Value(x[(a, ds, v)]) == 1:
                    hedef_09_13_atandi_mi = True

            # Atandığı vardiya ne?
            if solver.Value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                assigned_start = bas
                assigned_end = bit
                assigned_is_yasak = arife_kisitli_yasak_vardiya_mi.get((ds, v), False)
                assigned_is_arife_mesai = arife_mesai_vardiyasi_mi.get((ds, v), False)

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

            "hedef_09_13_var_mi": hedef_09_13_var_mi,
            "hedef_09_13_atandi_mi": hedef_09_13_atandi_mi,

            "13_sonrasina_sarkiyor_mu": assigned_is_yasak,
            "arife_mesai_vardiyasi_mi": assigned_is_arife_mesai,

            "arife_09_13_atanamadi_var": (
                solver.Value(arife_09_13_atanamadi[(a, ds)])
                if "arife_09_13_atanamadi" in globals() and (a, ds) in arife_09_13_atanamadi
                else None
            )
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
print("09-13 atanan:", len(arife_kisitli_full_df[arife_kisitli_full_df["hedef_09_13_atandi_mi"] == True]))
print("13 sonrasına sarkan vardiyaya atanan:", len(arife_kisitli_full_df[arife_kisitli_full_df["13_sonrasina_sarkiyor_mu"] == True]))
print("Hiç çalışmayan:", len(arife_kisitli_full_df[(arife_kisitli_full_df["work"] == 0) & (arife_kisitli_full_df["is_leave"] == False)]))
print("İzinli:", len(arife_kisitli_full_df[arife_kisitli_full_df["is_leave"] == True]))

display(
    arife_kisitli_full_df
    .sort_values(["13_sonrasina_sarkiyor_mu", "hedef_09_13_atandi_mi", "takim", "agent_user_code"], ascending=[False, True, True, True])
)
