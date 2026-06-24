# %% [DEBUG] - 2026-W23 HANGİ VARDİYALARDA SIKIŞIYOR?

problem_wk = "2026-W23"

w23_pattern_need = (
    pattern_need_df[pattern_need_df["week_key"] == problem_wk]
    .sort_values("min_agents_needed", ascending=False)
)

display(w23_pattern_need)

print("W23 toplam minimum agent ihtiyacı:", w23_pattern_need["min_agents_needed"].sum())
print("Mevcut agent sayısı:", len(AGENTS))
print("Gap:", len(AGENTS) - w23_pattern_need["min_agents_needed"].sum())
