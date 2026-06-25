# %% EXCEL - FINAL KİŞİ BAZLI KONTROL DOSYASI
# Yeni kurallar dahil:
# - Haftalık çalışma hedefi = 5 - izin günü + mesai
# - Ayda max 2 mesai
# - Mesaiye kalamaz kişiye mesai yok
# - Hafta içi takım bütünlüğü hard
# - Hafta sonu takım serbest
# - Ayda en az 1 Cumartesi-Pazar peş peşe OFF
# - %10 coverage buffer
# - 11 saat dinlenme
# - Max 6 gün üst üste çalışma
# - Sabah çalışan / hamile / süt izni / izin kontrolleri

import pandas as pd
import numpy as np

# -------------------------------------------------
# 0) Yardımcı fonksiyonlar
# -------------------------------------------------

def to_int_flag(s):
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

def dk(t):
    if pd.isna(t):
        return np.nan
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)

def shift_start_end(tarih, baslangic, bitis):
    if pd.isna(baslangic) or pd.isna(bitis):
        return pd.NaT, pd.NaT

    start_dt = pd.to_datetime(f"{tarih} {baslangic}")
    end_dt = pd.to_datetime(f"{tarih} {bitis}")

    if end_dt <= start_dt:
        end_dt += pd.Timedelta(days=1)

    return start_dt, end_dt


# -------------------------------------------------
# 1) Agent ana bilgileri
# -------------------------------------------------

agent_cols = [
    "agent_user_code",
    "agent_name",
    "teamleader_name",
    "working_main_group",
    "line_based_main_group",
    "takim",
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]

agent_base = df_tam[agent_cols].copy()
agent_base["agent_user_code"] = agent_base["agent_user_code"].astype(str).str.strip()

flag_cols = [
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]

for c in flag_cols:
    agent_base[c] = to_int_flag(agent_base[c])


# -------------------------------------------------
# 2) Tarih ana tablosu
# -------------------------------------------------

date_base = pd.DataFrame({"tarih": [str(ds) for ds in PLAN_GUNLER]})
date_base["tarih_dt"] = pd.to_datetime(date_base["tarih"])
date_base["gun"] = date_base["tarih_dt"].apply(lambda x: DAY_TR[x.weekday()])
date_base["weekday"] = date_base["tarih_dt"].dt.weekday
date_base["hafta_ici"] = date_base["weekday"].isin([0, 1, 2, 3, 4])
date_base["hafta_sonu"] = date_base["weekday"].isin([5, 6])
date_base["hafta"] = date_base["tarih"].map(day_week)


# -------------------------------------------------
# 3) Agent x Tarih full grid
# -------------------------------------------------

agent_base["_key"] = 1
date_base["_key"] = 1

agent_roster_full = (
    agent_base
    .merge(date_base, on="_key", how="outer")
    .drop(columns="_key")
)

agent_base = agent_base.drop(columns="_key")
date_base = date_base.drop(columns="_key")


# -------------------------------------------------
# 4) Solve sonucundan roster oluştur
# -------------------------------------------------

roster_rows = []

for a in AGENTS:
    for ds in PLAN_GUNLER:
        ds_str = str(ds)

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                roster_rows.append({
                    "agent_user_code": str(a).strip(),
                    "tarih": ds_str,
                    "vardiya": v,
                    "baslangic": saat[(ds, v)][0],
                    "bitis": saat[(ds, v)][1],
                    "hafta": day_week[ds],
                    "gun": DAY_TR[pd.to_datetime(ds).weekday()],
                    "weekday": pd.to_datetime(ds).weekday(),
                    "hafta_ici": pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4],
                    "takim": agent_team.get(a)
                })

roster_df = pd.DataFrame(roster_rows)

if len(roster_df) == 0:
    roster_df = pd.DataFrame(
        columns=[
            "agent_user_code", "tarih", "vardiya", "baslangic", "bitis",
            "hafta", "gun", "weekday", "hafta_ici", "takim"
        ]
    )


# -------------------------------------------------
# 5) Full grid'e vardiya atamalarını ekle
# -------------------------------------------------

roster_assign = roster_df[
    [
        "agent_user_code",
        "tarih",
        "vardiya",
        "baslangic",
        "bitis"
    ]
].copy()

agent_roster_full = agent_roster_full.merge(
    roster_assign,
    on=["agent_user_code", "tarih"],
    how="left"
)

agent_roster_full["durum"] = np.where(
    agent_roster_full["vardiya"].notna(),
    "WORK",
    "OFF"
)


# -------------------------------------------------
# 6) İzin bilgisi
# -------------------------------------------------

agent_roster_full["izinli_mi"] = agent_roster_full.apply(
    lambda r: pd.to_datetime(r["tarih"]).date() in izin_map.get(r["agent_user_code"], set()),
    axis=1
)

agent_roster_full["durum_detay"] = np.where(
    agent_roster_full["durum"] == "WORK",
    "WORK",
    np.where(agent_roster_full["izinli_mi"], "OFF_IZIN", "OFF")
)


# -------------------------------------------------
# 7) Team base vardiya tablosu
# -------------------------------------------------

team_base_rows = []

for t in TAKIMLAR:
    for wk in WEEKS:
        for v in week_vardiyalari[wk]:
            if (t, wk, v) in team_week_base and solver.Value(team_week_base[(t, wk, v)]) == 1:
                team_base_rows.append({
                    "takim": t,
                    "hafta": wk,
                    "base_vardiya": v
                })

team_base_df = pd.DataFrame(team_base_rows)

agent_roster_full = agent_roster_full.merge(
    team_base_df,
    on=["takim", "hafta"],
    how="left"
)

# Hafta içi çalışıyorsa base vardiyada olmalı.
# Hafta sonu takım serbest olduğu için base kontrolünü TRUE sayıyoruz.
agent_roster_full["base_vardiya_ok"] = np.where(
    (agent_roster_full["durum"] == "WORK") & (agent_roster_full["hafta_ici"]),
    agent_roster_full["vardiya"].eq(agent_roster_full["base_vardiya"]),
    True
)


# -------------------------------------------------
# 8) Saat ve 11 saat dinlenme kontrolü
# -------------------------------------------------

agent_roster_full[["start_dt", "end_dt"]] = agent_roster_full.apply(
    lambda r: pd.Series(shift_start_end(r["tarih"], r["baslangic"], r["bitis"])),
    axis=1
)

# 11 saat kontrolünü sadece WORK satırları arasında yapıyoruz
work_only = agent_roster_full[agent_roster_full["durum"] == "WORK"].copy()
work_only = work_only.sort_values(["agent_user_code", "start_dt"])

work_only["next_tarih"] = work_only.groupby("agent_user_code")["tarih"].shift(-1)
work_only["next_vardiya"] = work_only.groupby("agent_user_code")["vardiya"].shift(-1)
work_only["next_start_dt"] = work_only.groupby("agent_user_code")["start_dt"].shift(-1)

work_only["dinlenme_saat"] = (
    (work_only["next_start_dt"] - work_only["end_dt"])
    .dt.total_seconds() / 3600
)

work_only["dinlenme_11_saat_ok"] = (
    work_only["dinlenme_saat"].isna() |
    (work_only["dinlenme_saat"] >= 11)
)

rest_cols = [
    "agent_user_code",
    "tarih",
    "next_tarih",
    "next_vardiya",
    "dinlenme_saat",
    "dinlenme_11_saat_ok"
]

agent_roster_full = agent_roster_full.merge(
    work_only[rest_cols],
    on=["agent_user_code", "tarih"],
    how="left"
)

agent_roster_full["dinlenme_11_saat_ok"] = agent_roster_full["dinlenme_11_saat_ok"].fillna(True)


# -------------------------------------------------
# 9) Özel kural kontrolleri
# -------------------------------------------------

agent_roster_full["bas_dk"] = agent_roster_full["baslangic"].apply(dk)
agent_roster_full["bit_dk"] = agent_roster_full["bitis"].apply(dk)

mask_gece = (
    (agent_roster_full["durum"] == "WORK") &
    agent_roster_full["bit_dk"].notna() &
    agent_roster_full["bas_dk"].notna() &
    (agent_roster_full["bit_dk"] <= agent_roster_full["bas_dk"])
)

agent_roster_full.loc[mask_gece, "bit_dk"] += 24 * 60

# Sabah çalışır: 20:00 sonrası biten vardiyada çalışamaz
agent_roster_full["sabah_calisir_ok"] = ~(
    (agent_roster_full["durum"] == "WORK") &
    (agent_roster_full["sabah_calisir_flg"] == 1) &
    (agent_roster_full["bit_dk"] > dk("20:00"))
)

# Hamile / süt izni: hafta sonu çalışamaz
agent_roster_full["hamile_sut_hafta_sonu_ok"] = ~(
    (agent_roster_full["durum"] == "WORK") &
    (
        (agent_roster_full["hamile_flg"] == 1) |
        (agent_roster_full["sut_izni_flg"] == 1)
    ) &
    (agent_roster_full["hafta_sonu"])
)

# İzinli günde çalışamaz
agent_roster_full["izin_ok"] = ~(
    (agent_roster_full["durum"] == "WORK") &
    (agent_roster_full["izinli_mi"])
)


# -------------------------------------------------
# 10) Hafta bazlı çalışma + mesai kontrolü
# -------------------------------------------------

weekly_rows = []

for a in AGENTS:
    a = str(a).strip()
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        izin_count_this_week = sum(
            1
            for ds in days_in_week
            if pd.to_datetime(ds).date() in izinli
        )

        raw_normal_target = max(0, 5 - izin_count_this_week)

        feasible_days = []
        for ds in days_in_week:
            d_date = pd.to_datetime(ds).date()

            if d_date in izinli:
                continue

            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                feasible_days.append(ds)

        normal_target = min(raw_normal_target, len(feasible_days))

        worked_days = sum(
            solver.Value(work[(a, ds)])
            for ds in days_in_week
        )

        overtime_val = solver.Value(overtime_week[(a, wk)])

        weekly_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "haftadaki_gun": len(days_in_week),
            "izin_count_this_week": izin_count_this_week,
            "raw_normal_target": raw_normal_target,
            "feasible_day_count": len(feasible_days),
            "normal_target": normal_target,
            "worked_days": worked_days,
            "overtime_week": overtime_val,
            "worked_minus_target": worked_days - normal_target,
            "haftalik_calisma_ok": worked_days == normal_target + overtime_val
        })

agent_week_check = pd.DataFrame(weekly_rows)

agent_info_week = agent_base[
    [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "mesaiye_kalamaz_flg"
    ]
].copy()

agent_week_check = agent_week_check.merge(
    agent_info_week,
    on="agent_user_code",
    how="left"
)

agent_week_check["mesaiye_kalamaz_mesai_ok"] = ~(
    (agent_week_check["mesaiye_kalamaz_flg"] == 1) &
    (agent_week_check["overtime_week"] > 0)
)


# -------------------------------------------------
# 11) Max 6 gün üst üste çalışma kontrolü
# -------------------------------------------------

streak_rows = []

for a, grp in agent_roster_full.groupby("agent_user_code"):
    grp = grp.sort_values("tarih_dt")

    max_streak = 0
    current_streak = 0

    for _, r in grp.iterrows():
        if r["durum"] == "WORK":
            current_streak += 1
        else:
            current_streak = 0

        max_streak = max(max_streak, current_streak)

    streak_rows.append({
        "agent_user_code": a,
        "max_ust_uste_gun": max_streak,
        "max_6_gun_ok": max_streak <= 6
    })

streak_check = pd.DataFrame(streak_rows)


# -------------------------------------------------
# 12) Cumartesi-Pazar peş peşe OFF kontrolü
# -------------------------------------------------

# weekend_pairs yoksa burada yeniden oluşturuyoruz
weekend_pairs_final = []

plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])
date_to_ds = {
    pd.to_datetime(ds).date(): str(ds)
    for ds in PLAN_GUNLER
}

for d in plan_dates:
    if d.weekday() == 5:
        sunday = d + pd.Timedelta(days=1)

        if sunday in date_to_ds:
            weekend_pairs_final.append((date_to_ds[d], date_to_ds[sunday]))

weekend_off_rows = []

for a in AGENTS:
    a = str(a).strip()

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs_final):
        sat_work = int(solver.Value(work[(a, sat_ds)])) if (a, sat_ds) in work else 0
        sun_work = int(solver.Value(work[(a, sun_ds)])) if (a, sun_ds) in work else 0

        both_off = int((sat_work == 0) and (sun_work == 0))

        weekend_off_rows.append({
            "agent_user_code": a,
            "pair_no": i + 1,
            "cumartesi": sat_ds,
            "pazar": sun_ds,
            "cumartesi_work": sat_work,
            "pazar_work": sun_work,
            "both_off": both_off
        })

weekend_off_check = pd.DataFrame(weekend_off_rows)

agent_weekend_off_summary = (
    weekend_off_check
    .groupby("agent_user_code", as_index=False)
    .agg(
        toplam_pes_pese_hafta_sonu_off=("both_off", "sum")
    )
)

agent_weekend_off_summary["pes_pese_hafta_sonu_off_ok"] = (
    agent_weekend_off_summary["toplam_pes_pese_hafta_sonu_off"] >= 1
)


# -------------------------------------------------
# 13) Coverage / buffer tablosu
# -------------------------------------------------

coverage_rows = []

for ds in PLAN_GUNLER:
    ds_str = str(ds)

    for v in gun_vardiyalari.get(ds, []):
        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        req = int(talep[(ds, v)])

        coverage_rows.append({
            "tarih": ds_str,
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "weekday": pd.to_datetime(ds).weekday(),
            "hafta_ici": pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": req,
            "lower_10pct": coverage_lower[(ds, v)],
            "upper_10pct": coverage_upper[(ds, v)],
            "atanan": assigned,
            "gap": assigned - req,
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "buffer_ici": coverage_lower[(ds, v)] <= assigned <= coverage_upper[(ds, v)]
        })

coverage_for_excel = pd.DataFrame(coverage_rows).sort_values(["tarih", "baslangic"])


# -------------------------------------------------
# 14) Takım-tarih kontrol tablosu
# -------------------------------------------------

team_date_check = (
    agent_roster_full
    .groupby(["takim", "tarih", "gun", "weekday", "hafta_ici", "hafta"], as_index=False)
    .agg(
        toplam_agent=("agent_user_code", "nunique"),
        calisan_agent=("durum", lambda x: (x == "WORK").sum()),
        off_agent=("durum", lambda x: (x == "OFF").sum()),
        izinli_agent=("durum_detay", lambda x: (x == "OFF_IZIN").sum()),
        calisilan_vardiya_sayisi=("vardiya", "nunique")
    )
)

# Hafta içi takım bölünmemeli; hafta sonu serbest olduğu için OK kabul ediyoruz.
team_date_check["takim_butunlugu_ok"] = np.where(
    team_date_check["hafta_ici"],
    team_date_check["calisilan_vardiya_sayisi"].le(1),
    True
)

team_date_check["hafta_sonu_serbest"] = ~team_date_check["hafta_ici"]


# -------------------------------------------------
# 15) Agent calendar görünümü
# -------------------------------------------------

agent_roster_full["vardiya_gosterim"] = np.where(
    agent_roster_full["durum"] == "WORK",
    agent_roster_full["vardiya"].astype(str)
    + " | "
    + agent_roster_full["baslangic"].astype(str)
    + "-"
    + agent_roster_full["bitis"].astype(str),
    agent_roster_full["durum_detay"]
)

agent_calendar = (
    agent_roster_full
    .pivot_table(
        index=[
            "agent_user_code",
            "agent_name",
            "takim",
            "teamleader_name"
        ],
        columns="tarih",
        values="vardiya_gosterim",
        aggfunc="first"
    )
    .reset_index()
)

agent_calendar.columns.name = None


# -------------------------------------------------
# 16) Agent aylık özet
# -------------------------------------------------

agent_month_summary = (
    agent_roster_full
    .groupby(
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "teamleader_name",
            "working_main_group",
            "line_based_main_group",
            "sabah_calisir_flg",
            "mesaiye_kalamaz_flg",
            "hamile_flg",
            "sut_izni_flg"
        ],
        as_index=False
    )
    .agg(
        toplam_calisilan_gun=("durum", lambda x: (x == "WORK").sum()),
        toplam_off_gun=("durum", lambda x: (x == "OFF").sum()),
        toplam_izinli_gun=("durum_detay", lambda x: (x == "OFF_IZIN").sum()),
        base_vardiya_ihlali=("base_vardiya_ok", lambda x: (~x).sum()),
        dinlenme_11_saat_ihlali=("dinlenme_11_saat_ok", lambda x: (~x).sum()),
        sabah_calisir_ihlali=("sabah_calisir_ok", lambda x: (~x).sum()),
        hamile_sut_hafta_sonu_ihlali=("hamile_sut_hafta_sonu_ok", lambda x: (~x).sum()),
        izin_ihlali=("izin_ok", lambda x: (~x).sum())
    )
)

agent_month_summary = agent_month_summary.merge(
    streak_check,
    on="agent_user_code",
    how="left"
)

monthly_overtime = (
    agent_week_check
    .groupby("agent_user_code", as_index=False)
    .agg(
        toplam_mesai=("overtime_week", "sum"),
        haftalik_calisma_ihlali=("haftalik_calisma_ok", lambda x: (~x).sum()),
        mesaiye_kalamaz_mesai_ihlali=("mesaiye_kalamaz_mesai_ok", lambda x: (~x).sum())
    )
)

agent_month_summary = agent_month_summary.merge(
    monthly_overtime,
    on="agent_user_code",
    how="left"
)

agent_month_summary = agent_month_summary.merge(
    agent_weekend_off_summary,
    on="agent_user_code",
    how="left"
)

agent_month_summary["aylik_max_2_mesai_ok"] = agent_month_summary["toplam_mesai"].le(2)

agent_month_summary["genel_ok"] = (
    (agent_month_summary["base_vardiya_ihlali"] == 0) &
    (agent_month_summary["dinlenme_11_saat_ihlali"] == 0) &
    (agent_month_summary["sabah_calisir_ihlali"] == 0) &
    (agent_month_summary["hamile_sut_hafta_sonu_ihlali"] == 0) &
    (agent_month_summary["izin_ihlali"] == 0) &
    (agent_month_summary["max_6_gun_ok"] == True) &
    (agent_month_summary["haftalik_calisma_ihlali"] == 0) &
    (agent_month_summary["mesaiye_kalamaz_mesai_ihlali"] == 0) &
    (agent_month_summary["aylik_max_2_mesai_ok"] == True) &
    (agent_month_summary["pes_pese_hafta_sonu_off_ok"] == True)
)


# -------------------------------------------------
# 17) Özet sheet
# -------------------------------------------------

summary_rows = []

summary_rows.append({
    "kontrol": "solver_objective",
    "deger": solver.ObjectiveValue()
})

summary_rows.append({
    "kontrol": "solver_best_bound",
    "deger": solver.BestObjectiveBound()
})

summary_rows.append({
    "kontrol": "toplam_under_buffer",
    "deger": coverage_for_excel["under_buffer"].sum()
})

summary_rows.append({
    "kontrol": "toplam_over_buffer",
    "deger": coverage_for_excel["over_buffer"].sum()
})

summary_rows.append({
    "kontrol": "toplam_mesai",
    "deger": agent_month_summary["toplam_mesai"].sum()
})

summary_rows.append({
    "kontrol": "mesai_yapan_agent_sayisi",
    "deger": (agent_month_summary["toplam_mesai"] > 0).sum()
})

summary_rows.append({
    "kontrol": "hafta_ici_bolunen_takim_gun",
    "deger": len(team_date_check[
        (team_date_check["hafta_ici"]) &
        (team_date_check["calisilan_vardiya_sayisi"] > 1)
    ])
})

summary_rows.append({
    "kontrol": "pes_pese_hafta_sonu_off_almayan_agent",
    "deger": len(agent_weekend_off_summary[
        agent_weekend_off_summary["pes_pese_hafta_sonu_off_ok"] == False
    ])
})

summary_rows.append({
    "kontrol": "genel_ok_false_agent",
    "deger": len(agent_month_summary[agent_month_summary["genel_ok"] == False])
})

summary_df = pd.DataFrame(summary_rows)


# -------------------------------------------------
# 18) Excel'e yaz
# -------------------------------------------------

output_path = "vardiya_final_kisi_bazli_kontrol.xlsx"

with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
    summary_df.to_excel(writer, sheet_name="00_summary", index=False)
    agent_roster_full.to_excel(writer, sheet_name="01_agent_day_detail", index=False)
    agent_calendar.to_excel(writer, sheet_name="02_agent_calendar", index=False)
    agent_month_summary.to_excel(writer, sheet_name="03_agent_month_summary", index=False)
    agent_week_check.to_excel(writer, sheet_name="04_agent_week_check", index=False)
    coverage_for_excel.to_excel(writer, sheet_name="05_coverage_buffer", index=False)
    team_date_check.to_excel(writer, sheet_name="06_team_date_check", index=False)
    team_base_df.to_excel(writer, sheet_name="07_team_base", index=False)
    weekend_off_check.to_excel(writer, sheet_name="08_weekend_pair_off", index=False)
    agent_weekend_off_summary.to_excel(writer, sheet_name="09_weekend_off_summary", index=False)

    workbook = writer.book

    header_fmt = workbook.add_format({
        "bold": True,
        "bg_color": "#D9EAF7",
        "border": 1
    })

    bad_fmt = workbook.add_format({
        "bg_color": "#FFC7CE"
    })

    ok_fmt = workbook.add_format({
        "bg_color": "#C6EFCE"
    })

    sheets = {
        "00_summary": summary_df,
        "01_agent_day_detail": agent_roster_full,
        "02_agent_calendar": agent_calendar,
        "03_agent_month_summary": agent_month_summary,
        "04_agent_week_check": agent_week_check,
        "05_coverage_buffer": coverage_for_excel,
        "06_team_date_check": team_date_check,
        "07_team_base": team_base_df,
        "08_weekend_pair_off": weekend_off_check,
        "09_weekend_off_summary": agent_weekend_off_summary
    }

    for sheet_name, df in sheets.items():
        ws = writer.sheets[sheet_name]

        for col_num, value in enumerate(df.columns):
            ws.write(0, col_num, value, header_fmt)

        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)

        for i, col in enumerate(df.columns):
            width = min(max(len(str(col)) + 2, 12), 35)
            ws.set_column(i, i, width)

    # Boolean / OK kolonlarını renklendir
    for sheet_name, df in sheets.items():
        ws = writer.sheets[sheet_name]

        for col_name in df.columns:
            if (
                col_name.endswith("_ok")
                or col_name in [
                    "genel_ok",
                    "buffer_ici",
                    "hafta_ici",
                    "hafta_sonu_serbest",
                    "both_off"
                ]
            ):
                col_idx = df.columns.get_loc(col_name)

                ws.conditional_format(
                    1,
                    col_idx,
                    len(df),
                    col_idx,
                    {
                        "type": "cell",
                        "criteria": "==",
                        "value": False,
                        "format": bad_fmt
                    }
                )

                ws.conditional_format(
                    1,
                    col_idx,
                    len(df),
                    col_idx,
                    {
                        "type": "cell",
                        "criteria": "==",
                        "value": True,
                        "format": ok_fmt
                    }
                )

print("Excel oluşturuldu:", output_path)

print("\nÖZET")
display(summary_df)
