# %% [OBJECTIVE HAZIRLIK] - SOFT OFF_T TALEBİ CEZASI

# off_t hard ise:
#     Agent o gün zaten çalışamaz.
#     Objective cezası oluşturulmaz.
#
# off_t soft ise:
#     Agent o gün çalışmazsa ceza 0 olur.
#     Agent o gün çalışırsa work=1 üzerinden ceza oluşur.

OFF_TALEP_CEZA_W = globals().get(
    "OFF_TALEP_CEZA_W",
    100_000
)

soft_off_objective_terms = []
soft_off_objective_debug_rows = []

# PLAN_GUNLER içindeki tarihleri ds değerlerine bağla
date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

if not ENABLE_OFF_T_HARD:

    for a_raw in AGENTS:

        a = str(a_raw).strip()

        off_t_gunleri = {
            pd.to_datetime(d).date()
            for d in off_t_map.get(a, set())
        }

        for off_date in off_t_gunleri:

            # Talep tarihi plan dönemi dışında olabilir
            if off_date not in date_to_ds:
                continue

            ds = date_to_ds[off_date]

            # Günlük work değişkeni yoksa atla
            if (a, ds) not in work:
                continue

            # Soft OFF talebi karşılanmaz ve agent çalışırsa:
            # work[(a, ds)] = 1 olur ve objective cezası oluşur.
            soft_off_objective_terms.append(
                OFF_TALEP_CEZA_W * work[(a, ds)]
            )

            soft_off_objective_debug_rows.append({
                "agent_user_code": a,
                "date": off_date,
                "mode": "soft",
                "objective_term_created": True,
            })

else:

    print(
        "ENABLE_OFF_T_HARD=True: "
        "off_t talepleri hard olduğu için soft OFF cezası oluşturulmadı."
    )


soft_off_objective_debug_df = pd.DataFrame(
    soft_off_objective_debug_rows
)

print(
    "Soft OFF objective terimi sayısı:",
    len(soft_off_objective_terms)
)

print(
    "Soft OFF ceza ağırlığı:",
    OFF_TALEP_CEZA_W
)
