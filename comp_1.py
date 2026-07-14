# -------------------------------------------------
# 3.4) GÜN-VARDİYA BAZINDA LOKASYON ORAN KURALI
# -------------------------------------------------
# Her akşam/gece vardiyası kendi required değeri üzerinden değerlendirilir.
#
# Örnek:
# 2026-06-03 / 17:00-01:00 required = 20
# İzmir oranı = 0.30 -> hedef yaklaşık 6
# Gebze oranı = 0.30 -> hedef yaklaşık 6
# Samsun oranı = 0.30 -> hedef yaklaşık 6
#
# Kural soft'tur. Sapmalar objective içinde cezalandırılır.

lokasyon_aksam_gece_sapma_terms = []

lokasyon_aksam_gece_count = {}
lokasyon_aksam_gece_target = {}
lokasyon_aksam_gece_diff = {}
lokasyon_aksam_gece_abs_diff = {}
lokasyon_aksam_gece_max_possible = {}

lokasyon_aksam_gece_debug_rows = []


for ds, v in aksam_gece_shift_keys:

    if (ds, v) not in talep:
        continue

    required = int(talep[(ds, v)])

    for loc in oran_lokasyonlari:

        oran = float(lokasyon_oranlari[loc])

        # Bu gün-vardiya için bu lokasyondan atanabilecek x değişkenleri
        loc_assignment_vars = [
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
            and agent_location_map.get(str(a).strip()) == loc
        ]

        max_possible = len(loc_assignment_vars)

        key = (ds, v, loc)

        lokasyon_aksam_gece_max_possible[key] = max_possible

        lokasyon_aksam_gece_count[key] = model.NewIntVar(
            0,
            max_possible,
            f"lokasyon_aksam_gece_count_{ds}_{v}_{loc}"
        )

        if loc_assignment_vars:
            model.Add(
                lokasyon_aksam_gece_count[key]
                ==
                sum(loc_assignment_vars)
            )
        else:
            model.Add(
                lokasyon_aksam_gece_count[key] == 0
            )

        # O gün-vardiyanın required değerine göre lokasyon hedefi
        target = int(round(required * oran))

        lokasyon_aksam_gece_target[key] = target

        # count - target farkı
        diff_lb = -target
        diff_ub = max_possible - target

        lokasyon_aksam_gece_diff[key] = model.NewIntVar(
            diff_lb,
            diff_ub,
            f"lokasyon_aksam_gece_diff_{ds}_{v}_{loc}"
        )

        model.Add(
            lokasyon_aksam_gece_diff[key]
            ==
            lokasyon_aksam_gece_count[key] - target
        )

        max_abs_diff = max(
            abs(diff_lb),
            abs(diff_ub)
        )

        lokasyon_aksam_gece_abs_diff[key] = model.NewIntVar(
            0,
            max_abs_diff,
            f"lokasyon_aksam_gece_abs_diff_{ds}_{v}_{loc}"
        )

        model.AddAbsEquality(
            lokasyon_aksam_gece_abs_diff[key],
            lokasyon_aksam_gece_diff[key]
        )

        lokasyon_aksam_gece_sapma_terms.append(
            LOKASYON_AKSAM_GECE_ORAN_SAPMA_W
            * lokasyon_aksam_gece_abs_diff[key]
        )

        shift_start, shift_end = _get_shift_time_for_aksam_gece(ds, v)

        lokasyon_aksam_gece_debug_rows.append({
            "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
            "week": day_week.get(ds),
            "shift": v,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "lokasyon": loc,
            "config_oran": oran,
            "required": required,
            "hedef_atama": target,
            "max_possible_var_count": max_possible,
            "sapma_weight": LOKASYON_AKSAM_GECE_ORAN_SAPMA_W,
            "kural_tipi": "gun_vardiya_soft_abs_diff"
        })


lokasyon_aksam_gece_debug_df = pd.DataFrame(
    lokasyon_aksam_gece_debug_rows
)

print("Gün-vardiya-lokasyon soft kural sayısı:",
      len(lokasyon_aksam_gece_abs_diff))

print("Lokasyon akşam/gece hedefleri:")
display(
    lokasyon_aksam_gece_debug_df
    .sort_values(["date", "shift_start", "lokasyon"])
    .head(100)
)
