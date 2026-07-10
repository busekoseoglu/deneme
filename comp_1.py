# %% [KISIT] - HAFTALIK ÇALIŞMA + NORMAL MESAİ - HARD TARGET
# Mantık:
# - Agent haftalık hedefin altında da kalamaz, üstüne de çıkamaz.
# - weekly_under / weekly_over artık yok.
# - Haftalık çalışma hedefi hard eşitlik olarak kurulur.
#
# Normal haftalık hedef:
# NORMAL_WORK_DAYS
# - resmi tatil gün sayısı
# - izin gün sayısı
#
# Resmi tatil günleri normal haftalık hedefe dahil değildir.
# Resmi tatilde çalışma ayrıca takip edilir.
#
# Partial week'lerde haftalık hedef kurulmaz.
# Çünkü model haftanın tamamını görmez.
#
# İzinli haftada normal mesai verilmez.
# Çünkü izin aldıysa hedef düşer ve bu hedef tekrar overtime ile yukarı çekilmemelidir.

# --------------------------------------------------
# 0) MESAIYE KALAMAZ AGENT SETİ
# --------------------------------------------------

mesaiye_kalamaz_agents = set(
    df_tam[
        pd.to_numeric(
            df_tam["mesaiye_kalamaz_flg"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int) == 1
    ]["agent_user_code"]
    .astype(str)
    .str.strip()
)

# --------------------------------------------------
# 1) RESMİ TATİL GÜNLERİNİ PLAN_GUNLER FORMATINDA AL
# --------------------------------------------------

resmi_tatil_gunleri_for_weekly = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_gunleri_for_weekly = set(resmi_tatil_plan_gunleri)

else:
    if "ENABLE_RESMI_TATIL_KURALI" in globals() and ENABLE_RESMI_TATIL_KURALI:
        if "RESMI_TATIL_GUNLERI" in globals():

            resmi_tatil_key_set = set(
                pd.to_datetime(d).strftime("%Y-%m-%d")
                for d in RESMI_TATIL_GUNLERI
            )

            for ds in PLAN_GUNLER:
                ds_key = pd.to_datetime(ds).strftime("%Y-%m-%d")

                if ds_key in resmi_tatil_key_set:
                    resmi_tatil_gunleri_for_weekly.add(ds)

print(
    "Normal haftalık çalışmadan ayrı tutulacak resmi tatil günleri:",
    resmi_tatil_gunleri_for_weekly
)

# --------------------------------------------------
# 2) PARTIAL WEEK DEFAULT KONTROLLERİ
# --------------------------------------------------

if "SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS" not in globals():
    SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS = True

if "partial_weeks" not in globals():
    partial_weeks = set()

if "partial_end_weeks" not in globals():
    partial_end_weeks = set()

# --------------------------------------------------
# 3) KISIT SAYAÇLARI VE SÖZLÜKLER
# --------------------------------------------------

weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
leave_week_overtime_block_constraints = 0
monthly_overtime_constraints = 0
partial_week_skip_constraints = 0
resmi_tatil_work_week_constraints = 0

# DİKKAT:
# weekly_under / weekly_over artık kullanılmıyor.
# Ama eski objective / summary hücreleri patlamasın diye boş dict bırakıyoruz.
weekly_under = {}
weekly_over = {}

# Resmi tatil çalışmasını ayrı takip etmek için kalıyor.
resmi_tatil_work_week = {}

weekly_target_debug_rows = []

# --------------------------------------------------
# 4) HAFTALIK NORMAL ÇALIŞMA HEDEFİ - HARD
# --------------------------------------------------

for a in AGENTS:

    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]
        wk_str = str(wk).strip()

        # --------------------------------------------------
        # 4.1) PARTIAL WEEK KONTROLÜ
        # --------------------------------------------------
        # Partial week'lerde haftalık hedef kurulmaz.
        # Çünkü model haftanın tamamını görmez.
        #
        # Örnek:
        # Haziran 2026 W27 sadece 29-30 Haziran'dır.
        # Bu hafta Temmuz ile tamamlanacağı için Haziran modelinde
        # weekly target kurulmaz.
        #
        # Bu haftada normal mesai de kapatılır:
        # overtime_week = 0

        if "week_boundary_df" in globals():
            wk_boundary_row = week_boundary_df[
                week_boundary_df["week"].astype(str).str.strip() == wk_str
            ]

            wk_is_partial = (
                len(wk_boundary_row) > 0
                and bool(wk_boundary_row["is_partial_week"].iloc[0])
            )

            wk_partial_type = (
                wk_boundary_row["partial_type"].iloc[0]
                if len(wk_boundary_row) > 0
                else None
            )

        else:
            wk_is_partial = wk in partial_weeks
            wk_partial_type = "partial_week" if wk_is_partial else "full_week"

        if SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS and wk_is_partial:

            if (a, wk) in overtime_week:
                model.Add(overtime_week[(a, wk)] == 0)
                partial_week_skip_constraints += 1

            weekly_target_debug_rows.append({
                "agent_user_code": a,
                "week": wk,
                "normal_target": None,
                "normal_work_var_count": None,
                "resmi_tatil_work_var_count": None,
                "izin_normal_count": None,
                "resmi_tatil_count": None,
                "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
                "partial_week": True,
                "partial_type": wk_partial_type,
                "partial_week_reason": "weekly_target_skip",
                "hard_weekly_target": False,
                "overtime_forced_zero_reason": "partial_week"
            })

            continue

        # --------------------------------------------------
        # 4.2) OVERTIME WEEK DEĞİŞKENİ VAR MI?
        # --------------------------------------------------

        if (a, wk) not in overtime_week:
            continue

        # --------------------------------------------------
        # 4.3) BU HAFTANIN RESMİ TATİL GÜNLERİ
        # --------------------------------------------------

        resmi_tatil_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in resmi_tatil_gunleri_for_weekly
        )

        # --------------------------------------------------
        # 4.4) BU HAFTANIN İZİN GÜNLERİ
        # --------------------------------------------------
        # Burada hafta sonu izni de sayılır.
        #
        # Örnek:
        # Agent Cumartesi-Pazar izin aldıysa:
        # izin_normal_count = 2
        # normal_target = 5 - 2 = 3
        #
        # Böylece bu agent hafta içinde 5 gün çalışamaz.
        # Tam 3 normal gün çalışmak zorunda kalır.

        izin_days_this_week = set(
            ds
            for ds in week_days_list
            if agent_izinli_mi(a, ds)
        )

        # Resmi tatil günleri normal hedeften ayrıca düşüldüğü için,
        # resmi tatilde izin varsa iki kere düşmemesi adına çıkarıyoruz.

        izin_normal_days_this_week = (
            izin_days_this_week
            - resmi_tatil_days_this_week
        )

        # --------------------------------------------------
        # 4.5) NORMAL GÜNLERDEKİ WORK DEĞİŞKENLERİ
        # --------------------------------------------------
        # Resmi tatil günleri burada yok.
        # Yani resmi tatil çalışması haftalık normal çalışma hedefine girmez.

        normal_work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
            and ds not in resmi_tatil_days_this_week
        ]

        if not normal_work_vars:

            weekly_target_debug_rows.append({
                "agent_user_code": a,
                "week": wk,
                "normal_target": None,
                "normal_work_var_count": 0,
                "resmi_tatil_work_var_count": None,
                "izin_normal_count": len(izin_normal_days_this_week),
                "resmi_tatil_count": len(resmi_tatil_days_this_week),
                "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
                "partial_week": False,
                "partial_type": wk_partial_type,
                "partial_week_reason": "normal_work_var_yok",
                "hard_weekly_target": False,
                "overtime_forced_zero_reason": None
            })

            continue

        # --------------------------------------------------
        # 4.6) RESMİ TATİL WORK DEĞİŞKENLERİ
        # --------------------------------------------------
        # Resmi tatilde çalışılan günler ayrı takip edilir.
        # Bunlar normal weekly target içine girmez.

        resmi_tatil_work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
            and ds in resmi_tatil_days_this_week
        ]

        if resmi_tatil_work_vars:

            resmi_tatil_work_week[(a, wk)] = model.NewIntVar(
                0,
                len(resmi_tatil_work_vars),
                f"resmi_tatil_work_week_{a}_{wk}"
            )

            model.Add(
                resmi_tatil_work_week[(a, wk)]
                == sum(resmi_tatil_work_vars)
            )

            resmi_tatil_work_week_constraints += 1

        # --------------------------------------------------
        # 4.7) NORMAL HAFTALIK HEDEF
        # --------------------------------------------------

        normal_target = NORMAL_WORK_DAYS
        normal_target -= len(resmi_tatil_days_this_week)
        normal_target -= len(izin_normal_days_this_week)

        normal_target = max(0, normal_target)
        normal_target = min(normal_target, len(normal_work_vars))

        # --------------------------------------------------
        # 4.8) İZİNLİ HAFTADA NORMAL MESAİ KAPAT
        # --------------------------------------------------
        # Agent o hafta izin aldıysa, haftalık hedef zaten düşer.
        # Bu hedef overtime ile tekrar yukarı çekilmemeli.
        #
        # Örnek:
        # Cumartesi-Pazar izin aldıysa:
        # normal_target = 3
        #
        # overtime_week = 1 olursa 4 gün çalışabilir.
        # Bu istenmiyor.
        #
        # Bu yüzden izinli haftada overtime_week = 0.

        overtime_forced_zero_reason = None

        if len(izin_normal_days_this_week) > 0:
            model.Add(overtime_week[(a, wk)] == 0)
            leave_week_overtime_block_constraints += 1
            overtime_forced_zero_reason = "izinli_hafta"

        # --------------------------------------------------
        # 4.9) MESAİYE KALAMAZ AGENT NORMAL MESAİ ALAMAZ
        # --------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

            if overtime_forced_zero_reason is None:
                overtime_forced_zero_reason = "mesaiye_kalamaz"
            else:
                overtime_forced_zero_reason += "+mesaiye_kalamaz"

        # --------------------------------------------------
        # 4.10) HAFTALIK NORMAL ÇALIŞMA EŞİTLİĞİ - HARD
        # --------------------------------------------------
        # DİKKAT:
        # Artık weekly_under / weekly_over yok.
        #
        # Agent haftalık hedefin altında da kalamaz, üstüne de çıkamaz.
        #
        # Eğer overtime_week = 0 ise:
        # sum(normal_work_vars) == normal_target
        #
        # Eğer overtime_week = 1 ise:
        # sum(normal_work_vars) == normal_target + 1

        model.Add(
            sum(normal_work_vars)
            ==
            normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # --------------------------------------------------
        # 4.11) DEBUG SATIRI
        # --------------------------------------------------

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "normal_work_var_count": len(normal_work_vars),
            "resmi_tatil_work_var_count": len(resmi_tatil_work_vars),
            "izin_normal_count": len(izin_normal_days_this_week),
            "resmi_tatil_count": len(resmi_tatil_days_this_week),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
            "partial_week": False,
            "partial_type": wk_partial_type,
            "partial_week_reason": None,
            "hard_weekly_target": True,
            "overtime_forced_zero_reason": overtime_forced_zero_reason
        })

# --------------------------------------------------
# 5) AYDA MAX NORMAL MESAİ HARD KURALI
# --------------------------------------------------
# Resmi tatil mesaisi bu limite dahil değildir.
# Sadece overtime_week değişkenleri sayılır.
#
# Partial week'lerde overtime_week yukarıda 0'a sabitlendiği için
# ay sınırı haftaları normal mesai limitini tüketmez.

for a in AGENTS:

    a = str(a).strip()

    model.Add(
        sum(
            overtime_week[(a, wk)]
            for wk in WEEKS
            if (a, wk) in overtime_week
        )
        <= MAX_OVERTIME_PER_MONTH
    )

    monthly_overtime_constraints += 1

# --------------------------------------------------
# 6) DEBUG DATAFRAME
# --------------------------------------------------

weekly_target_debug_df = pd.DataFrame(weekly_target_debug_rows)

print("Haftalık hard çalışma kısıtı:", weekly_work_constraints)
print("Mesaiye kalamaz overtime kapatma kısıtı:", weekly_overtime_block_constraints)
print("İzinli haftada overtime kapatma kısıtı:", leave_week_overtime_block_constraints)
print("Partial week skip/overtime kapatma kısıtı:", partial_week_skip_constraints)
print("Aylık max normal mesai kısıtı:", monthly_overtime_constraints)
print("Resmi tatil work week takip kısıtı:", resmi_tatil_work_week_constraints)
print("weekly_under değişken sayısı:", len(weekly_under))
print("weekly_over değişken sayısı:", len(weekly_over))
print("resmi_tatil_work_week değişken sayısı:", len(resmi_tatil_work_week))

print("Partial week kontrol özeti:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["partial_week"] == True
    ]
    .sort_values(["week", "agent_user_code"])
    .head(20)
)

print("Resmi tatil haftası hedef kontrolü:")
display(
    weekly_target_debug_df[
        pd.to_numeric(
            weekly_target_debug_df["resmi_tatil_count"],
            errors="coerce"
        ).fillna(0) > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(10)
)

print("İzinli hafta hedef kontrolü:")
display(
    weekly_target_debug_df[
        pd.to_numeric(
            weekly_target_debug_df["izin_normal_count"],
            errors="coerce"
        ).fillna(0) > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(20)
)



# %% [KONTROL] - HAFTALIK HARD TARGET SONUÇ KONTROLÜ
# Amaç:
# weekly_under / weekly_over kaldırıldıktan sonra
# her agent-week için gerçek çalışma sayısı hedefe eşit mi kontrol etmek.

weekly_hard_target_result_rows = []

for _, r in weekly_target_debug_df.iterrows():

    if bool(r.get("partial_week", False)) == True:
        continue

    if bool(r.get("hard_weekly_target", False)) != True:
        continue

    a = str(r["agent_user_code"]).strip()
    wk = str(r["week"]).strip()

    week_days_list = week_days[wk]

    resmi_tatil_days_this_week = set(
        ds
        for ds in week_days_list
        if ds in resmi_tatil_gunleri_for_weekly
    )

    normal_worked = sum(
        int(solver.Value(work[(a, ds)]))
        for ds in week_days_list
        if (a, ds) in work
        and ds not in resmi_tatil_days_this_week
    )

    overtime_val = (
        int(solver.Value(overtime_week[(a, wk)]))
        if (a, wk) in overtime_week
        else 0
    )

    normal_target = int(r["normal_target"])
    expected_work = normal_target + overtime_val

    izin_normal_count = int(
        pd.to_numeric(
            r.get("izin_normal_count", 0),
            errors="coerce"
        )
    )

    weekly_hard_target_result_rows.append({
        "agent_user_code": a,
        "week": wk,
        "normal_target": normal_target,
        "overtime_week": overtime_val,
        "expected_work": expected_work,
        "actual_normal_worked": normal_worked,
        "izin_normal_count": izin_normal_count,
        "overtime_forced_zero_reason": r.get("overtime_forced_zero_reason"),
        "target_ok": normal_worked == expected_work,
        "izinli_haftada_overtime_ok": (
            overtime_val == 0
            if izin_normal_count > 0
            else True
        )
    })

weekly_hard_target_result_df = pd.DataFrame(weekly_hard_target_result_rows)

print(
    "Haftalık hard target ihlal sayısı:",
    (
        weekly_hard_target_result_df["target_ok"] == False
    ).sum()
)

print(
    "İzinli haftada overtime ihlal sayısı:",
    (
        weekly_hard_target_result_df["izinli_haftada_overtime_ok"] == False
    ).sum()
)

display(
    weekly_hard_target_result_df[
        (weekly_hard_target_result_df["target_ok"] == False)
        |
        (weekly_hard_target_result_df["izinli_haftada_overtime_ok"] == False)
    ]
)
