# %% KONTROL - GÜNLÜK AKŞAM/GECE LOKASYON DAĞILIMI
#
# Kullanılan mevcut değişkenler:
# - aksam_gece_shift_keys
# - talep
# - x
# - solver
# - AGENTS
# - agent_location_map
# - lokasyon_oranlari
# - day_week
#
# Her gün için:
# 1. 15:00 sonrası kapsamdaki vardiyaların required toplamı
# 2. Toplam atanan kişi
# 3. İzmir / Gebze / Samsun hedefi
# 4. Her lokasyondan gerçekten gelen kişi
# 5. Hedeften fark

gunluk_lokasyon_rows = []

aksam_gece_gunleri = sorted(
    set(ds for ds, v in aksam_gece_shift_keys),
    key=lambda ds: pd.to_datetime(ds)
)

for ds in aksam_gece_gunleri:

    # Bu güne ait akşam/gece vardiyaları
    gun_shift_keys = [
        (d, v)
        for d, v in aksam_gece_shift_keys
        if d == ds and (d, v) in talep
    ]

    # Günlük toplam required
    required_total = sum(
        int(talep[(d, v)])
        for d, v in gun_shift_keys
    )

    # Günlük toplam atama
    assigned_total = sum(
        solver.Value(x[(a, d, v)])
        for a in AGENTS
        for d, v in gun_shift_keys
        if (a, d, v) in x
    )

    row = {
        "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
        "week": day_week.get(ds),
        "aksam_gece_vardiya_sayisi": len(gun_shift_keys),
        "required_total": required_total,
        "assigned_total": assigned_total,
        "coverage_gap": assigned_total - required_total,
    }

    takip_edilen_lokasyon_atama = 0

    for loc, oran in lokasyon_oranlari.items():

        loc = str(loc).strip().lower()
        oran = float(oran)

        gelen = sum(
            solver.Value(x[(a, d, v)])
            for a in AGENTS
            if agent_location_map.get(str(a).strip()) == loc
            for d, v in gun_shift_keys
            if (a, d, v) in x
        )

        hedef = int(round(required_total * oran))

        row[f"{loc}_oran"] = oran
        row[f"{loc}_hedef"] = hedef
        row[f"{loc}_gelen"] = gelen
        row[f"{loc}_fark"] = gelen - hedef

        row[f"{loc}_gercek_oran_pct"] = round(
            (gelen / required_total * 100)
            if required_total > 0
            else 0,
            2
        )

        takip_edilen_lokasyon_atama += gelen

    row["diger_lokasyon_gelen"] = (
        assigned_total - takip_edilen_lokasyon_atama
    )

    gunluk_lokasyon_rows.append(row)


gunluk_lokasyon_kontrol_df = pd.DataFrame(
    gunluk_lokasyon_rows
).sort_values("date").reset_index(drop=True)

display(gunluk_lokasyon_kontrol_df)
