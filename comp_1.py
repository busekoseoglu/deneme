# %% [KONTROL] - GÜNDÜZ DIŞI ÇALIŞAMAYACAK KİŞİLER

def time_to_minutes(t):
    h, m = map(int, str(t).split(":"))
    return h * 60 + m


def is_day_only_shift_allowed_text(vardiya_text):
    if vardiya_text in ["off", "izin"]:
        return True

    bas, bit = str(vardiya_text).split("-")

    start_min = time_to_minutes(bas)
    end_min = time_to_minutes(bit)

    # geceye dönen vardiya yasak: 15:00-00:00
    if end_min <= start_min:
        return False

    # 00:00-08:00 gibi erken başlayan vardiya yasak
    if start_min < time_to_minutes("07:00"):
        return False

    # 20:00 sonrası biten vardiya yasak
    if end_min > time_to_minutes("20:00"):
        return False

    return True


day_only_agents = df_tam[
    (df_tam["sabah_calisir_flg"].astype(int) == 1) |
    (df_tam["hamile_flg"].astype(int) == 1) |
    (df_tam["sut_izni_flg"].astype(int) == 1)
]["agent_user_code"].astype(str).str.strip().tolist()


problems = []

for a in day_only_agents:
    if a not in roster.index:
        continue

    for ds in roster.columns:
        vardiya_text = roster.loc[a, ds]

        if not is_day_only_shift_allowed_text(vardiya_text):
            problems.append({
                "agent": a,
                "tarih": ds,
                "vardiya": vardiya_text
            })

day_only_problem_df = pd.DataFrame(problems)

display(day_only_problem_df)
print("Gündüz dışı çalışma problemi:", len(day_only_problem_df))
