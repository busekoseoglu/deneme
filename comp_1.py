# %% [KISIT] - AYDA EN AZ 1 GERÇEK CUMARTESİ-PAZAR ÇİFT OFF

# --------------------------------------------------
# MANTIK
# --------------------------------------------------
#
# izin:
#     Çalışılmayan gün olsa da gerçek OFF sayılmaz.
#
# off_t2:
#     Her zaman hard OFF'tur ve gerçek OFF sayılır.
#
# off_t:
#     ENABLE_OFF_T_HARD=True ise hard OFF'tur ve
#     gerçek OFF sayılır.
#
#     ENABLE_OFF_T_HARD=False ise soft taleptir.
#     Model o gün çalıştırmazsa work=0 olur ve
#     gerçek OFF sayılır.
#
# Normal gün:
#     work=0 ise gerçek OFF,
#     work=1 ise OFF değildir.
#
# Çift OFF:
#     Cumartesi ve pazarın ikisi de gerçek OFF ise oluşur.


# --------------------------------------------------
# 1) PLAN İÇİNDEKİ CUMARTESİ-PAZAR ÇİFTLERİ
# --------------------------------------------------

plan_date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

weekend_pairs = []

for sat_date, sat_ds in plan_date_to_ds.items():

    # Sadece cumartesiler
    if sat_date.weekday() != 5:
        continue

    sun_date = (
        pd.Timestamp(sat_date)
        + pd.Timedelta(days=1)
    ).date()

    # Pazar da plan dönemi içindeyse çifti ekle
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

        # Gerçek izin, çift OFF hesabında OFF sayılmaz
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

            # Normal gün veya soft off_t günü:
            #
            # work=0 → gercek_off=1
            # work=1 → gercek_off=0

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

for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_pair_vars = []

    for pair_index, (sat_ds, sun_ds) in enumerate(
        weekend_pairs
    ):

        pair_off[(a, pair_index)] = model.NewBoolVar(
            f"pair_off_{a}_{pair_index}"
        )

        # Cumartesi gerçek OFF değilse pair_off=0
        model.Add(
            pair_off[(a, pair_index)]
            <= gercek_off[(a, sat_ds)]
        )

        # Pazar gerçek OFF değilse pair_off=0
        model.Add(
            pair_off[(a, pair_index)]
            <= gercek_off[(a, sun_ds)]
        )

        # İki gün de gerçek OFF ise pair_off=1
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

    # Her agent ayda en az bir gerçek
    # Cumartesi-Pazar çift OFF almalı
    if agent_pair_vars:

        model.Add(
            sum(agent_pair_vars) >= 1
        )

        cift_off_kisit_sayisi += 1


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
