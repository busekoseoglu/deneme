# %% [HÜCRE] - HAFTALIK ÇALIŞMA + NORMAL MESAİ - RESMİ TATİL AYRI
# Mantık:
# - Normal haftalık çalışma sadece resmi tatil olmayan günlerden hesaplanır.
# - Normal mesai = overtime_week.
# - Resmi tatilde çalışma bu eşitliğe girmez.
# - Resmi tatil mesaisi, ayda max 2 normal mesai limitine dahil değildir.
# - Partial week'lerde haftalık hedef kurulmaz.
# - Şimdilik weekly_under / weekly_over soft debug olarak kalır.

# --------------------------------------------------
# 0) MESAIYE KALAMAZ AGENT SETİ
# --------------------------------------------------
# mesaiye_kalamaz_flg = 1 olan agentlar normal mesai alamaz.
# Yani overtime_week[(agent, week)] = 0 olacak.

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
# Bu set haftalık çalışma hedefinden düşülecek resmi tatil günlerini tutar.
#
# Öncelik:
# 1) Eğer daha önce resmi_tatil_plan_gunleri üretildiyse onu kullan.
# 2) Yoksa CONFIG içindeki RESMI_TATIL_GUNLERI üzerinden PLAN_GUNLER ile eşleştir.

resmi_tatil_gunleri_for_weekly = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_gunleri_for_weekly = set(resmi_tatil_plan_gunleri)

else:
    if "ENABLE_RESMI_TATIL_KURALI" in globals() and ENABLE_RESMI_TATIL_KURALI:
        if "RESMI_TATIL_GUNLERI" in globals():

            resmi_tatil_key_set = set(RESMI_TATIL_GUNLERI)

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
# Helper hücresi daha önce çalıştıysa:
# - week_boundary_df
# - partial_weeks
# zaten hazır olmalı.
#
# Yine de hücre patlamasın diye default koruma ekliyoruz.

if "SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS" not in globals():
    SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS = True

if "partial_weeks" not in globals():
    partial_weeks = set()

# --------------------------------------------------
# 3) KISIT SAYAÇLARI VE DEĞİŞKEN SÖZLÜKLERİ
# --------------------------------------------------

weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_overtime_constraints = 0
partial_week_skip_constraints = 0

weekly_under = {}
weekly_over = {}
resmi_tatil_work_week = {}

weekly_target_debug_rows = []

# --------------------------------------------------
# 4) HAFTALIK NORMAL ÇALIŞMA HEDEFİ
# --------------------------------------------------
# Her agent-week için:
#
# normal_target =
# NORMAL_WORK_DAYS
# - o haftadaki resmi tatil gün sayısı
# - o haftadaki normal izin gün sayısı
#
# Daha sonra:
#
# sum(normal_work_vars)
# + weekly_under
# - weekly_over
# =
# normal_target + overtime_week
#
# Not:
# Resmi tatil çalışması bu eşitliğe girmez.
# Resmi tatil çalışması ayrıca resmi_tatil_work_week içinde takip edilir.

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        # --------------------------------------------------
        # 4.1) PARTIAL WEEK KONTROLÜ
        # --------------------------------------------------
        # Haftalık çalışma hedefi sadece tam haftalarda uygulanır.
        #
        # Partial week'lerde model haftanın tamamını görmediği için
        # haftalık hedefi bu ay içinde kapatmaya çalışmamalıdır.
        #
        # Örnek:
        # Haziran 2026 W27 sadece 29-30 Haziran'dır.
        # Bu hafta Temmuz ile tamamlanacağı için Haziran modelinde
        # weekly target kurulmaz.
        #
        # Coverage kuralı yine çalışır.
        #
        # Ayrıca overtime_week varsa 0'a sabitlenir.
        # Çünkü partial week'te normal haftalık hedef kurulmadığı için
        # bu haftanın normal mesai tüketmesi de istenmez.

        wk_str = str(wk).strip()

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
                "partial_week_reason": "weekly_target_skip"
            })

            continue

        # --------------------------------------------------
        # 4.2) OVERTIME WEEK DEĞİŞKENİ VAR MI?
        # --------------------------------------------------
        # Bu modelde overtime_week daha önce oluşturuluyor.
        # Eğer agent-week için değişken yoksa bu hafta atlanır.

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
        # agent_izinli_mi(a, ds):
        # - özel off
        # - tekrar izin
        # - pzt/cuma izinleri
        # - tam ay izinleri
        # gibi izin_map içine alınmış günleri kontrol eder.

        izin_days_this_week = set(
            ds
            for ds in week_days_list
            if agent_izinli_mi(a, ds)
        )

        # Resmi tatilde izin varsa, normal hedeften iki kere düşmemesi için
        # resmi tatil günlerini izin setinden çıkarıyoruz.

        izin_normal_days_this_week = (
            izin_days_this_week
            - resmi_tatil_days_this_week
        )

        # --------------------------------------------------
        # 4.5) NORMAL GÜNLERDEKİ WORK DEĞİŞKENLERİ
        # --------------------------------------------------
        # DİKKAT:
        # Resmi tatil günleri burada yok.
        # Bu yüzden resmi tatilde çalışmak overtime_week tüketmez.

        normal_work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
            and ds not in resmi_tatil_days_this_week
        ]

        # Eğer bu agent-week için normal gün work değişkeni yoksa,
        # haftalık normal hedef kurmaya gerek yok.

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
                "partial_week_reason": "normal_work_var_yok"
            })
            continue

        # --------------------------------------------------
        # 4.6) RESMİ TATİL WORK DEĞİŞKENLERİ
        # --------------------------------------------------
        # Resmi tatilde çalışılan günler ayrı takip edilir.
        # Bunlar haftalık normal çalışma eşitliğine girmez.

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

        # --------------------------------------------------
        # 4.7) NORMAL HAFTALIK HEDEF
        # --------------------------------------------------
        # Normal hedef:
        # NORMAL_WORK_DAYS
        # - resmi tatil gün sayısı
        # - normal izin gün sayısı
        #
        # Sonra hedef:
        # - 0'ın altına düşemez.
        # - eldeki normal_work_vars sayısını aşamaz.

        normal_target = NORMAL_WORK_DAYS
        normal_target -= len(resmi_tatil_days_this_week)
        normal_target -= len(izin_normal_days_this_week)

        normal_target = max(0, normal_target)
        normal_target = min(normal_target, len(normal_work_vars))

        # --------------------------------------------------
        # 4.8) WEEKLY SAPMA DEĞİŞKENLERİ
        # --------------------------------------------------
        # weekly_under:
        # Agent hedefin altında kalırsa pozitif olur.
        #
        # weekly_over:
        # Agent hedefin üstüne çıkarsa pozitif olur.
        #
        # Bu ikisi soft debug/ceza mantığı için tutuluyor.

        weekly_under[(a, wk)] = model.NewIntVar(
            0,
            len(normal_work_vars),
            f"weekly_under_{a}_{wk}"
        )

        weekly_over[(a, wk)] = model.NewIntVar(
            0,
            len(normal_work_vars),
            f"weekly_over_{a}_{wk}"
        )

        # --------------------------------------------------
        # 4.9) HAFTALIK NORMAL ÇALIŞMA EŞİTLİĞİ
        # --------------------------------------------------
        # DİKKAT:
        # Sadece normal günler eşitlikte.
        # Resmi tatil çalışması burada yok.
        #
        # sum(normal_work_vars)
        # + weekly_under
        # - weekly_over
        # =
        # normal_target + overtime_week
        #
        # overtime_week = 1 ise agent o hafta 1 normal mesai almış sayılır.

        model.Add(
            sum(normal_work_vars)
            + weekly_under[(a, wk)]
            - weekly_over[(a, wk)]
            ==
            normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # --------------------------------------------------
        # 4.10) MESAİYE KALAMAZ AGENT NORMAL MESAİ ALAMAZ
        # --------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

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
            "partial_week_reason": None
        })

# --------------------------------------------------
# 5) AYDA MAX NORMAL MESAİ HARD KURALI
# --------------------------------------------------
# Resmi tatil mesaisi bu limite dahil değildir.
#
# Sadece overtime_week değişkenleri sayılır.
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

print("Haftalık normal çalışma soft kısıtı:", weekly_work_constraints)
print("Haftalık normal mesai kapatma kısıtı:", weekly_overtime_block_constraints)
print("Partial week skip/overtime kapatma kısıtı:", partial_week_skip_constraints)
print("Aylık max normal mesai kısıtı:", monthly_overtime_constraints)
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
