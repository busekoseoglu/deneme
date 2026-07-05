model.Add(work[(a, ds)] == 0)

model.Add(x[(a, ds, v)] == 0)


model.Add(resmi_tatil_kisitli_ihlal[(a, ds, v)] >= x[(a, ds, v)])



# %% DEBUG - RESMİ TATİL İZİN_MAP'E GİRMİŞ Mİ?

resmi_tatil_izin_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in resmi_tatil_plan_gunleri:
        if ds in izin_map.get(a, set()):
            resmi_tatil_izin_rows.append({
                "agent_user_code": a,
                "date": ds,
                "tatil_kisitli_agent": a in tatil_kisitli_agents
            })

resmi_tatil_izin_df = pd.DataFrame(resmi_tatil_izin_rows)

print("Resmi tatil günü izin_map içinde görünen agent sayısı:", len(resmi_tatil_izin_df))

if len(resmi_tatil_izin_df) > 0:
    display(resmi_tatil_izin_df.head(100))
