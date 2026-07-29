OFF_TALEP_KARSILANMAMA_W = 100000


# %% [OBJECTIVE HAZIRLIK] - SOFT OFF_T TALEBİ CEZA TERİMLERİ

# ENABLE_OFF_T_HARD = True:
#   off_t günleri hard_off_map içindedir.
#   Agent çalışamaz, objective cezası gerekmez.
#
# ENABLE_OFF_T_HARD = False:
#   off_t günleri soft taleptir.
#   Agent o gün çalışırsa work=1 olur ve objective cezası oluşur.

off_talep_ceza_terms = []

plan_date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

if not ENABLE_OFF_T_HARD:

    for a_raw in AGENTS:

        a = str(a_raw).strip()

        for off_date_raw in off_t_map.get(a, set()):

            off_date = pd.to_datetime(off_date_raw).date()

            # Talep tarihi plan döneminde değilse alma
            if off_date not in plan_date_to_ds:
                continue

            ds = plan_date_to_ds[off_date]

            # work değişkeni yoksa ceza terimi oluşturma
            if (a, ds) not in work:
                continue

            # Soft OFF talebi bulunan günde:
            # work = 0 → OFF talebi karşılandı, ceza yok
            # work = 1 → OFF talebi karşılanmadı, ceza var
            off_talep_ceza_terms.append(
                work[(a, ds)]
            )


print("ENABLE_OFF_T_HARD:", ENABLE_OFF_T_HARD)
print(
    "Soft OFF talebi ceza terimi sayısı:",
    len(off_talep_ceza_terms)
)


OFF_TALEP_KARSILANMAMA_W * sum(off_talep_ceza_terms)


objective_terms.append(
    OFF_TALEP_KARSILANMAMA_W
    * sum(off_talep_ceza_terms)
)
