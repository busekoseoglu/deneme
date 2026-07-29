# %% [KARAR DEĞİŞKENİ] - NORMAL ÇALIŞMA TELAFİ HAFTASI

# telafi_week[(agent, hafta)] = 1:
# Agent bu hafta standart hedefinden 1 gün fazla NORMAL çalışır.
#
# Bu gün NORMAL_MESAI değildir.
# Başka bir haftada 2 standart OFF'u aşan OFF talebinin telafisidir.
#
# Gerçek mesai sistemi overtime_week üzerinden ayrıca devam eder.

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


# %% [KISIT] - HAFTALIK ÇALIŞMA + HARD OFF + TELAFİ + MESAİ

# Temel haftalık yapı:
#
# Normal hafta:
#     5 çalışma
#
# Gerçek mesai haftası:
#     5 + 1 NORMAL_MESAI = 6 çalışma
#
# OFF telafi haftası:
#     5 + 1 normal çalışma telafisi = 6 çalışma
#
# Aynı haftada:
#     telafi_week + overtime_week <= 1
#
# Böylece bir kişinin haftalık hedefi hiçbir zaman
# telafi ve mesai nedeniyle 7 güne çıkmaz.
#
# İlk iki hard OFF talebi standart OFF hakkıdır.
# Yalnızca 2'yi aşan hard OFF talepleri extra_off_week oluşturur.
#
# İzin günleri ve resmî tatiller extra_off_week hesabına girmez.

extra_off_week = {}
haftalik_off_telafi_debug_rows = []


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

    # Yalnızca gerçek OFF talepleri.
    # İzin günleri burada bulunmaz.
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

        # İzin ve resmî tatil aynı güne denk gelirse
        # hedef yalnızca bir kez düşürülür.
        hedef_dusuren_dates = (
            week_izin_dates
            | week_resmi_tatil_dates
        )

        normal_target = max(
            NORMAL_WORK_DAYS
            - len(hedef_dusuren_dates),
            0
        )

        # Resmî tatil veya izin gününe denk gelen OFF talebi
        # ekstra OFF hesabına alınmaz.
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

        # Telafi ve gerçek mesai aynı hafta kullanılamaz.
        model.Add(
            telafi_week[(a, wk)]
            + overtime_week[(a, wk)]
            <= 1
        )

        # --------------------------------------------------
        # PARTIAL HAFTA
        # --------------------------------------------------

        if (
            SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS
            and wk_key in partial_week_set
        ):

            # Ayın sadece bir kısmı görüldüğü için bu hafta
            # standart 5 günlük hedef hesabına sokulmaz.
            model.Add(
                extra_off_week[(a, wk)] == 0
            )

            model.Add(
                telafi_week[(a, wk)] == 0
            )

            model.Add(
                overtime_week[(a, wk)] == 0
            )

            haftalik_off_telafi_debug_rows.append({
                "agent_user_code": a,
                "week": wk_key,
                "normal_target": normal_target,
                "hard_off_talep_count": hard_off_talep_count,
                "extra_off_count": 0,
                "telafi_uygun": False,
                "mesai_uygun": False,
                "neden": "partial_week"
            })

            continue

        # Full week için ekstra OFF sayısını sabitle.
        model.Add(
            extra_off_week[(a, wk)]
            == extra_off_count
        )

        # Resmî tatil günleri haftalık normal çalışma
        # toplamının içinde sayılmaz.
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
        # GERÇEK MESAİ UYGUNLUĞU
        # --------------------------------------------------

        # Mesaiye kalamayan agent gerçek mesai alamaz.
        if a in mesaiye_kalamaz_agents:

            model.Add(
                overtime_week[(a, wk)] == 0
            )

        # İzin bulunan haftada gerçek mesai verilmez.
        if len(week_izin_dates) > 0:

            model.Add(
                overtime_week[(a, wk)] == 0
            )

        # Ekstra OFF alınan hafta aynı zamanda
        # gerçek mesai veya telafi haftası olamaz.
        if extra_off_count > 0:

            model.Add(
                telafi_week[(a, wk)] == 0
            )

            model.Add(
                overtime_week[(a, wk)] == 0
            )

        # --------------------------------------------------
        # NORMAL ÇALIŞMA TELAFİSİ UYGUNLUĞU
        # --------------------------------------------------

        # Telafi haftası toplam 6 çalışma günü olmalıdır.
        # İzin veya resmî tatil nedeniyle normal hedef 5'in
        # altına düşmüşse bu hafta telafi haftası olamaz.
        if normal_target != NORMAL_WORK_DAYS:

            model.Add(
                telafi_week[(a, wk)] == 0
            )

        # Agentın gerçekten çalışabileceği normal gün sayısı.
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

        # Telafi için en az 6 kullanılabilir gün gerekir.
        if (
            kullanilabilir_normal_gun_sayisi
            < NORMAL_WORK_DAYS + 1
        ):

            model.Add(
                telafi_week[(a, wk)] == 0
            )

        # --------------------------------------------------
        # HAFTALIK ÇALIŞMA EŞİTLİĞİ
        # --------------------------------------------------
        #
        # Normal hafta:
        #     target
        #
        # Ekstra OFF haftası:
        #     target - extra_off
        #
        # Telafi haftası:
        #     target + telafi_week
        #
        # Mesai haftası:
        #     target + overtime_week

        model.Add(
            sum(normal_work_vars)
            ==
            normal_target
            - extra_off_week[(a, wk)]
            + telafi_week[(a, wk)]
            + overtime_week[(a, wk)]
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
                and normal_target == NORMAL_WORK_DAYS
                and kullanilabilir_normal_gun_sayisi
                >= NORMAL_WORK_DAYS + 1
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
    "Mesaiye kalamayan agent sayısı:",
    len(mesaiye_kalamaz_agents)
)

# %% [KISIT] - AYLIK EKSTRA OFF / TELAFİ VE MESAİ SINIRI

# OFF telafisi:
#     Aylık toplam ekstra OFF
#     =
#     aylık toplam normal çalışma telafisi
#
# Gerçek mesai:
#     overtime_week üzerinden ayrıca devam eder.
#
# Telafi gerçek mesai sayılmaz.
# Gerçek mesai aylık mevcut sınırına tabidir.

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

    # Gerçek mesai için mevcut aylık üst sınır korunur.
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
