# %% [KISIT] - AYLIK EKSTRA OFF / TELAFİ DENGESİ

# Mantık:
#
# Haftalık ilk 2 hard OFF talebi standart OFF hakkıdır.
# Bunlar için telafi gerekmez.
#
# 2'yi aşan hard OFF talepleri extra_off_week içinde tutulur.
#
# Aylık toplam ekstra OFF:
#     aylık toplam telafi günüyle kesin olarak eşit olmalıdır.
#
# Örnek:
#     Bir hafta 2 hard OFF  -> extra_off_week = 0
#     Bir hafta 3 hard OFF  -> extra_off_week = 1
#     Bir hafta 4 hard OFF  -> extra_off_week = 2
#
# İzin günleri extra_off_week hesabına dahil değildir.

aylik_telafi_debug_rows = []

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

    # Ay içindeki ekstra OFF günleri kesinlikle başka haftalarda
    # telafi edilmelidir.
    model.Add(
        sum(agent_extra_off_vars)
        ==
        sum(agent_overtime_vars)
    )

    # Agentın ay içinde yapabileceği maksimum telafi günü
    model.Add(
        sum(agent_overtime_vars)
        <= MAX_OVERTIME_PER_MONTH
    )

    aylik_telafi_debug_rows.append({
        "agent_user_code": a,
        "extra_off_week_var_sayisi": len(agent_extra_off_vars),
        "overtime_week_var_sayisi": len(agent_overtime_vars),
    })


aylik_telafi_debug_df = pd.DataFrame(
    aylik_telafi_debug_rows
)

print("Aylık ekstra OFF / telafi eşitliği eklendi.")
print("Agent sayısı:", len(AGENTS))
print("Aylık maksimum telafi:", MAX_OVERTIME_PER_MONTH)
