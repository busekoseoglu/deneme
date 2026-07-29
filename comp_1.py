# %% [OBJECTIVE HAZIRLIK] - SOFT OFF_T TALEBİ CEZASI

# OFF_TALEP_CEZA_W config hücresinde tanımlıdır.
# Bu hücre herhangi bir ağırlık değeri üretmez veya değiştirmez.

if "OFF_TALEP_CEZA_W" not in globals():
    raise NameError(
        "OFF_TALEP_CEZA_W config hücresinde tanımlı değil."
    )

soft_off_objective_terms = []
soft_off_objective_debug_rows = []

date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

# off_t yalnızca soft moddayken objective cezasına girer
if not ENABLE_OFF_T_HARD:

    for a_raw in AGENTS:

        a = str(a_raw).strip()

        for off_date_raw in off_t_map.get(a, set()):

            off_date = pd.to_datetime(off_date_raw).date()

            # Plan dönemi dışındaki talepler objective'e alınmaz
            if off_date not in date_to_ds:
                continue

            ds = date_to_ds[off_date]

            if (a, ds) not in work:
                continue

            # Soft OFF tarihinde çalışırsa work=1 olur
            # ve config'teki ağırlık kadar ceza oluşur.
            soft_off_objective_terms.append(
                OFF_TALEP_CEZA_W * work[(a, ds)]
            )

            soft_off_objective_debug_rows.append({
                "agent_user_code": a,
                "tarih": off_date,
                "ceza_agirligi": OFF_TALEP_CEZA_W,
            })


soft_off_objective_debug_df = pd.DataFrame(
    soft_off_objective_debug_rows
)

print(
    "ENABLE_OFF_T_HARD:",
    ENABLE_OFF_T_HARD
)

print(
    "Soft OFF objective terimi sayısı:",
    len(soft_off_objective_terms)
)
