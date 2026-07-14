# %% KONTROL - GÜNLÜK 15:00 SONRASI LOKASYON DAĞILIMI
#
# Her gün için:
# - 15:00 sonrası kapsama giren vardiyaların toplam required değeri
# - Bu vardiyalara toplam kaç kişi atandığı
# - Her lokasyondan kaç kişi geldiği
# - Lokasyon hedefi
# - Hedeften sapma
#
# birlikte gösterilir.

gunluk_lokasyon_kontrol_rows = []

for ds, day_shift_keys in aksam_gece_shifts_by_day.items():

    # -------------------------------------------------
    # 1) Günün 15:00 sonrası toplam required değeri
    # -------------------------------------------------

    daily_required = sum(
        int(talep[(d, v)])
        for d, v in day_shift_keys
        if (d, v) in talep
    )

    # -------------------------------------------------
    # 2) Günün 15:00 sonrası toplam gerçekleşen ataması
    # -------------------------------------------------

    daily_assigned = sum(
        solver.Value(x[(a, d, v)])
        for a in AGENTS
        for d, v in day_shift_keys
        if (a, d, v) in x
    )

    row = {
        "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
        "week": day_week.get(ds),
        "vardiya_sayisi": len(day_shift_keys),
        "required_total": daily_required,
        "assigned_total": daily_assigned,
        "coverage_gap": daily_assigned - daily_required,
    }

    takip_edilen_lokasyon_toplam = 0

    # -------------------------------------------------
    # 3) Her lokasyondan gelen kişi sayısı
    # -------------------------------------------------

    for loc in oran_lokasyonlari:

        config_oran = float(lokasyon_oranlari[loc])

        actual_count = sum(
            solver.Value(x[(a, d, v)])
            for a in AGENTS
            if agent_location_map.get(str(a).strip()) == loc
            for d, v in day_shift_keys
            if (a, d, v) in x
        )

        target_count = int(round(daily_required * config_oran))

        actual_ratio_to_required = (
            actual_count / daily_required
            if daily_required > 0
            else 0
        )

        row[f"{loc}_hedef"] = target_count
        row[f"{loc}_gelen"] = actual_count
        row[f"{loc}_fark"] = actual_count - target_count
        row[f"{loc}_oran_pct"] = round(
            actual_ratio_to_required * 100,
            2
        )

        takip_edilen_lokasyon_toplam += actual_count

    # Config'te oran tanımlanmayan diğer lokasyonlar
    row["diger_lokasyon_gelen"] = (
        daily_assigned - takip_edilen_lokasyon_toplam
    )

    gunluk_lokasyon_kontrol_rows.append(row)


gunluk_lokasyon_kontrol_df = pd.DataFrame(
    gunluk_lokasyon_kontrol_rows
)

gunluk_lokasyon_kontrol_df = (
    gunluk_lokasyon_kontrol_df
    .sort_values(["date"])
    .reset_index(drop=True)
)

display(gunluk_lokasyon_kontrol_df)
