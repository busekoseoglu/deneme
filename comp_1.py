# %% [KISIT / DEBUG] - HAFTALIK ÇALIŞMA + HARD OFF + TELAFİ + MESAİ

# Bu geçici debug sürümü haftalık kısıtları üç gruba ayırır:
#
# 1) EXTRA_OFF
#    Haftadaki 2'yi aşan hard OFF talebi hesabı
#
# 2) UYGUNLUK
#    Telafi ve mesainin aynı hafta olmaması,
#    izinli/partial/uygun olmayan haftalarda kapatılması
#
# 3) ESITLIK
#    Haftalık toplam çalışma eşitliği
#
# Model infeasible olduğunda hangi agent-hafta ve hangi grup
# çakışmaya giriyor göreceğiz.

extra_off_week = {}

haftalik_off_telafi_debug_rows = []

haftalik_assumption_map = {}
haftalik_assumption_index_map = {}


# --------------------------------------------------
# PARTIAL HAFTALAR
# --------------------------------------------------

partial_week_set = {
    str(wk).strip()
    for wk in partial_weeks
}


# --------------------------------------------------
# RESMÎ TATİL TARİHLERİ
# --------------------------------------------------

resmi_tatil_date_set = {
    pd.to_datetime(ds).date()
    for ds in resmi_tatil_plan_gunleri
}


# --------------------------------------------------
# MESAİYE KALAMAYAN AGENTLAR
# --------------------------------------------------

mesaiye_kalamaz_flag = (
    pd.to_numeric(
        df_tam["mesaiye_kalamaz_flg"],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)

mesaiye_kalamaz_agents = set(
    df_tam.loc[
        mesaiye_kalamaz_flag == 1,
        "agent_user_code"
    ]
    .astype(str)
    .str.strip()
)


# --------------------------------------------------
# ASSUMPTION OLUŞTURMA FONKSİYONU
# --------------------------------------------------

def assumption_olustur(agent_code, week_key, grup):

    assumption_var = model.NewBoolVar(
        f"assumption_{grup}_{agent_code}_{week_key}"
    )

    model.AddAssumption(
        assumption_var
    )

    key = (
        str(agent_code).strip(),
        str(week_key).strip(),
        str(grup).strip()
    )

    haftalik_assumption_map[key] = assumption_var

    haftalik_assumption_index_map[
        assumption_var.Index()
    ] = {
        "agent_user_code": str(agent_code).strip(),
        "week": str(week_key).strip(),
        "grup": str(grup).strip()
    }

    return assumption_var


# --------------------------------------------------
# HAFTALIK KISITLAR
# --------------------------------------------------

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

    # Yalnızca gerçek hard OFF talepleri.
    # İzin günleri bu sete girmez.
    agent_hard_off_talep_dates = (
        agent_off_t2_dates
        | agent_hard_off_t_dates
    )

    for wk in WEEKS:

        wk_key = str(wk).strip()

        week_ds = week_days.get(
            wk,
            []
        )

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

        hedef_dusuren_dates = (
            week_izin_dates
            | week_resmi_tatil_dates
        )

        normal_target = max(
            NORMAL_WORK_DAYS
            - len(hedef_dusuren_dates),
            0
        )

        # İzin veya resmî tatille çakışan OFF talebi,
        # ekstra OFF hesabına tekrar alınmaz.
        week_hard_off_talep_dates = (
            agent_hard_off_talep_dates
            & week_dates
        ) - hedef_dusuren_dates

        hard_off_talep_count = len(
            week_hard_off_talep_dates
        )

        extra_off_count = max(
            hard_off_talep_count - 2,
            0
        )

        extra_off_week[(a, wk)] = model.NewIntVar(
            0,
            len(week_ds),
            f"extra_off_week_{a}_{wk}"
        )

        # Her agent-hafta için üç ayrı debug assumption
        assumption_extra = assumption_olustur(
            a,
            wk_key,
            "EXTRA_OFF"
        )

        assumption_uygunluk = assumption_olustur(
            a,
            wk_key,
            "UYGUNLUK"
        )

        assumption_esitlik = assumption_olustur(
            a,
            wk_key,
            "ESITLIK"
        )

        partial_week_mi = (
            SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS
            and wk_key in partial_week_set
        )

        # --------------------------------------------------
        # PARTIAL HAFTA
        # --------------------------------------------------

        if partial_week_mi:

            model.Add(
                extra_off_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_extra
            )

            model.Add(
                telafi_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

            model.Add(
                overtime_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

            haftalik_off_telafi_debug_rows.append({
                "agent_user_code": a,
                "week": wk_key,
                "partial_week": True,
                "normal_target": normal_target,
                "izin_gun_sayisi": len(
                    week_izin_dates
                ),
                "resmi_tatil_sayisi": len(
                    week_resmi_tatil_dates
                ),
                "hard_off_talep_count": (
                    hard_off_talep_count
                ),
                "extra_off_count": 0,
                "kullanilabilir_normal_gun": 0,
                "mesaiye_kalamaz": (
                    a in mesaiye_kalamaz_agents
                ),
                "neden": "partial_week"
            })

            continue

        # --------------------------------------------------
        # EXTRA OFF HESABI
        # --------------------------------------------------

        model.Add(
            extra_off_week[(a, wk)]
            == extra_off_count
        ).OnlyEnforceIf(
            assumption_extra
        )

        # --------------------------------------------------
        # NORMAL ÇALIŞMA TOPLAMI
        # --------------------------------------------------

        normal_work_vars = [
            work[(a, ds)]
            for ds in week_ds
            if (
                (a, ds) in work
                and pd.to_datetime(ds).date()
                not in resmi_tatil_date_set
            )
        ]

        # --------------------------------------------------
        # TELAFİ / MESAİ UYGUNLUK KISITLARI
        # --------------------------------------------------

        # Aynı haftada hem telafi hem gerçek mesai olamaz.
        model.Add(
            telafi_week[(a, wk)]
            + overtime_week[(a, wk)]
            <= 1
        ).OnlyEnforceIf(
            assumption_uygunluk
        )

        # Mesaiye kalamayan agent gerçek mesai alamaz.
        if a in mesaiye_kalamaz_agents:

            model.Add(
                overtime_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

        # İzin bulunan haftada gerçek mesai verilmez.
        if len(week_izin_dates) > 0:

            model.Add(
                overtime_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

        # Ekstra OFF alınan hafta aynı zamanda
        # telafi veya gerçek mesai haftası olamaz.
        if extra_off_count > 0:

            model.Add(
                telafi_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

            model.Add(
                overtime_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

        # Telafi haftası 6 çalışma günü olmalı.
        # İzin/resmî tatil nedeniyle hedef düşmüş haftada
        # başka haftanın OFF telafisi yapılmaz.
        if normal_target != NORMAL_WORK_DAYS:

            model.Add(
                telafi_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

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

        if (
            kullanilabilir_normal_gun_sayisi
            < NORMAL_WORK_DAYS + 1
        ):

            model.Add(
                telafi_week[(a, wk)] == 0
            ).OnlyEnforceIf(
                assumption_uygunluk
            )

        # --------------------------------------------------
        # HAFTALIK ÇALIŞMA EŞİTLİĞİ
        # --------------------------------------------------

        model.Add(
            sum(normal_work_vars)
            ==
            normal_target
            - extra_off_week[(a, wk)]
            + telafi_week[(a, wk)]
            + overtime_week[(a, wk)]
        ).OnlyEnforceIf(
            assumption_esitlik
        )

        haftalik_off_telafi_debug_rows.append({
            "agent_user_code": a,
            "week": wk_key,
            "partial_week": False,
            "normal_target": normal_target,
            "izin_gun_sayisi": len(
                week_izin_dates
            ),
            "resmi_tatil_sayisi": len(
                week_resmi_tatil_dates
            ),
            "hard_off_talep_count": (
                hard_off_talep_count
            ),
            "extra_off_count": extra_off_count,
            "kullanilabilir_normal_gun": (
                kullanilabilir_normal_gun_sayisi
            ),
            "mesaiye_kalamaz": (
                a in mesaiye_kalamaz_agents
            ),
            "neden": ""
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

print(
    "Haftalık debug assumption sayısı:",
    len(haftalik_assumption_index_map)
)


# %% [KISIT] - AYLIK EKSTRA OFF / TELAFİ VE MESAİ SINIRI

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

    agent_overtime_vars = [
        overtime_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in overtime_week
    ]

    # Ekstra OFF günlerinin tamamı ay içinde
    # normal çalışma ile kesin telafi edilir.
    model.Add(
        sum(agent_extra_off_vars)
        ==
        sum(agent_telafi_vars)
    )

    # Gerçek mesai sistemi ayrı devam eder.
    model.Add(
        sum(agent_overtime_vars)
        <= MAX_OVERTIME_PER_MONTH
    )

    aylik_telafi_debug_rows.append({
        "agent_user_code": a,
        "extra_off_week_var_sayisi": len(
            agent_extra_off_vars
        ),
        "telafi_week_var_sayisi": len(
            agent_telafi_vars
        ),
        "overtime_week_var_sayisi": len(
            agent_overtime_vars
        )
    })


aylik_telafi_debug_df = pd.DataFrame(
    aylik_telafi_debug_rows
)

print(
    "Aylık ekstra OFF / normal çalışma telafi eşitliği eklendi."
)

print(
    "Gerçek mesai aylık üst sınırı:",
    MAX_OVERTIME_PER_MONTH
)

print(
    "Agent sayısı:",
    len(AGENTS)
)


# %% [SOLVE / DEBUG] - HAFTALIK ÇAKIŞMA TESPİTİ

status = solver.Solve(model)

print(
    "Solver status:",
    solver.StatusName(status)
)

if status == cp_model.INFEASIBLE:

    core_literals = (
        solver.SufficientAssumptionsForInfeasibility()
    )

    core_rows = []

    for literal_raw in core_literals:

        literal = int(literal_raw)

        if literal >= 0:
            variable_index = literal
        else:
            variable_index = -literal - 1

        if variable_index in haftalik_assumption_index_map:

            core_rows.append(
                haftalik_assumption_index_map[
                    variable_index
                ]
            )

    haftalik_infeasible_core_df = pd.DataFrame(
        core_rows
    )

    if not haftalik_infeasible_core_df.empty:

        haftalik_infeasible_core_df = (
            haftalik_infeasible_core_df
            .drop_duplicates()
            .sort_values(
                [
                    "grup",
                    "agent_user_code",
                    "week"
                ]
            )
            .reset_index(drop=True)
        )

    print(
        "Infeasible core assumption sayısı:",
        len(core_literals)
    )

    print(
        "Haftalık bloktan bulunan kayıt:",
        len(haftalik_infeasible_core_df)
    )

    display(
        haftalik_infeasible_core_df
    )

    if not haftalik_infeasible_core_df.empty:

        sorunlu_agent_week = (
            haftalik_infeasible_core_df[
                [
                    "agent_user_code",
                    "week"
                ]
            ]
            .drop_duplicates()
        )

        haftalik_infeasible_detay_df = (
            haftalik_off_telafi_debug_df
            .merge(
                sorunlu_agent_week,
                on=[
                    "agent_user_code",
                    "week"
                ],
                how="inner"
            )
            .sort_values(
                [
                    "agent_user_code",
                    "week"
                ]
            )
            .reset_index(drop=True)
        )

        display(
            haftalik_infeasible_detay_df
        )

    else:

        print(
            "Infeasible core haftalık yeni bloktan gelmiyor."
        )

        print(
            "Sorun telafi/OFF hücreleri dışındaki "
            "başka bir hard kısıtta."
        )

elif status in (
    cp_model.FEASIBLE,
    cp_model.OPTIMAL
):

    print(
        "Model feasible."
    )

    print(
        "Yeni haftalık OFF/telafi/mesai bloğu "
        "infeasible oluşturmuyor."
    )
