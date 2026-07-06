# %% [HÜCRE] - HAFTALIK TAKIM BASE KAPASİTE KORUMASI - GENEL
# Amaç:
# Takım hard kuralı varken, hafta içi talebi olan hiçbir vardiya base seçimsiz kalmasın.
#
# Mantık:
# Bir vardiyanın hafta içi talebi varsa,
# o hafta o vardiyayı base seçen takımların toplam kişi sayısı,
# o vardiyanın haftadaki maksimum lower buffer ihtiyacını karşılamalı.
#
# Böylece V01 gibi hiçbir vardiya selected_team_count=0 kalmaz.

team_base_capacity_constraints = 0
team_base_capacity_debug_rows = []

# Takım büyüklükleri
team_size_map = (
    df_tam
    .assign(takim=df_tam["takim"].astype(str).str.strip())
    .groupby("takim")["agent_user_code"]
    .nunique()
    .to_dict()
)

for wk in WEEKS:

    # Bu hafta özel günler hariç hafta içi günler
    normal_weekdays = []

    for ds in week_days[wk]:

        if "ozel_tatil_plan_gunleri" in globals() and ds in ozel_tatil_plan_gunleri:
            continue

        weekday = pd.to_datetime(ds).weekday()

        if weekday in [0, 1, 2, 3, 4]:
            normal_weekdays.append(ds)

    if not normal_weekdays:
        continue

    # Bu haftadaki weekday vardiya kodları
    vardiyalar_this_week = sorted(
        set(
            v
            for ds in normal_weekdays
            for v in gun_vardiyalari.get(ds, [])
            if (ds, v) in talep
            and (ds, v) in saat
            and v not in arife_ozel_vardiya_kodlari
        )
    )

    for v in vardiyalar_this_week:

        # Bu vardiyanın o hafta hafta içindeki maksimum ihtiyacı
        required_values = []

        for ds in normal_weekdays:

            if (ds, v) not in talep:
                continue

            required = int(talep[(ds, v)])

            # Buffer lower varsa onu kullan.
            # Yoksa required kullan.
            lower_req = coverage_lower.get((ds, v), required) if "coverage_lower" in globals() else required

            required_values.append(lower_req)

        if not required_values:
            continue

        max_needed = max(required_values)

        # Talep 0 ise kapasite zorlamaya gerek yok
        if max_needed <= 0:
            continue

        # Bu vardiyayı base seçebilen takımların kapasite terimleri
        selected_team_capacity_terms = []

        for t in TAKIMLAR:
            t = str(t).strip()

            if (t, wk, v) not in team_week_base:
                continue

            team_size = int(team_size_map.get(t, 0))

            selected_team_capacity_terms.append(
                team_size * team_week_base[(t, wk, v)]
            )

        if not selected_team_capacity_terms:
            team_base_capacity_debug_rows.append({
                "week": wk,
                "shift": v,
                "start": None,
                "end": None,
                "max_needed": max_needed,
                "status": "team_week_base_yok"
            })
            continue

        # Genel kapasite guard
        model.Add(
            sum(selected_team_capacity_terms) >= max_needed
        )

        team_base_capacity_constraints += 1

        # Saat bilgisi
        start, end = None, None
        for ds in normal_weekdays:
            if (ds, v) in saat:
                start, end = saat[(ds, v)]
                break

        team_base_capacity_debug_rows.append({
            "week": wk,
            "shift": v,
            "start": start,
            "end": end,
            "max_needed": max_needed,
            "status": "constraint_added"
        })

team_base_capacity_debug_df = pd.DataFrame(team_base_capacity_debug_rows)

print("Haftalık takım base kapasite guard kısıtı:", team_base_capacity_constraints)

display(
    team_base_capacity_debug_df
    .sort_values(["week", "start", "end", "shift"])
)