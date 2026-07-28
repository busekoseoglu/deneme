# %% [FONKSİYON] - HAFTALIK ÇALIŞMA + OFF TALEBİ + AYLIK TELAFİ

def haftalik_calisma_off_talep_kisitlarini_ekle():

    # -------------------------------------------------
    # ÇIKTI SÖZLÜKLERİ / LİSTELERİ
    # -------------------------------------------------

    off_talep_karsilandi = {}
    extra_off_week = {}

    resmi_tatil_work_week = {}

    off_talep_ceza_terms = []
    weekly_target_debug_rows = []

    weekly_work_constraints = 0
    weekly_overtime_block_constraints = 0
    partial_week_skip_constraints = 0
    monthly_overtime_constraints = 0
    monthly_extra_off_balance_constraints = 0
    off_talep_link_constraints = 0
    extra_off_link_constraints = 0
    resmi_tatil_work_week_constraints = 0

    # -------------------------------------------------
    # MESAİYE KALAMAYAN AGENT SETİ
    # -------------------------------------------------

    mesaiye_kalamaz_agents = set(
        df_tam[
            pd.to_numeric(
                df_tam["mesaiye_kalamaz_flg"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
            == 1
        ]["agent_user_code"]
        .astype(str)
        .str.strip()
    )

    # -------------------------------------------------
    # RESMİ TATİL GÜNLERİNİ PLAN_GUNLER FORMATINDA AL
    # -------------------------------------------------

    resmi_tatil_gunleri_for_weekly = set()

    if "resmi_tatil_plan_gunleri" in globals():

        resmi_tatil_gunleri_for_weekly = set(
            resmi_tatil_plan_gunleri
        )

    elif (
        "ENABLE_RESMI_TATIL_KURALI" in globals()
        and ENABLE_RESMI_TATIL_KURALI
        and "RESMI_TATIL_GUNLERI" in globals()
    ):

        resmi_tatil_key_set = {
            pd.to_datetime(d).strftime("%Y-%m-%d")
            for d in RESMI_TATIL_GUNLERI
        }

        for ds in PLAN_GUNLER:

            ds_key = pd.to_datetime(ds).strftime("%Y-%m-%d")

            if ds_key in resmi_tatil_key_set:
                resmi_tatil_gunleri_for_weekly.add(ds)

    # -------------------------------------------------
    # PARTIAL WEEK DEFAULT
    # -------------------------------------------------

    skip_partial_week = globals().get(
        "SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS",
        True
    )

    partial_weeks_local = globals().get(
        "partial_weeks",
        set()
    )

    # -------------------------------------------------
    # HAFTALIK KISITLAR
    # -------------------------------------------------

    for a_raw in AGENTS:

        a = str(a_raw).strip()

        for wk in WEEKS:

            week_days_list = week_days[wk]
            wk_str = str(wk).strip()

            # -----------------------------------------
            # 1. PARTIAL WEEK KONTROLÜ
            # -----------------------------------------

            wk_is_partial = False
            wk_partial_type = "full_week"

            if "week_boundary_df" in globals():

                wk_boundary_row = week_boundary_df[
                    week_boundary_df["week"]
                    .astype(str)
                    .str.strip()
                    == wk_str
                ]

                if len(wk_boundary_row) > 0:

                    wk_is_partial = bool(
                        wk_boundary_row["is_partial_week"].iloc[0]
                    )

                    if "partial_type" in wk_boundary_row.columns:
                        wk_partial_type = (
                            wk_boundary_row["partial_type"].iloc[0]
                        )

            else:

                wk_is_partial = wk in partial_weeks_local

                if wk_is_partial:
                    wk_partial_type = "partial_week"

            if skip_partial_week and wk_is_partial:

                if (a, wk) in overtime_week:

                    model.Add(
                        overtime_week[(a, wk)] == 0
                    )

                    partial_week_skip_constraints += 1

                weekly_target_debug_rows.append({
                    "agent_user_code": a,
                    "week": wk,
                    "normal_target": None,
                    "normal_work_var_count": None,
                    "izin_normal_count": None,
                    "resmi_tatil_count": None,
                    "off_talep_count": None,
                    "karsilanan_off_talep": None,
                    "extra_off": None,
                    "mesaiye_kalamaz": (
                        a in mesaiye_kalamaz_agents
                    ),
                    "partial_week": True,
                    "partial_type": wk_partial_type,
                    "hard_weekly_target": False,
                    "overtime_forced_zero_reason": "partial_week"
                })

                continue

            # -----------------------------------------
            # 2. OVERTIME_WEEK VAR MI?
            # -----------------------------------------

            if (a, wk) not in overtime_week:
                continue

            # -----------------------------------------
            # 3. BU HAFTANIN RESMİ TATİL GÜNLERİ
            # -----------------------------------------

            resmi_tatil_days_this_week = {
                ds
                for ds in week_days_list
                if ds in resmi_tatil_gunleri_for_weekly
            }

            # -----------------------------------------
            # 4. BU HAFTANIN İZİN GÜNLERİ
            # -----------------------------------------

            izin_days_this_week = {
                ds
                for ds in week_days_list
                if agent_izinli_mi(a, ds)
            }

            # Resmî tatil zaten ayrıca düşüldüğü için
            # izin hesabında tekrar sayılmasın.
            izin_normal_days_this_week = (
                izin_days_this_week
                - resmi_tatil_days_this_week
            )

            # -----------------------------------------
            # 5. NORMAL WORK DEĞİŞKENLERİ
            # -----------------------------------------

            normal_work_vars = [
                work[(a, ds)]
                for ds in week_days_list
                if (a, ds) in work
                and ds not in resmi_tatil_days_this_week
            ]

            if not normal_work_vars:

                model.Add(
                    overtime_week[(a, wk)] == 0
                )

                weekly_target_debug_rows.append({
                    "agent_user_code": a,
                    "week": wk,
                    "normal_target": None,
                    "normal_work_var_count": 0,
                    "izin_normal_count": len(
                        izin_normal_days_this_week
                    ),
                    "resmi_tatil_count": len(
                        resmi_tatil_days_this_week
                    ),
                    "off_talep_count": 0,
                    "karsilanan_off_talep": 0,
                    "extra_off": 0,
                    "mesaiye_kalamaz": (
                        a in mesaiye_kalamaz_agents
                    ),
                    "partial_week": False,
                    "partial_type": wk_partial_type,
                    "hard_weekly_target": False,
                    "overtime_forced_zero_reason": (
                        "normal_work_var_yok"
                    )
                })

                continue

            # -----------------------------------------
            # 6. RESMİ TATİL ÇALIŞMASINI AYRI TAKİP ET
            # -----------------------------------------

            resmi_tatil_work_vars = [
                work[(a, ds)]
                for ds in week_days_list
                if (a, ds) in work
                and ds in resmi_tatil_days_this_week
            ]

            if resmi_tatil_work_vars:

                resmi_tatil_work_week[(a, wk)] = (
                    model.NewIntVar(
                        0,
                        len(resmi_tatil_work_vars),
                        f"resmi_tatil_work_week_{a}_{wk}"
                    )
                )

                model.Add(
                    resmi_tatil_work_week[(a, wk)]
                    ==
                    sum(resmi_tatil_work_vars)
                )

                resmi_tatil_work_week_constraints += 1

            # -----------------------------------------
            # 7. NORMAL HAFTALIK HEDEF
            # -----------------------------------------

            normal_target = NORMAL_WORK_DAYS

            normal_target -= len(
                resmi_tatil_days_this_week
            )

            normal_target -= len(
                izin_normal_days_this_week
            )

            normal_target = max(
                0,
                normal_target
            )

            normal_target = min(
                normal_target,
                len(normal_work_vars)
            )

            # -----------------------------------------
            # 8. BU HAFTANIN OFF TALEPLERİ
            # -----------------------------------------
            # İzin veya resmî tatil günündeki talep
            # ayrıca OFF talebi olarak sayılmaz.

            off_talep_days_this_week = [
                ds
                for ds in week_days_list
                if off_talep_map.get((a, ds), 0) == 1
                and ds not in resmi_tatil_days_this_week
                and ds not in izin_days_this_week
                and (a, ds) in work
            ]

            karsilanan_talep_vars = []

            for ds in off_talep_days_this_week:

                key = (a, ds)

                off_talep_karsilandi[key] = (
                    model.NewBoolVar(
                        f"off_talep_karsilandi_{a}_{ds}"
                    )
                )

                # work=0 ise talep karşılandı
                # work=1 ise talep karşılanmadı
                model.Add(
                    off_talep_karsilandi[key]
                    + work[(a, ds)]
                    == 1
                )

                off_talep_link_constraints += 1

                karsilanan_talep_vars.append(
                    off_talep_karsilandi[key]
                )

                # 1 - karşılandı değişkeni
                # objective içinde cezalandırılacak.
                off_talep_ceza_terms.append(
                    1 - off_talep_karsilandi[key]
                )

            # -----------------------------------------
            # 9. STANDART OFF SAYISI
            # -----------------------------------------
            # Tam haftada normal olarak 2 OFF vardır.
            # İzin günleri bu sayıyı artırmamalıdır.
            #
            # Örnek:
            # 1 izin + 2 OFF = normal düzen
            # 1 izin + 3 OFF = 1 ekstra OFF

            izin_haric_normal_target = (
                NORMAL_WORK_DAYS
                - len(resmi_tatil_days_this_week)
            )

            izin_haric_normal_target = max(
                0,
                izin_haric_normal_target
            )

            izin_haric_normal_target = min(
                izin_haric_normal_target,
                len(normal_work_vars)
            )

            standart_off_sayisi = max(
                0,
                len(normal_work_vars)
                - izin_haric_normal_target
            )

            # -----------------------------------------
            # 10. EKSTRA OFF SAYISI
            # -----------------------------------------
            # extra_off =
            # max(karşılanan talep - standart OFF, 0)

            extra_off_week[(a, wk)] = model.NewIntVar(
                0,
                len(karsilanan_talep_vars),
                f"extra_off_week_{a}_{wk}"
            )

            if karsilanan_talep_vars:

                talep_fazlasi_alt_sinir = (
                    -standart_off_sayisi
                )

                talep_fazlasi_ust_sinir = (
                    len(karsilanan_talep_vars)
                )

                talep_fazlasi = model.NewIntVar(
                    talep_fazlasi_alt_sinir,
                    talep_fazlasi_ust_sinir,
                    f"off_talep_fazlasi_{a}_{wk}"
                )

                model.Add(
                    talep_fazlasi
                    ==
                    sum(karsilanan_talep_vars)
                    - standart_off_sayisi
                )

                model.AddMaxEquality(
                    extra_off_week[(a, wk)],
                    [
                        talep_fazlasi,
                        0
                    ]
                )

                extra_off_link_constraints += 2

            else:

                model.Add(
                    extra_off_week[(a, wk)] == 0
                )

                extra_off_link_constraints += 1

            # -----------------------------------------
            # 11. OVERTIME KAPATMA KURALLARI
            # -----------------------------------------

            overtime_forced_zero_reasons = []

            # Mesaiye kalamayan agent
            if a in mesaiye_kalamaz_agents:

                model.Add(
                    overtime_week[(a, wk)] == 0
                )

                weekly_overtime_block_constraints += 1
                overtime_forced_zero_reasons.append(
                    "mesaiye_kalamaz"
                )

            # İzinli haftada telafi çalışması verilmez.
            # Telafi sonraki uygun haftaya kayar.
            if len(izin_normal_days_this_week) > 0:

                model.Add(
                    overtime_week[(a, wk)] == 0
                )

                weekly_overtime_block_constraints += 1
                overtime_forced_zero_reasons.append(
                    "izinli_hafta"
                )

            # -----------------------------------------
            # 12. HAFTALIK ÇALIŞMA EŞİTLİĞİ
            # -----------------------------------------
            #
            # OFF talebi yoksa:
            # normal çalışma = normal_target
            #
            # 3. talep ekstra OFF olduysa:
            # normal çalışma = normal_target - 1
            #
            # Telafi haftasında:
            # normal çalışma = normal_target + 1

            model.Add(
                sum(normal_work_vars)
                ==
                normal_target
                - extra_off_week[(a, wk)]
                + overtime_week[(a, wk)]
            )

            weekly_work_constraints += 1

            # -----------------------------------------
            # 13. DEBUG
            # -----------------------------------------

            weekly_target_debug_rows.append({
                "agent_user_code": a,
                "week": wk,
                "normal_target": normal_target,
                "normal_work_var_count": len(
                    normal_work_vars
                ),
                "izin_normal_count": len(
                    izin_normal_days_this_week
                ),
                "resmi_tatil_count": len(
                    resmi_tatil_days_this_week
                ),
                "off_talep_count": len(
                    off_talep_days_this_week
                ),
                "standart_off_sayisi": (
                    standart_off_sayisi
                ),
                "karsilanan_off_talep_var_count": len(
                    karsilanan_talep_vars
                ),
                "mesaiye_kalamaz": (
                    a in mesaiye_kalamaz_agents
                ),
                "partial_week": False,
                "partial_type": wk_partial_type,
                "hard_weekly_target": True,
                "overtime_forced_zero_reason": (
                    " | ".join(
                        overtime_forced_zero_reasons
                    )
                    if overtime_forced_zero_reasons
                    else None
                )
            })

    # -------------------------------------------------
    # AYLIK EKSTRA OFF – TELAFİ EŞİTLİĞİ
    # -------------------------------------------------
    #
    # Bir ayda verilen toplam ekstra OFF sayısı,
    # başka haftalarda verilen toplam telafi günüyle
    # birebir kapanmalıdır.

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

            model.Add(
                sum(agent_extra_off_vars)
                ==
                sum(agent_overtime_vars)
            )

            monthly_extra_off_balance_constraints += 1

        elif agent_overtime_vars:

            # Ekstra OFF yoksa gereksiz telafi verilmesin.
            model.Add(
                sum(agent_overtime_vars) == 0
            )

            monthly_extra_off_balance_constraints += 1

    # -------------------------------------------------
    # AYLIK MAKSİMUM NORMAL MESAİ
    # -------------------------------------------------

    for a_raw in AGENTS:

        a = str(a_raw).strip()

        agent_overtime_vars = [
            overtime_week[(a, wk)]
            for wk in WEEKS
            if (a, wk) in overtime_week
        ]

        if agent_overtime_vars:

            model.Add(
                sum(agent_overtime_vars)
                <= MAX_OVERTIME_PER_MONTH
            )

            monthly_overtime_constraints += 1

    # -------------------------------------------------
    # DEBUG DATAFRAME
    # -------------------------------------------------

    weekly_target_debug_df = pd.DataFrame(
        weekly_target_debug_rows
    )

    print(
        "Haftalık çalışma kısıtı:",
        weekly_work_constraints
    )

    print(
        "Overtime kapatma kısıtı:",
        weekly_overtime_block_constraints
    )

    print(
        "Partial week skip kısıtı:",
        partial_week_skip_constraints
    )

    print(
        "OFF talebi bağlantı kısıtı:",
        off_talep_link_constraints
    )

    print(
        "Ekstra OFF bağlantı kısıtı:",
        extra_off_link_constraints
    )

    print(
        "Aylık ekstra OFF-telafi kısıtı:",
        monthly_extra_off_balance_constraints
    )

    print(
        "Aylık maksimum mesai kısıtı:",
        monthly_overtime_constraints
    )

    return {
        "off_talep_karsilandi": off_talep_karsilandi,
        "extra_off_week": extra_off_week,
        "off_talep_ceza_terms": off_talep_ceza_terms,
        "resmi_tatil_work_week": resmi_tatil_work_week,
        "weekly_target_debug_df": weekly_target_debug_df,
        "mesaiye_kalamaz_agents": mesaiye_kalamaz_agents
    }



haftalik_off_sonuclari = (
    haftalik_calisma_off_talep_kisitlarini_ekle()
)

off_talep_karsilandi = (
    haftalik_off_sonuclari["off_talep_karsilandi"]
)

extra_off_week = (
    haftalik_off_sonuclari["extra_off_week"]
)

off_talep_ceza_terms = (
    haftalik_off_sonuclari["off_talep_ceza_terms"]
)

resmi_tatil_work_week = (
    haftalik_off_sonuclari["resmi_tatil_work_week"]
)

weekly_target_debug_df = (
    haftalik_off_sonuclari["weekly_target_debug_df"]
)


"OFF_TALEP_KARSILANMAMA_W": 100000,


OFF_TALEP_KARSILANMAMA_W = CONFIG[
    "OFF_TALEP_KARSILANMAMA_W"
]


objective_terms.extend(
    OFF_TALEP_KARSILANMAMA_W * term
    for term in off_talep_ceza_terms
)
