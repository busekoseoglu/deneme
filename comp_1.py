# %% [HAZIRLIK] - HAFTALIK HARD OFF VE TELAFİ YAPISI

extra_off_week = {}
weekly_target_debug_rows = []

weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_extra_off_balance_constraints = 0
monthly_overtime_constraints = 0


# Mesaiye kalamayan agentlar
mesaiye_kalamaz_agents = set(
    df_tam.loc[
        pd.to_numeric(
            df_tam["mesaiye_kalamaz_flg"],
            errors="coerce"
        ).fillna(0).astype(int) == 1,
        "agent_user_code"
    ]
    .astype(str)
    .str.strip()
)


# Resmî tatilleri date formatına çevir
resmi_tatil_date_set = set()

if "resmi_tatil_plan_gunleri" in globals():

    resmi_tatil_date_set = {
        pd.to_datetime(d).date()
        for d in resmi_tatil_plan_gunleri
    }

elif "RESMI_TATIL_GUNLERI" in globals():

    resmi_tatil_date_set = {
        pd.to_datetime(d).date()
        for d in RESMI_TATIL_GUNLERI
    }


# Partial week ayarı
skip_partial_week = globals().get(
    "SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS",
    True
)

partial_weeks_local = globals().get(
    "partial_weeks",
    set()
)

print("Haftalık hard OFF hazırlığı tamamlandı.")
print("Mesaiye kalamayan agent:", len(mesaiye_kalamaz_agents))
print("Resmî tatil günü:", len(resmi_tatil_date_set))



# %% [KISIT] - HAFTALIK ÇALIŞMA + HARD OFF

for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_izin_gunleri = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    agent_off_t2_gunleri = {
        pd.to_datetime(d).date()
        for d in off_t2_map.get(a, set())
    }

    agent_off_t_gunleri = {
        pd.to_datetime(d).date()
        for d in off_t_map.get(a, set())
    }

    # off_t2 her zaman hard
    agent_hard_talep_gunleri = set(
        agent_off_t2_gunleri
    )

    # off_t config'e göre hard
    if ENABLE_OFF_T_HARD:
        agent_hard_talep_gunleri |= agent_off_t_gunleri


    for wk in WEEKS:

        week_days_list = [
            ds
            for ds in week_days[wk]
            if (a, ds) in work
        ]

        # Her hafta için ekstra OFF değişkeni oluştur
        extra_off_week[(a, wk)] = model.NewIntVar(
            0,
            len(week_days_list),
            f"extra_off_week_{a}_{wk}"
        )

        # -------------------------------------------------
        # PARÇA HAFTA
        # -------------------------------------------------

        wk_is_partial = wk in partial_weeks_local

        if skip_partial_week and wk_is_partial:

            model.Add(
                extra_off_week[(a, wk)] == 0
            )

            if (a, wk) in overtime_week:
                model.Add(
                    overtime_week[(a, wk)] == 0
                )

            weekly_target_debug_rows.append({
                "agent_user_code": a,
                "week": wk,
                "partial_week": True,
                "normal_target": None,
                "izin_sayisi": None,
                "resmi_tatil_sayisi": None,
                "hard_off_talep_sayisi": None,
                "standart_off_sayisi": None,
                "extra_off_sayisi": 0
            })

            continue


        # -------------------------------------------------
        # HAFTALIK GÜN SETLERİ
        # -------------------------------------------------

        week_date_map = {
            ds: pd.to_datetime(ds).date()
            for ds in week_days_list
        }

        resmi_tatil_days_this_week = {
            ds
            for ds, d_date in week_date_map.items()
            if d_date in resmi_tatil_date_set
        }

        izin_days_this_week = {
            ds
            for ds, d_date in week_date_map.items()
            if d_date in agent_izin_gunleri
        }

        # Resmî tatil ile izin aynı güne geldiyse iki kez düşme
        izin_normal_days_this_week = (
            izin_days_this_week
            - resmi_tatil_days_this_week
        )

        hard_talep_days_this_week = {
            ds
            for ds, d_date in week_date_map.items()
            if d_date in agent_hard_talep_gunleri
            and ds not in izin_days_this_week
            and ds not in resmi_tatil_days_this_week
        }


        # -------------------------------------------------
        # NORMAL ÇALIŞMA DEĞİŞKENLERİ
        # -------------------------------------------------

        # Resmî tatildeki çalışma normal çalışmadan ayrı tutuluyor
        normal_work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if ds not in resmi_tatil_days_this_week
        ]

        if not normal_work_vars:

            model.Add(
                extra_off_week[(a, wk)] == 0
            )

            if (a, wk) in overtime_week:
                model.Add(
                    overtime_week[(a, wk)] == 0
                )

            continue


        # -------------------------------------------------
        # NORMAL HAFTALIK HEDEF
        # -------------------------------------------------

        normal_target = (
            NORMAL_WORK_DAYS
            - len(izin_normal_days_this_week)
            - len(resmi_tatil_days_this_week)
        )

        normal_target = max(
            0,
            min(normal_target, len(normal_work_vars))
        )


        # -------------------------------------------------
        # STANDART OFF KAPASİTESİ
        # -------------------------------------------------
        #
        # Normal tam haftada:
        # 7 gün - 5 çalışma = 2 standart OFF
        #
        # İzin günü standart OFF sayılmaz.

        izin_ve_tatil_haric_gun_sayisi = len([
            ds
            for ds in week_days_list
            if ds not in izin_days_this_week
            and ds not in resmi_tatil_days_this_week
        ])

        standart_off_sayisi = max(
            0,
            izin_ve_tatil_haric_gun_sayisi
            - normal_target
        )


        # -------------------------------------------------
        # EKSTRA HARD OFF
        # -------------------------------------------------

        hard_off_talep_sayisi = len(
            hard_talep_days_this_week
        )

        extra_off_sayisi = max(
            0,
            hard_off_talep_sayisi
            - standart_off_sayisi
        )

        model.Add(
            extra_off_week[(a, wk)]
            == extra_off_sayisi
        )


        # -------------------------------------------------
        # TELAFİ ÇALIŞMASINI KAPATAN DURUMLAR
        # -------------------------------------------------

        overtime_forced_zero_reasons = []

        if (a, wk) not in overtime_week:
            raise KeyError(
                f"overtime_week değişkeni bulunamadı: {(a, wk)}"
            )

        # Mesaiye kalamayan kişi 6. gün çalışamaz
        if a in mesaiye_kalamaz_agents:

            model.Add(
                overtime_week[(a, wk)] == 0
            )

            weekly_overtime_block_constraints += 1
            overtime_forced_zero_reasons.append(
                "mesaiye_kalamaz"
            )

        # Gerçek izin bulunan haftada telafi yapılmaz
        if len(izin_normal_days_this_week) > 0:

            model.Add(
                overtime_week[(a, wk)] == 0
            )

            weekly_overtime_block_constraints += 1
            overtime_forced_zero_reasons.append(
                "izinli_hafta"
            )


        # -------------------------------------------------
        # HAFTALIK HARD EŞİTLİK
        # -------------------------------------------------

        model.Add(
            sum(normal_work_vars)
            ==
            normal_target
            - extra_off_week[(a, wk)]
            + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1


        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "partial_week": False,
            "normal_target": normal_target,
            "izin_sayisi": len(
                izin_normal_days_this_week
            ),
            "resmi_tatil_sayisi": len(
                resmi_tatil_days_this_week
            ),
            "hard_off_talep_sayisi": (
                hard_off_talep_sayisi
            ),
            "standart_off_sayisi": (
                standart_off_sayisi
            ),
            "extra_off_sayisi": (
                extra_off_sayisi
            ),
            "overtime_forced_zero_reason": (
                " | ".join(overtime_forced_zero_reasons)
                if overtime_forced_zero_reasons
                else None
            )
        })


weekly_target_debug_df = pd.DataFrame(
    weekly_target_debug_rows
)

print("Haftalık çalışma kısıtı:", weekly_work_constraints)
print(
    "Telafi kapatma kısıtı:",
    weekly_overtime_block_constraints
)



# %% [KISIT] - AYLIK EKSTRA OFF / TELAFİ DENGESİ

for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_extra_off_vars = [
        extra_off_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in extra_off_week
    ]

    agent_overtime_vars = [
        overtime_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in overtime_week
    ]

    if agent_extra_off_vars:

        # Ay içinde verilen her ekstra OFF,
        # başka bir haftada bir telafi günüyle kapanır.
        model.Add(
            sum(agent_extra_off_vars)
            ==
            sum(agent_overtime_vars)
        )

        monthly_extra_off_balance_constraints += 1

    if agent_overtime_vars:

        model.Add(
            sum(agent_overtime_vars)
            <= MAX_OVERTIME_PER_MONTH
        )

        monthly_overtime_constraints += 1


print(
    "Aylık ekstra OFF-telafi kısıtı:",
    monthly_extra_off_balance_constraints
)

print(
    "Aylık maksimum telafi kısıtı:",
    monthly_overtime_constraints
)
