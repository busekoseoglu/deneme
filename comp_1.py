"ENABLE_TEAM_1500_DENGE": True,

# Ekiplerin geçmiş + mevcut ay 15:00 toplamlarını dengeleme ağırlığı
"TEAM_1500_DENGE_W": 10000,


ENABLE_TEAM_1500_DENGE = CONFIG["ENABLE_TEAM_1500_DENGE"]
TEAM_1500_DENGE_W = CONFIG["TEAM_1500_DENGE_W"]


# %% [KARAR DEĞİŞKENİ + BAĞLANTI] - EKİP 15:00 DENGESİ

team_1500_bu_ay = {}
team_1500_toplam = {}
team_1500_spread = None

if ENABLE_TEAM_1500_DENGE:

    team_1500_max_toplam_possible = (
        max(team_gecmis_1500.values(), default=0)
        + len(WEEKS)
    )

    for t in TAKIMLAR:

        t = str(t).strip()
        gecmis_sayi = int(team_gecmis_1500.get(t, 0))

        bu_ay_1500_vars = []

        for wk in WEEKS:
            for v in week_1500_vardiyalari.get(wk, []):

                if (t, wk, v) in team_week_base:
                    bu_ay_1500_vars.append(
                        team_week_base[(t, wk, v)]
                    )

        team_1500_bu_ay[t] = model.NewIntVar(
            0,
            len(WEEKS),
            f"team_1500_bu_ay_{t}"
        )

        if bu_ay_1500_vars:
            model.Add(
                team_1500_bu_ay[t]
                ==
                sum(bu_ay_1500_vars)
            )
        else:
            model.Add(
                team_1500_bu_ay[t] == 0
            )

        team_1500_toplam[t] = model.NewIntVar(
            gecmis_sayi,
            gecmis_sayi + len(WEEKS),
            f"team_1500_toplam_{t}"
        )

        model.Add(
            team_1500_toplam[t]
            ==
            gecmis_sayi + team_1500_bu_ay[t]
        )

    team_1500_max = model.NewIntVar(
        0,
        team_1500_max_toplam_possible,
        "team_1500_max"
    )

    team_1500_min = model.NewIntVar(
        0,
        team_1500_max_toplam_possible,
        "team_1500_min"
    )

    team_1500_spread = model.NewIntVar(
        0,
        team_1500_max_toplam_possible,
        "team_1500_spread"
    )

    model.AddMaxEquality(
        team_1500_max,
        list(team_1500_toplam.values())
    )

    model.AddMinEquality(
        team_1500_min,
        list(team_1500_toplam.values())
    )

    model.Add(
        team_1500_spread
        ==
        team_1500_max - team_1500_min
    )

    print("15:00 ekip denge kuralı AÇIK.")

else:
    print("15:00 ekip denge kuralı KAPALI.")



# -------------------------------------------------
# EKİP 15:00 TARİHSEL ADALET CEZASI
# -------------------------------------------------

if ENABLE_TEAM_1500_DENGE:

    # Maksimum ve minimum toplam arasındaki farkı azalt
    objective_terms.append(
        TEAM_1500_DENGE_W
        * team_1500_spread
    )

    # Geçmişte çok alan ekibin bu ay tekrar seçilmesini azalt
    for t in TAKIMLAR:

        t = str(t).strip()
        gecmis_sayi = int(team_gecmis_1500.get(t, 0))

        objective_terms.append(
            TEAM_1500_DENGE_W
            * gecmis_sayi
            * team_1500_bu_ay[t]
        )

    print("15:00 ekip denge objective cezası eklendi.")
