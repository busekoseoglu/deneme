# %% [KONTROL] - AGENT HAFTA SONU ÇALIŞMA SAYISI
# Amaç:
# Her agent'ın plan ayı içinde kaç hafta sonu günü çalıştığını görmek.
#
# Mantık:
# - PLAN_GUNLER içinden Cumartesi/Pazar günleri alınır.
# - work[(agent, gün)] solver sonucunda 1 ise agent o hafta sonu günü çalışmıştır.
# - Agent bazında toplam hafta sonu çalışma günü hesaplanır.
# - Sonra "kaç kişi 0 gün, kaç kişi 1 gün, kaç kişi 5 gün..." şeklinde dağılım çıkarılır.

weekend_work_rows = []

# --------------------------------------------------
# 1) Plan ayındaki hafta sonu günleri
# --------------------------------------------------

weekend_days = [
    ds
    for ds in PLAN_GUNLER
    if pd.to_datetime(ds).weekday() in [5, 6]
]

print("Plan ayındaki hafta sonu günleri:", weekend_days)
print("Hafta sonu gün sayısı:", len(weekend_days))

# --------------------------------------------------
# 2) Agent bazında hafta sonu çalışma sayısı
# --------------------------------------------------

for _, row in df_tam.iterrows():

    a = str(row["agent_user_code"]).strip()

    agent_name = row.get("agent_name", None)
    teamleader_name = row.get("teamleader_name", None)
    working_main_group = row.get("working_main_group", None)
    line_based_main_group = row.get("line_based_main_group", None)

    hafta_sonu_calistigi_gun = 0
    hafta_sonu_off_gun = 0

    worked_weekend_dates = []
    off_weekend_dates = []

    for ds in weekend_days:

        worked = 0

        if (a, ds) in work:
            worked = int(solver.Value(work[(a, ds)]))

        if worked == 1:
            hafta_sonu_calistigi_gun += 1
            worked_weekend_dates.append(ds)
        else:
            hafta_sonu_off_gun += 1
            off_weekend_dates.append(ds)

    weekend_work_rows.append({
        "agent_user_code": a,
        "agent_name": agent_name,
        "teamleader_name": teamleader_name,
        "working_main_group": working_main_group,
        "line_based_main_group": line_based_main_group,
        "hafta_sonu_toplam_gun": len(weekend_days),
        "hafta_sonu_calistigi_gun": hafta_sonu_calistigi_gun,
        "hafta_sonu_off_gun": hafta_sonu_off_gun,
        "hafta_sonu_calistigi_tarihler": worked_weekend_dates,
        "hafta_sonu_off_tarihler": off_weekend_dates
    })

weekend_work_agent_df = pd.DataFrame(weekend_work_rows)

print("Agent hafta sonu çalışma kontrolü oluşturuldu.")
print("Agent sayısı:", len(weekend_work_agent_df))

display(
    weekend_work_agent_df
    .sort_values(["hafta_sonu_calistigi_gun", "agent_user_code"], ascending=[False, True])
    .head(30)
)



# %% [KONTROL] - 5 HAFTA SONU GÜNÜ ÇALIŞAN AGENTLAR

display(
    weekend_work_agent_df[
        weekend_work_agent_df["hafta_sonu_calistigi_gun"] == 5
    ]
    .sort_values(["teamleader_name", "agent_user_code"])
)


# %% [KONTROL] - HAFTA SONU ÇALIŞMA LİMİT İHLALİ
# Mevcut iş kuralı:
# 4 güne kadar sorun yok.
# 5 ve üzeri hafta sonu çalışma ceza/ihlal gibi değerlendiriliyor.

HAFTA_SONU_LIMIT = 4

weekend_work_violation_df = (
    weekend_work_agent_df[
        weekend_work_agent_df["hafta_sonu_calistigi_gun"] > HAFTA_SONU_LIMIT
    ]
    .sort_values(["hafta_sonu_calistigi_gun", "agent_user_code"], ascending=[False, True])
)

print("Hafta sonu çalışma limitini aşan agent sayısı:", len(weekend_work_violation_df))

display(weekend_work_violation_df)
