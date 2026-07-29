# %% [KISIT] - AYDA EN AZ 1 GERÇEK CUMARTESİ-PAZAR ÇİFT OFF

# --------------------------------------------------
# 1) PLAN İÇİNDEKİ CUMARTESİ-PAZAR ÇİFTLERİ
# --------------------------------------------------

plan_date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

weekend_pairs = []

for sat_date, sat_ds in plan_date_to_ds.items():

    if sat_date.weekday() != 5:
        continue

    sun_date = sat_date + pd.Timedelta(days=1)

    if sun_date in plan_date_to_ds:
        weekend_pairs.append(
            (
                sat_ds,
                plan_date_to_ds[sun_date]
            )
        )


# --------------------------------------------------
# 2) GERÇEK OFF DEĞİŞKENLERİ
# --------------------------------------------------
#
# Gerçek izin:
#     gerçek OFF sayılmaz.
#
# off_t2:
#     hard OFF olduğu için gerçek OFF sayılır.
#
# off_t:
#     hard açıksa gerçek OFF sayılır.
#     soft olduğunda model çalıştırmazsa normal OFF sayılır.
#
# Normal gün:
#     work=0 ise gerçek OFF,
#     work=1 ise OFF değildir.

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

        # Gerçek izin çift OFF sayılmaz
        if ds_date in izin_gunleri:

            model.Add(
                gercek_off[(a, ds)] == 0
            )

        # off_t2 her zaman hard ve gerçek OFF
        elif ds_date in off_t2_gunleri:

            model.Add(
                gercek_off[(a, ds)] == 1
            )

        # off_t hard moddaysa gerçek OFF
        elif (
            ENABLE_OFF_T_HARD
            and ds_date in off_t_gunleri
        ):

            model.Add(
                gercek_off[(a, ds)] == 1
            )

        else:

            # Normal gün veya ileride soft off_t günü:
            # çalışmıyorsa OFF, çalışıyorsa OFF değil
            model.Add(
                gercek_off[(a, ds)]
                + work[(a, ds)]
                == 1
            )


# --------------------------------------------------
# 3) CUMARTESİ-PAZAR ÇİFT OFF DEĞİŞKENLERİ
# --------------------------------------------------

pair_off = {}
weekend_pair_constraints = 0

for a_raw in AGENTS:

    a = str(a_raw).strip()
    agent_pair_vars = []

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs):

        pair_off[(a, i)] = model.NewBoolVar(
            f"pair_off_{a}_{i}"
        )

        # pair_off ancak iki gün de gerçek OFF ise 1 olabilir
        model.Add(
            pair_off[(a, i)]
            <= gercek_off[(a, sat_ds)]
        )

        model.Add(
            pair_off[(a, i)]
            <= gercek_off[(a, sun_ds)]
        )

        # İki gün de gerçek OFF ise pair_off mutlaka 1
        model.Add(
            pair_off[(a, i)]
            >=
            gercek_off[(a, sat_ds)]
            + gercek_off[(a, sun_ds)]
            - 1
        )

        agent_pair_vars.append(
            pair_off[(a, i)]
        )

        weekend_pair_constraints += 3

    # Her agent ayda en az bir gerçek Cmt-Paz çift OFF almalı
    if agent_pair_vars:

        model.Add(
            sum(agent_pair_vars) >= 1
        )

        weekend_pair_constraints += 1


print("Cumartesi-Pazar çifti:", len(weekend_pairs))
print("Gerçek OFF değişkeni:", len(gercek_off))
print("Pair OFF değişkeni:", len(pair_off))
print("Çift OFF kısıtı:", weekend_pair_constraints)
