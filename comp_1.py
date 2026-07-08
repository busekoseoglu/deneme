# =================================================
# 11.A) HAFTA SONU ÇALIŞMA KONTROLÜ
# =================================================
# Amaç:
# Her agent ay içinde kaç Cumartesi/Pazar çalışmış onu görmek.
#
# Bu kontrol iş biriminin baktığı:
# "Ayda 5 hafta sonu günü çalışan kişi var mı?"
# sorusunu cevaplar.

weekend_days_export = [
    ds
    for ds in PLAN_GUNLER
    if pd.to_datetime(ds).weekday() in [5, 6]
]

weekend_work_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    hafta_sonu_calistigi_gun = 0
    hafta_sonu_off_gun = 0
    hafta_sonu_calistigi_tarihler = []
    hafta_sonu_off_tarihler = []

    for ds in weekend_days_export:

        worked = 0

        if (a, ds) in work:
            worked = safe_solver_value(work[(a, ds)])

        if worked == 1:
            hafta_sonu_calistigi_gun += 1
            hafta_sonu_calistigi_tarihler.append(ds_key(ds))
        else:
            hafta_sonu_off_gun += 1
            hafta_sonu_off_tarihler.append(ds_key(ds))

    weekend_work_rows.append({
        "agent_user_code": a,
        "agent_name": info.get("agent_name"),
        "takim": info.get("takim"),
        "teamleader_name": info.get("teamleader_name"),
        "working_main_group": info.get("working_main_group"),
        "line_based_main_group": info.get("line_based_main_group"),
        "hafta_sonu_toplam_gun": len(weekend_days_export),
        "hafta_sonu_calistigi_gun": hafta_sonu_calistigi_gun,
        "hafta_sonu_off_gun": hafta_sonu_off_gun,
        "hafta_sonu_calistigi_tarihler": ", ".join(hafta_sonu_calistigi_tarihler),
        "hafta_sonu_off_tarihler": ", ".join(hafta_sonu_off_tarihler),
        "hafta_sonu_5_ve_uzeri_mi": hafta_sonu_calistigi_gun >= 5,
    })

weekend_work_agent_df = pd.DataFrame(weekend_work_rows)

weekend_work_distribution_df = (
    weekend_work_agent_df
    .groupby("hafta_sonu_calistigi_gun", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("hafta_sonu_calistigi_gun")
)


# =================================================
# 11.B) PARTIAL WEEK / WEEKLY TARGET DEBUG EXPORT
# =================================================
# Amaç:
# W27 gibi ay sonu/ay başı bölünen haftalarda weekly target skip edilmiş mi görmek.
#
# Beklenen:
# W27 için:
# normal_target = NaN
# partial_week = True
# partial_type = partial_end
# partial_week_reason = weekly_target_skip

weekly_target_debug_export_df = (
    weekly_target_debug_df.copy()
    if "weekly_target_debug_df" in globals()
    and isinstance(weekly_target_debug_df, pd.DataFrame)
    else pd.DataFrame()
)

week_boundary_export_df = (
    week_boundary_df.copy()
    if "week_boundary_df" in globals()
    and isinstance(week_boundary_df, pd.DataFrame)
    else pd.DataFrame()
)


# =================================================
# 11.C) AGENT AYLIK GÜN KONTROL EXPORT
# =================================================
# Daha detaylı 30 gün kontrol hücresini çalıştırdıysan onu da Excel'e ekle.
# Yoksa boş dataframe olarak geçer.

agent_month_control_export_df = (
    agent_month_control_df.copy()
    if "agent_month_control_df" in globals()
    and isinstance(agent_month_control_df, pd.DataFrame)
    else pd.DataFrame()
)


    {
        "kontrol": "Hafta sonu 5 ve üzeri çalışan agent",
        "deger": weekend_work_agent_df["hafta_sonu_5_ve_uzeri_mi"].sum(),
        "beklenen": "mümkün olduğunca düşük / 0 tercih",
    },
    {
        "kontrol": "Partial week sayısı",
        "deger": len(partial_weeks) if "partial_weeks" in globals() else 0,
        "beklenen": "ay başı/ay sonuna göre değişebilir",
    },
    {
        "kontrol": "Weekly target debug partial skip satırı",
        "deger": (
            weekly_target_debug_export_df[
                weekly_target_debug_export_df.get("partial_week", False) == True
            ].shape[0]
            if not weekly_target_debug_export_df.empty
            and "partial_week" in weekly_target_debug_export_df.columns
            else 0
        ),
        "beklenen": "partial week varsa agent sayısı kadar olabilir",
    },


sheet_df_map = {
    "00_Ozet": summary_df,
    "01_df_tam": df_tam.copy(),

    # DİKKAT:
    # Bu senin orijinal df_off tablon değil.
    # Model sonucunda OFF kalan günleri gösteriyor.
    "02_Model_OFF": df_off_export,

    "03_Vardiya_Talep": vardiya_talep_df,
    "04_Aylik_Takvim": calendar_shift_df,
    "05_Coverage": coverage_simple_df,
    "06_Vardiya_Ozet": vardiya_ozet_df,
    "07_Agent_Aylik_Ozet": agent_monthly_df,

    # Yeni eklenmesi gerekenler
    "08_Roster_Long": agent_day_plan_df,
    "09_Agent_Gun_Kontrol": agent_month_control_export_df,
    "10_Hafta_Sonu_Agent": weekend_work_agent_df,
    "11_Hafta_Sonu_Dagilim": weekend_work_distribution_df,
    "12_Weekly_Target_Debug": weekly_target_debug_export_df,
    "13_Week_Boundary": week_boundary_export_df,
}
