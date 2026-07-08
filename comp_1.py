    # --------------------------------------------------
    # AY SINIRI / WEEK BOUNDARY PARAMETRELERİ
    # --------------------------------------------------
    # Amaç:
    # Model aylık plan üretse de bazı kurallar haftalık çalışır.
    # Ay başı veya ay sonunda ISO hafta bölünüyorsa bu hafta partial week kabul edilir.
    #
    # Örnek:
    # Haziran 2026:
    # 2026-W27 sadece 29-30 Haziran olarak modelde görünür.
    # Ancak hafta 1-5 Temmuz ile devam eder.
    #
    # Bu nedenle haftalık hedef, ekip base vardiya, lokasyon oranı gibi kurallar
    # ay sınırında dikkatli ele alınmalıdır.

    # Haftalık hedefin tam uygulanması için model içinde görülmesi gereken
    # normal hafta içi gün sayısı.
    "FULL_WEEKDAY_COUNT": 5,

    # Partial week'lerde haftalık çalışma hedefi kurulmasın.
    # Coverage yine çalışır.
    "SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS": True,

    # Partial week günlerinde fazla atama limiti.
    # 0: assigned <= required
    # 1 veya 2: küçük esneklik bırakır.
    "PARTIAL_WEEK_MAX_FAZLA_ATAMA": 0,

    # Ay sonundaki partial week'te, mümkün olduğunca agentların
    # görünen günlerin tamamında OFF kalmasını engellemek için soft ceza.
    #
    # Örn:
    # Haziran sonunda sadece Pzt-Salı görünüyorsa,
    # bu iki günün ikisinde de OFF kalan agent sayısı minimize edilir.
    "ENABLE_PARTIAL_END_WEEK_ALL_OFF_PENALTY": True,
    "PARTIAL_END_WEEK_ALL_OFF_W": 5000,



# --------------------------------------------------
# AY SINIRI / WEEK BOUNDARY PARAMETRELERİ
# --------------------------------------------------

FULL_WEEKDAY_COUNT = CONFIG["FULL_WEEKDAY_COUNT"]
SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS = CONFIG["SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS"]
PARTIAL_WEEK_MAX_FAZLA_ATAMA = CONFIG["PARTIAL_WEEK_MAX_FAZLA_ATAMA"]

ENABLE_PARTIAL_END_WEEK_ALL_OFF_PENALTY = CONFIG["ENABLE_PARTIAL_END_WEEK_ALL_OFF_PENALTY"]
PARTIAL_END_WEEK_ALL_OFF_W = CONFIG["PARTIAL_END_WEEK_ALL_OFF_W"]


# %% [HÜCRE] - WEEK BOUNDARY / PARTIAL WEEK HELPER
# Amaç:
# Model aylık plan üretse de bazı kurallar haftalık çalışır.
#
# Ay başı veya ay sonunda ISO hafta bölünebilir.
# Bu durumda model haftanın sadece bir kısmını görür.
#
# Örnek:
# Haziran 2026:
# 2026-W27 = 29 Haziran - 5 Temmuz
# Haziran modeli sadece 29-30 Haziran'ı görür.
# Bu hafta partial_end_week kabul edilir.
#
# Temmuz 2026:
# 2026-W27 = 29 Haziran - 5 Temmuz
# Temmuz modeli sadece 1-5 Temmuz'u görür.
# Bu hafta partial_start_week kabul edilir.
#
# Bu helper tüm aylar için dinamik çalışır.
# Hiçbir tarih hard-code edilmez.

from datetime import timedelta

plan_dates = sorted([pd.to_datetime(d).date() for d in PLAN_GUNLER])
plan_date_set = set(plan_dates)

PLAN_START_DATE = min(plan_dates)
PLAN_END_DATE = max(plan_dates)

week_boundary_rows = []

for wk in sorted(WEEKS):
    
    # --------------------------------------------------
    # 1) Bu haftanın model içinde görünen günleri
    # --------------------------------------------------
    
    week_days_list = sorted([
        pd.to_datetime(d).date()
        for d in week_days[wk]
    ])
    
    # --------------------------------------------------
    # 2) ISO haftanın gerçek Pazartesi-Pazar aralığı
    # --------------------------------------------------
    # ISO calendar'da weekday:
    # Pazartesi = 1
    # Pazar = 7
    
    sample_day = week_days_list[0]
    iso_weekday = sample_day.isocalendar().weekday
    
    week_start = sample_day - timedelta(days=iso_weekday - 1)
    week_end = week_start + timedelta(days=6)
    
    full_week_days = [
        week_start + timedelta(days=i)
        for i in range(7)
    ]
    
    full_weekdays = [
        d for d in full_week_days
        if d.weekday() in [0, 1, 2, 3, 4]
    ]
    
    # --------------------------------------------------
    # 3) Plan içinde görünen gün / weekday sayıları
    # --------------------------------------------------
    
    plan_days_in_week = [
        d for d in full_week_days
        if d in plan_date_set
    ]
    
    plan_weekdays_in_week = [
        d for d in plan_days_in_week
        if d.weekday() in [0, 1, 2, 3, 4]
    ]
    
    plan_days_count = len(plan_days_in_week)
    plan_weekday_count = len(plan_weekdays_in_week)
    full_weekday_count = len(full_weekdays)
    
    # --------------------------------------------------
    # 4) Partial week tipi
    # --------------------------------------------------
    # Haftanın tamamı plan ayı içinde değilse partial kabul edilir.
    #
    # partial_start:
    # Haftanın başlangıcı plan ayından önce kalmış.
    # Örn: Temmuz 1 Çarşamba başlıyorsa, Pazartesi-Salı Haziran'dadır.
    #
    # partial_end:
    # Haftanın bitişi plan ayından sonra kalmış.
    # Örn: Haziran 30 Salı bitiyorsa, Çarşamba-Pazar Temmuz'dadır.
    
    is_partial_week = plan_weekday_count < FULL_WEEKDAY_COUNT
    
    if not is_partial_week:
        partial_type = "full_week"
    else:
        if week_start < PLAN_START_DATE:
            partial_type = "partial_start"
        elif week_end > PLAN_END_DATE:
            partial_type = "partial_end"
        else:
            partial_type = "partial_inside"
    
    week_boundary_rows.append({
        "week": wk,
        "week_start": week_start,
        "week_end": week_end,
        "plan_start_date": PLAN_START_DATE,
        "plan_end_date": PLAN_END_DATE,
        "plan_days_count": plan_days_count,
        "plan_weekday_count": plan_weekday_count,
        "full_weekday_count": full_weekday_count,
        "is_partial_week": is_partial_week,
        "partial_type": partial_type,
        "plan_days_in_week": plan_days_in_week,
        "plan_weekdays_in_week": plan_weekdays_in_week
    })

week_boundary_df = pd.DataFrame(week_boundary_rows)

# --------------------------------------------------
# 5) Kurallarda kullanılacak set'ler
# --------------------------------------------------

partial_weeks = set(
    week_boundary_df.loc[
        week_boundary_df["is_partial_week"] == True,
        "week"
    ]
)

partial_start_weeks = set(
    week_boundary_df.loc[
        week_boundary_df["partial_type"] == "partial_start",
        "week"
    ]
)

partial_end_weeks = set(
    week_boundary_df.loc[
        week_boundary_df["partial_type"] == "partial_end",
        "week"
    ]
)

full_weeks = set(
    week_boundary_df.loc[
        week_boundary_df["partial_type"] == "full_week",
        "week"
    ]
)

print("Week boundary helper oluşturuldu.")
print("Full week sayısı:", len(full_weeks))
print("Partial week sayısı:", len(partial_weeks))
print("Partial start week sayısı:", len(partial_start_weeks))
print("Partial end week sayısı:", len(partial_end_weeks))

display(
    week_boundary_df[
        [
            "week",
            "week_start",
            "week_end",
            "plan_days_count",
            "plan_weekday_count",
            "full_weekday_count",
            "is_partial_week",
            "partial_type"
        ]
    ]
)


        # --------------------------------------------------
        # PARTIAL WEEK KONTROLÜ
        # --------------------------------------------------
        # Haftalık çalışma hedefi sadece tam haftalarda uygulanır.
        #
        # Partial week'lerde model haftanın tamamını görmediği için
        # haftalık hedefi bu ay içinde kapatmaya çalışmamalıdır.
        #
        # Örn:
        # Haziran 2026 W27 sadece 29-30 Haziran'dır.
        # Bu hafta Temmuz ile tamamlanacağı için Haziran modelinde
        # weekly target kurulmaz.
        #
        # Coverage kuralı yine çalışır.

        if SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS and wk in partial_weeks:
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
                "partial_type": (
                    week_boundary_df
                    .loc[week_boundary_df["week"] == wk, "partial_type"]
                    .iloc[0]
                ),
                "partial_week_reason": "weekly_target_skip"
            })
            continue



        # --------------------------------------------------
        # Normal / partial week fazla atama limiti
        # --------------------------------------------------
        # Normal haftalarda mevcut fazla_atama_ust_limit kullanılır.
        #
        # Partial week'lerde ise fazla atama limiti sıkılaştırılır.
        # Çünkü bu haftalar ay sınırına denk gelir ve fazla kişileri
        # burada yığmak sonraki ayın planını bozabilir.

        wk = day_week[ds]

        if wk in partial_weeks:
            max_fazla = PARTIAL_WEEK_MAX_FAZLA_ATAMA
        else:
            max_fazla = fazla_atama_ust_limit.get(
                (ds, v),
                GENEL_MAX_FAZLA_ATAMA
            )



# %% [HÜCRE] - PARTIAL END WEEK TAMAMEN OFF KALMA CEZASI
# Amaç:
# Ay sonundaki partial week'lerde agentların görünen günlerin tamamında OFF kalmasını azaltmak.
#
# Örnek:
# Haziran 2026:
# 2026-W27 içinde model sadece 29-30 Haziran'ı görür.
#
# Eğer bir agent 29 ve 30 Haziran'ın ikisinde de OFF kalırsa,
# Temmuz tarafında aynı haftanın Çarşamba-Pazar kısmında daha fazla çalışmak zorunda kalabilir.
#
# Bu yüzden:
# partial_end_week içinde görünen günlerde work_count = 0 olan agentlar cezalandırılır.
#
# Not:
# Bu hard kural değildir.
# Toplam required tüm agentları en az 1 gün çalıştırmaya yetmiyorsa model infeasible olmaz.
# Sadece hangi agentların tamamen OFF kalacağını daha dengeli seçmeye çalışır.

partial_end_week_all_off = {}
partial_end_week_all_off_rows = []

partial_end_all_off_constraints = 0

if ENABLE_PARTIAL_END_WEEK_ALL_OFF_PENALTY:
    
    for wk in sorted(partial_end_weeks):
        
        # Bu partial end week içinde plan ayına düşen günler
        wk_days = sorted([
            ds
            for ds in week_days[wk]
            if pd.to_datetime(ds).date() in plan_date_set
        ])
        
        # Eğer görünen gün yoksa geç
        if not wk_days:
            continue
        
        for a in AGENTS:
            
            # Agent'ın bu partial end week içindeki work değişkenleri
            agent_work_vars = [
                work[(a, ds)]
                for ds in wk_days
                if (a, ds) in work
            ]
            
            # Eğer agent için bu günlerde hiç work değişkeni yoksa,
            # örn tüm günler izinliyse, bu agentı cezalandırmayalım.
            if not agent_work_vars:
                continue
            
            # work_count:
            # Agent partial end week içinde kaç gün çalıştı?
            work_count = sum(agent_work_vars)
            
            # all_off_var:
            # 1 ise agent bu partial end week içinde hiç çalışmadı.
            # 0 ise en az 1 gün çalıştı.
            all_off_var = model.NewBoolVar(
                f"partial_end_all_off_{a}_{wk}"
            )
            
            partial_end_week_all_off[(a, wk)] = all_off_var
            
            # --------------------------------------------------
            # Mantık:
            # Eğer work_count >= 1 ise all_off_var = 0 olabilir.
            # Eğer work_count = 0 ise all_off_var = 1 olmak zorunda.
            #
            # Aşağıdaki iki constraint bunu lineer şekilde kurar.
            # n = görünen gün sayısı
            #
            # work_count + n * all_off_var >= 1
            # work_count <= n * (1 - all_off_var)
            #
            # Örnek n=2:
            # work_count=0 ise:
            #   0 + 2*all_off >= 1 → all_off=1
            #
            # work_count>=1 ise:
            #   work_count <= 2*(1-all_off)
            #   all_off=1 olamaz, çünkü RHS=0 olur.
            # --------------------------------------------------
            
            n = len(agent_work_vars)
            
            model.Add(
                work_count + n * all_off_var >= 1
            )
            
            model.Add(
                work_count <= n * (1 - all_off_var)
            )
            
            partial_end_all_off_constraints += 2
            
            partial_end_week_all_off_rows.append({
                "agent_user_code": a,
                "week": wk,
                "partial_type": "partial_end",
                "visible_days_count": n,
                "all_off_var": f"partial_end_all_off_{a}_{wk}"
            })

partial_end_week_all_off_debug_df = pd.DataFrame(
    partial_end_week_all_off_rows
)

print("Partial end week all-off değişken sayısı:", len(partial_end_week_all_off))
print("Partial end week all-off constraint sayısı:", partial_end_all_off_constraints)

if len(partial_end_week_all_off_debug_df) > 0:
    display(partial_end_week_all_off_debug_df.head(20))



# --------------------------------------------------
# PARTIAL END WEEK TAMAMEN OFF KALMA CEZASI
# --------------------------------------------------
# Amaç:
# Ay sonundaki partial week'te bir agent'ın görünen günlerin tamamında OFF kalmasını azaltmak.
#
# Örn:
# Haziran sonunda sadece Pazartesi-Salı görünüyorsa,
# ikisinde de OFF kalan agent sayısı minimize edilir.
#
# Bu soft ceza olduğu için infeasible yaratmaz.

if "partial_end_week_all_off" in globals():
    for key, var in partial_end_week_all_off.items():
        objective_terms.append(
            PARTIAL_END_WEEK_ALL_OFF_W * var
        )

print("PARTIAL_END_WEEK_ALL_OFF_W:", PARTIAL_END_WEEK_ALL_OFF_W)
