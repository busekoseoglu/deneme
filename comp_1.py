# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ - FEASIBLE DAY DÜZELTMELİ
# Bu versiyon resmi tatili özel haftalık hedefe karıştırmaz.
# Ama agentın gerçekten çalışabileceği gün sayısını doğru hesaplar.
#
# Kritik düzeltme:
# work[(a, ds)] var diye gün feasible sayılmaz.
# O gün agent için en az bir x[(a, ds, v)] değişkeni varsa feasible sayılır.

# -------------------------------------------------
# Hafta yapısı yoksa oluştur
# -------------------------------------------------

if "day_week" not in globals() or "week_days" not in globals() or "WEEKS" not in globals():

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
# Agent-gün bazında gerçekten vardiya opsiyonu var mı?
# -------------------------------------------------

agent_day_has_shift = {}

for a in AGENTS:
    a = str(a).strip()

    for ds in PLAN_GUNLER:

        has_shift = False

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x:
                has_shift = True
                break

        agent_day_has_shift[(a, ds)] = has_shift


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

        izin_count = len(izin_days_this_week)

        # -------------------------------------------------
        # 2) Gerçekten çalışılabilir günler
        # -------------------------------------------------
        # Bir günün feasible olması için:
        # - work değişkeni olmalı
        # - izin günü olmamalı
        # - agent için en az bir x değişkeni olmalı

        feasible_days = [
            ds
            for ds in week_days_list
            if (a, ds) in work
            and ds not in izin_days_this_week
            and agent_day_has_shift.get((a, ds), False)
        ]

        feasible_day_count = len(feasible_days)

        # -------------------------------------------------
        # 3) Normal haftalık hedef
        # -------------------------------------------------

        normal_target = NORMAL_WORK_DAYS - izin_count
        normal_target = max(0, normal_target)

        # Kritik:
        # Eğer agentın gerçekten çalışabileceği gün sayısı hedefin altındaysa hedefi kırp.
        normal_target = min(normal_target, feasible_day_count)

        # -------------------------------------------------
        # 4) Haftalık çalışma eşitliği
        # -------------------------------------------------
        # work_vars içinde work==0 sabitlenmiş günler olabilir.
        # Sorun değil; hedef feasible_day_count'e göre kırpıldı.

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
        # 6) +1 mesai koyacak gerçek feasible gün yoksa overtime kapat
        # -------------------------------------------------

        if normal_target + 1 > feasible_day_count:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "feasible_day_count": feasible_day_count,
            "izin_count": izin_count,
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
            "no_shift_day_count": sum(
                1
                for ds in week_days_list
                if (a, ds) in work
                and not agent_day_has_shift.get((a, ds), False)
            )
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

print("Feasible day debug:")
display(
    weekly_target_debug_df
    .sort_values(["no_shift_day_count", "week", "agent_user_code"], ascending=[False, True, True])
    .head(100)
)
