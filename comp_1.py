# %% [KISIT] - AYDA EN AZ 1 GERÇEK CUMARTESİ-PAZAR ÇİFT OFF

# --------------------------------------------------
# MANTIK
# --------------------------------------------------
#
# izin:
#     Çalışılmayan gün olsa da gerçek OFF sayılmaz.
#
# off_t2:
#     Her zaman gerçek OFF sayılır.
#
# off_t:
#     ENABLE_OFF_T_HARD=True ise gerçek OFF sayılır.
#     ENABLE_OFF_T_HARD=False ise çalışılmadığında gerçek OFF sayılır.
#
# Normal gün:
#     work=0 ise gerçek OFF,
#     work=1 ise OFF değildir.
#
# Ayın tamamı izinli olan agent:
#     Modelde kalır, bütün günleri izin olur.
#     Ancak bu agent için çift OFF zorunluluğu kurulmaz.


# --------------------------------------------------
# 1) PLAN İÇİNDEKİ CUMARTESİ-PAZAR ÇİFTLERİ
# --------------------------------------------------

plan_date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

plan_date_set = set(
    plan_date_to_ds.keys()
)

weekend_pairs = []

for sat_date, sat_ds in plan_date_to_ds.items():

    if sat_date.weekday() != 5:
        continue

    sun_date = (
        pd.Timestamp(sat_date)
        + pd.Timedelta(days=1)
    ).date()

    if sun_date in plan_date_to_ds:

        weekend_pairs.append(
            (
                sat_ds,
                plan_date_to_ds[sun_date],
            )
        )


# --------------------------------------------------
# 2) GERÇEK OFF DEĞİŞKENLERİ
# --------------------------------------------------

gercek_off = {}

for a_raw in AGENTS:

    a = str(a_raw).strip()

    izin_gunleri = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    off_t2_gunleri = {
        pd.to_datetime(d).date()
        for d in off_t2_map.get(a, set())
    }

    off_t_gunleri = {
        pd.to_datetime(d).date()
        for d in off_t_map.get(a, set())
    }

    for ds in PLAN_GUNLER:

        ds_date = pd.to_datetime(ds).date()

        gercek_off[(a, ds)] = model.NewBoolVar(
            f"gercek_off_{a}_{ds}"
        )

        # İzin günü gerçek OFF değildir
        if ds_date in izin_gunleri:

            model.Add(
                gercek_off[(a, ds)] == 0
            )

        # off_t2 her zaman gerçek OFF
        elif ds_date in off_t2_gunleri:

            model.Add(
                gercek_off[(a, ds)] == 1
            )

        # Hard moddaki off_t gerçek OFF
        elif (
            ENABLE_OFF_T_HARD
            and ds_date in off_t_gunleri
        ):

            model.Add(
                gercek_off[(a, ds)] == 1
            )

        else:

            # Normal gün veya soft off_t:
            # çalışmıyorsa gerçek OFF
            model.Add(
                gercek_off[(a, ds)]
                + work[(a, ds)]
                == 1
            )


# --------------------------------------------------
# 3) CUMARTESİ-PAZAR ÇİFT OFF DEĞİŞKENLERİ
# --------------------------------------------------

pair_off = {}

cift_off_kisit_sayisi = 0
cift_off_zorunlulugu_olan_agent = 0
cift_off_zorunlulugu_olmayan_agent = 0

cift_off_debug_rows = []

for a_raw in AGENTS:

    a = str(a_raw).strip()

    izin_gunleri = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    plan_ici_izin_gunleri = (
        izin_gunleri
        & plan_date_set
    )

    # Planın bütün günleri izinliyse çift OFF zorunluluğu kurulmaz
    tum_plan_izinli = (
        len(plan_date_set) > 0
        and plan_date_set.issubset(
            plan_ici_izin_gunleri
        )
    )

    agent_pair_vars = []

    for pair_index, (sat_ds, sun_ds) in enumerate(
        weekend_pairs
    ):

        pair_off[(a, pair_index)] = model.NewBoolVar(
            f"pair_off_{a}_{pair_index}"
        )

        model.Add(
            pair_off[(a, pair_index)]
            <= gercek_off[(a, sat_ds)]
        )

        model.Add(
            pair_off[(a, pair_index)]
            <= gercek_off[(a, sun_ds)]
        )

        model.Add(
            pair_off[(a, pair_index)]
            >= gercek_off[(a, sat_ds)]
            + gercek_off[(a, sun_ds)]
            - 1
        )

        agent_pair_vars.append(
            pair_off[(a, pair_index)]
        )

        cift_off_kisit_sayisi += 3

    # Yalnızca ay içinde çalışabilecek agent için
    # en az bir gerçek çift OFF zorunluluğu kur
    if agent_pair_vars and not tum_plan_izinli:

        model.Add(
            sum(agent_pair_vars) >= 1
        )

        cift_off_kisit_sayisi += 1
        cift_off_zorunlulugu_olan_agent += 1

    else:

        cift_off_zorunlulugu_olmayan_agent += 1

    cift_off_debug_rows.append({
        "agent_user_code": a,
        "izin_gun_sayisi_plan_ici": len(
            plan_ici_izin_gunleri
        ),
        "plan_gun_sayisi": len(
            plan_date_set
        ),
        "tum_plan_izinli": tum_plan_izinli,
        "cift_off_zorunlulugu_kuruldu": (
            bool(agent_pair_vars)
            and not tum_plan_izinli
        ),
    })


cift_off_debug_df = pd.DataFrame(
    cift_off_debug_rows
)


# --------------------------------------------------
# 4) BİLGİ ÇIKTISI
# --------------------------------------------------

print(
    "Plan içindeki Cumartesi-Pazar çifti:",
    len(weekend_pairs)
)

print(
    "Gerçek OFF değişkeni:",
    len(gercek_off)
)

print(
    "Pair OFF değişkeni:",
    len(pair_off)
)

print(
    "Çift OFF kısıt sayısı:",
    cift_off_kisit_sayisi
)

print(
    "Çift OFF zorunluluğu kurulan agent:",
    cift_off_zorunlulugu_olan_agent
)

print(
    "Tüm ay izinli olduğu için çift OFF zorunluluğu kurulmayan agent:",
    cift_off_zorunlulugu_olmayan_agent
)