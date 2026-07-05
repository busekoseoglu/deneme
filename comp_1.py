# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ
# Amaç:
# Her agent haftalık çalışma hedefi kadar çalışır.
# İzin günleri hedeften düşer.
# Resmi tatilde çalışamayacak agentlar için resmi tatil günü de hedeften düşer.
#
# Örn:
# Normal hedef = 5
# Agent 1 gün izinliyse hedef = 4
# Agent resmi tatilde çalışamaz ve o hafta 1 resmi tatil varsa hedef = 4
# Hem izin hem resmi tatil aynı güne denk gelirse 1 kez düşülür.

# -------------------------------------------------
# Hafta günlerini garanti oluştur
# -------------------------------------------------
# Sende week_days bazen tanımlı olmayabiliyor.
# Bu yüzden bu hücre kendi içinde haftaları oluşturuyor.

day_week = {}
week_days = {}

for ds in PLAN_GUNLER:
    dt = pd.to_datetime(ds)
    wk = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"

    day_week[ds] = wk

    if wk not in week_days:
        week_days[wk] = []

    week_days[wk].append(ds)

WEEKS = sorted(week_days.keys())

print("Hafta sayısı:", len(WEEKS))
print("Haftalar:", WEEKS)


# -------------------------------------------------
# Mesaiye kalamaz agentlar
# -------------------------------------------------

mesaiye_kalamaz_agents = set(
    df_tam[
        pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce")
        .fillna(0)
        .astype(int) == 1
    ]["agent_user_code"].astype(str).str.strip()
)


# -------------------------------------------------
# Resmi tatilde çalışamayacak agentlar
# -------------------------------------------------
# Tatil helper hücresinde tatil_kisitli_agents zaten oluştuysa onu kullanır.
# Yoksa burada tekrar oluşturur.
#
# Kısıtlı agent:
# - hamile
# - süt izni
# - mesaiye kalamaz

if "tatil_kisitli_agents" not in globals():
    tatil_kisitli_agents = set(
        df_tam[
            (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
            (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
            (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
        ]["agent_user_code"].astype(str).str.strip()
    )

# Resmi tatil günlerini güvenli şekilde al
if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_gunleri_for_weekly = set(resmi_tatil_plan_gunleri)
else:
    resmi_tatil_gunleri_for_weekly = set()

    if "ENABLE_RESMI_TATIL_KURALI" in globals() and ENABLE_RESMI_TATIL_KURALI:
        if "RESMI_TATIL_GUNLERI" in globals():
            resmi_tatil_key_set = set(RESMI_TATIL_GUNLERI)

            for ds in PLAN_GUNLER:
                ds_key = pd.to_datetime(ds).strftime("%Y-%m-%d")

                if ds_key in resmi_tatil_key_set:
                    resmi_tatil_gunleri_for_weekly.add(ds)

print("Mesaiye kalamaz agent sayısı:", len(mesaiye_kalamaz_agents))
print("Tatil kısıtlı agent sayısı:", len(tatil_kisitli_agents))
print("Haftalık hedeften düşülecek resmi tatil günleri:", resmi_tatil_gunleri_for_weekly)


# -------------------------------------------------
# Haftalık çalışma + mesai kısıtları
# -------------------------------------------------

weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_overtime_constraints = 0

weekly_target_debug_rows = []

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        # Bu agent-week için work değişkenleri
        work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
        ]

        if not work_vars:
            continue

        # -------------------------------------------------
        # 1) İzin günleri
        # -------------------------------------------------

        izin_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        # -------------------------------------------------
        # 2) Resmi tatil nedeniyle çalışamayacağı günler
        # -------------------------------------------------
        # Sadece tatil kısıtlı agentlar için düşülür.
        # Diğer agentlar resmi tatilde çalışabilir; çalışırlarsa resmi tatil mesaisi olarak etiketlenir.

        resmi_tatil_off_days_this_week = set()

        if a in tatil_kisitli_agents:
            resmi_tatil_off_days_this_week = set(
                ds
                for ds in week_days_list
                if ds in resmi_tatil_gunleri_for_weekly
            )

        # Aynı gün hem izin hem resmi tatilse iki kere düşmeyelim.
        hedef_dusulecek_gunler = izin_days_this_week | resmi_tatil_off_days_this_week

        # -------------------------------------------------
        # 3) Normal haftalık hedef
        # -------------------------------------------------

        normal_target = NORMAL_WORK_DAYS - len(hedef_dusulecek_gunler)
        normal_target = max(0, normal_target)

        # Agentın o hafta çalışabileceği gün sayısı
        # İzin ve resmi tatil-off günlerini çıkarıyoruz.
        feasible_days = [
            ds
            for ds in week_days_list
            if (a, ds) in work
            and ds not in hedef_dusulecek_gunler
        ]

        feasible_day_count = len(feasible_days)

        # Hedef, mümkün gün sayısını aşmasın.
        normal_target = min(normal_target, feasible_day_count)

        # -------------------------------------------------
        # 4) Haftalık çalışma eşitliği
        # -------------------------------------------------
        # Bu mevcut ana mantık:
        # çalışma günü = normal hedef + mesai

        model.Add(
            sum(work_vars) == normal_target + overtime_week[(a, wk)]
        )
        weekly_work_constraints += 1

        # -------------------------------------------------
        # 5) Mesaiye kalamaz agent mesai alamaz
        # -------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        # -------------------------------------------------
        # 6) Eğer mesai yapmak fiziksel olarak mümkün değilse mesaiyi kapat
        # -------------------------------------------------
        # Örn: feasible_day_count = normal_target ise +1 mesai koyacak gün yoktur.

        if normal_target + 1 > feasible_day_count:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "feasible_day_count": feasible_day_count,
            "izin_days_count": len(izin_days_this_week),
            "resmi_tatil_off_days_count": len(resmi_tatil_off_days_this_week),
            "hedef_dusulecek_gun_count": len(hedef_dusulecek_gunler),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
            "tatil_kisitli_agent": a in tatil_kisitli_agents
        })


# -------------------------------------------------
# 7) Ayda max mesai hard kuralı
# -------------------------------------------------

for a in AGENTS:
    a = str(a).strip()

    model.Add(
        sum(
            overtime_week[(a, wk)]
            for wk in WEEKS
            if (a, wk) in overtime_week
        ) <= MAX_OVERTIME_PER_MONTH
    )

    monthly_overtime_constraints += 1


weekly_target_debug_df = pd.DataFrame(weekly_target_debug_rows)

print("Haftalık çalışma kısıtı:", weekly_work_constraints)
print("Haftalık mesai kapatma kısıtı:", weekly_overtime_block_constraints)
print("Aylık max mesai kısıtı:", monthly_overtime_constraints)

print("Resmi tatil nedeniyle haftalık hedefi düşen agent-week sayısı:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["resmi_tatil_off_days_count"] > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(100)
)
