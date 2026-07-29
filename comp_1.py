# %% [KARAR DEĞİŞKENİ] - NORMAL ÇALIŞMA TELAFİ HAFTASI

# telafi_week[(agent, hafta)] = 1:
# Agent bu hafta standart hedefinden 1 gün fazla NORMAL çalışır.
#
# Bu çalışma NORMAL_MESAI değildir.
# Sadece başka bir haftadaki ekstra OFF gününü telafi eder.

telafi_week = {}

for a_raw in AGENTS:

    a = str(a_raw).strip()

    for wk in WEEKS:

        telafi_week[(a, wk)] = model.NewBoolVar(
            f"telafi_week_{a}_{wk}"
        )

print(
    "Normal çalışma telafi değişkeni:",
    len(telafi_week)
)


# %% [KISIT] - HAFTALIK NORMAL ÇALIŞMA + HARD OFF + TELAFİ

# Temel mantık:
#
# 0, 1 veya 2 hard OFF talebi:
#     Haftalık normal çalışma hedefi değişmez.
#
# 3 hard OFF talebi:
#     1 ekstra OFF oluşur.
#     O hafta normal çalışma hedefi 1 azalır.
#
# 4 hard OFF talebi:
#     2 ekstra OFF oluşur.
#     O hafta normal çalışma hedefi 2 azalır.
#
# Ekstra OFF başka bir haftada NORMAL çalışma ile telafi edilir.
# Telafi günü NORMAL_MESAI değildir.

extra_off_week = {}

haftalik_off_telafi_debug_rows = []

partial_week_set = {
    str(wk).strip()
    for wk in partial_weeks
}

resmi_tatil_date_set = {
    pd.to_datetime(ds).date()
    for ds in resmi_tatil_plan_gunleri
}

for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_izin_dates = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    agent_off_t2_dates = {
        pd.to_datetime(d).date()
        for d in off_t2_map.get(a, set())
    }

    agent_hard_off_t_dates = set()

    if ENABLE_OFF_T_HARD:

        agent_hard_off_t_dates = {
            pd.to_datetime(d).date()
            for d in off_t_map.get(a, set())
        }

    # Yalnızca gerçek OFF talepleri.
    # İzin günleri burada yoktur.
    agent_hard_off_talep_dates = (
        agent_off_t2_dates
        | agent_hard_off_t_dates
    )

    for wk in WEEKS:

        wk_key = str(wk).strip()

        week_ds = week_days.get(wk, [])

        week_dates = {
            pd.to_datetime(ds).date()
            for ds in week_ds
        }

        week_izin_dates = (
            agent_izin_dates
            & week_dates
        )

        week_resmi_tatil_dates = (
            resmi_tatil_date_set
            & week_dates
        )

        week_hard_off_talep_dates = (
            agent_hard_off_talep_dates
            & week_dates
        )

        # İzin ve resmî tatil aynı güne denk gelirse
        # haftalık hedef yalnızca bir kez düşürülür.
        hedef_dusuren_dates = (
            week_izin_dates
            | week_resmi_tatil_dates
        )

        normal_target = max(
            NORMAL_WORK_DAYS
            - len(hedef_dusuren_dates),
            0,
        )

        # İlk iki hard OFF talebi kişinin standart OFF hakkıdır.
        hard_off_talep_count = len(
            week_hard_off_talep_dates
        )

        extra_off_count = max(
            hard_off_talep_count - 2,
            0,
        )

        extra_off_week[(a, wk)] = model.NewIntVar(
            0,
            len(week_ds),
            f"extra_off_week_{a}_{wk}"
        )

        model.Add(
            extra_off_week[(a, wk)]
            == extra_off_count
        )

        # Resmî tatil günleri normal çalışma sayısına dahil edilmez.
        normal_work_vars = [
            work[(a, ds)]
            for ds in week_ds
            if (
                (a, ds) in work
                and pd.to_datetime(ds).date()
                not in resmi_tatil_date_set
            )
        ]

        # Partial hafta için haftalık normal hedef kurulmayacaksa,
        # bu haftada normal çalışma telafisi de yapılmaz.
        if (
            SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS
            and wk_key in partial_week_set
        ):

            model.Add(
                telafi_week[(a, wk)] == 0
            )

            haftalik_off_telafi_debug_rows.append({
                "agent_user_code": a,
                "week": wk_key,
                "normal_target": normal_target,
                "hard_off_talep_count": hard_off_talep_count,
                "extra_off_count": extra_off_count,
                "telafi_uygun": False,
                "neden": "partial_week",
            })

            continue

        # Ekstra OFF alınan hafta aynı zamanda telafi haftası olamaz.
        if extra_off_count > 0:

            model.Add(
                telafi_week[(a, wk)] == 0
            )

        # Gerçek izin bulunan haftada başka haftanın OFF'u
        # telafi edilmez.
        if len(week_izin_dates) > 0:

            model.Add(
                telafi_week[(a, wk)] == 0
            )

        # Bu haftada normal_target + 1 gün çalışmaya yetecek
        # kullanılabilir normal gün yoksa telafi yapılamaz.
        kullanilabilir_normal_gun_sayisi = sum(
            1
            for ds in week_ds
            if (
                pd.to_datetime(ds).date()
                not in hedef_dusuren_dates
                and pd.to_datetime(ds).date()
                not in week_hard_off_talep_dates
            )
        )

        if kullanilabilir_normal_gun_sayisi < normal_target + 1:

            model.Add(
                telafi_week[(a, wk)] == 0
            )

        # Haftalık normal çalışma eşitliği:
        #
        # normal hedef
        # - bu haftadaki ekstra OFF
        # + başka haftadan gelen normal çalışma telafisi
        model.Add(
            sum(normal_work_vars)
            ==
            normal_target
            - extra_off_week[(a, wk)]
            + telafi_week[(a, wk)]
        )

        haftalik_off_telafi_debug_rows.append({
            "agent_user_code": a,
            "week": wk_key,
            "normal_target": normal_target,
            "hard_off_talep_count": hard_off_talep_count,
            "extra_off_count": extra_off_count,
            "kullanilabilir_normal_gun": (
                kullanilabilir_normal_gun_sayisi
            ),
            "telafi_uygun": (
                extra_off_count == 0
                and len(week_izin_dates) == 0
                and kullanilabilir_normal_gun_sayisi
                >= normal_target + 1
            ),
            "neden": "",
        })


haftalik_off_telafi_debug_df = pd.DataFrame(
    haftalik_off_telafi_debug_rows
)

print(
    "Ekstra OFF hafta değişkeni:",
    len(extra_off_week)
)

print(
    "Normal çalışma telafi değişkeni:",
    len(telafi_week)
)


# %% [KISIT] - AYLIK EKSTRA OFF / NORMAL ÇALIŞMA TELAFİ DENGESİ

# Ay içinde 2'yi aşan hard OFF talebi sayısı,
# başka haftalarda yapılan ekstra NORMAL çalışma sayısına
# kesin olarak eşit olmalıdır.
#
# Bu telafiler NORMAL_MESAI değildir.

aylik_telafi_debug_rows = []

for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_extra_off_vars = [
        extra_off_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in extra_off_week
    ]

    agent_telafi_vars = [
        telafi_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in telafi_week
    ]

    model.Add(
        sum(agent_extra_off_vars)
        ==
        sum(agent_telafi_vars)
    )

    aylik_telafi_debug_rows.append({
        "agent_user_code": a,
        "extra_off_week_var_sayisi": len(
            agent_extra_off_vars
        ),
        "telafi_week_var_sayisi": len(
            agent_telafi_vars
        ),
    })


aylik_telafi_debug_df = pd.DataFrame(
    aylik_telafi_debug_rows
)

print(
    "Aylık ekstra OFF / normal çalışma telafi eşitliği eklendi."
)

print(
    "Agent sayısı:",
    len(AGENTS)
)
