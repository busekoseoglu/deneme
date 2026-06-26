# %% KONTROL - HER AGENT KAÇ GÜN ÇALIŞMIŞ?

agent_work_rows = []

for a in AGENTS:
    izinli = izin_map.get(a, set())

    toplam_calisilan_gun = 0
    toplam_izinli_gun = 0
    toplam_off_gun = 0
    toplam_mesai = 0

    for ds in PLAN_GUNLER:
        worked = solver.Value(work[(a, ds)])

        is_izinli = pd.to_datetime(ds).date() in izinli

        toplam_calisilan_gun += worked

        if is_izinli:
            toplam_izinli_gun += 1

        if worked == 0 and not is_izinli:
            toplam_off_gun += 1

    for wk in WEEKS:
        toplam_mesai += solver.Value(overtime_week[(a, wk)])

    agent_work_rows.append({
        "agent_user_code": a,
        "toplam_calisilan_gun": toplam_calisilan_gun,
        "toplam_off_gun": toplam_off_gun,
        "toplam_izinli_gun": toplam_izinli_gun,
        "toplam_mesai": toplam_mesai,
        "plan_gun_sayisi": len(PLAN_GUNLER)
    })

agent_work_summary = pd.DataFrame(agent_work_rows)

# Agent bilgileriyle birleştir
agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

agent_work_summary = agent_work_summary.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

display(
    agent_work_summary
    .sort_values("toplam_calisilan_gun", ascending=False)
)
