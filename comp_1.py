# %% EXCEL - KİŞİ BAZLI KONTROL DOSYASI

import pandas as pd
import numpy as np

# -------------------------------------------------
# 1) Agent bilgilerini roster'a ekle
# -------------------------------------------------

agent_cols = [
    "agent_user_code",
    "agent_name",
    "teamleader_name",
    "working_main_group",
    "line_based_main_group",
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]

agent_info = df_tam[agent_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

for c in [
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]:
    agent_info[c] = pd.to_numeric(agent_info[c], errors="coerce").fillna(0).astype(int)


agent_roster = roster_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

# Team base vardiya bilgisini ekle
agent_roster = agent_roster.merge(
    team_base_df,
    on=["takim", "hafta"],
    how="left"
)

agent_roster["base_vardiya_ok"] = agent_roster["vardiya"].eq(agent_roster["base_vardiya"])

agent_roster["tarih_dt"] = pd.to_datetime(agent_roster["tarih"])
agent_roster = agent_roster.sort_values(["agent_user_code", "tarih_dt"])


# -------------------------------------------------
# 2) 11 saat dinlenme kişi bazlı kontrol
# -------------------------------------------------

def shift_start_end(tarih, baslangic, bitis):
    start_dt = pd.to_datetime(f"{tarih} {baslangic}")
    end_dt = pd.to_datetime(f"{tarih} {bitis}")

    if end_dt <= start_dt:
        end_dt += pd.Timedelta(days=1)

    return start_dt, end_dt


agent_roster[["start_dt", "end_dt"]] = agent_roster.apply(
    lambda r: pd.Series(shift_start_end(r["tarih"], r["baslangic"], r["bitis"])),
    axis=1
)

agent_roster["next_tarih"] = agent_roster.groupby("agent_user_code")["tarih"].shift(-1)
agent_roster["next_vardiya"] = agent_roster.groupby("agent_user_code")["vardiya"].shift(-1)
agent_roster["next_start_dt"] = agent_roster.groupby("agent_user_code")["start_dt"].shift(-1)

agent_roster["dinlenme_saat"] = (
    (agent_roster["next_start_dt"] - agent_roster["end_dt"])
    .dt.total_seconds() / 3600
)

agent_roster["dinlenme_11_saat_ok"] = (
    agent_roster["dinlenme_saat"].isna() |
    (agent_roster["dinlenme_saat"] >= 11)
)


# -------------------------------------------------
# 3) Özel kural kontrolleri
# -------------------------------------------------

def dk(t):
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)


agent_roster["bas_dk"] = agent_roster["baslangic"].apply(dk)
agent_roster["bit_dk"] = agent_roster["bitis"].apply(dk)

# Gece dönen vardiya
agent_roster.loc[
    agent_roster["bit_dk"] <= agent_roster["bas_dk"],
    "bit_dk"
] += 24 * 60

# Sabah çalışır 20:00 sonrası çalışamaz
agent_roster["sabah_calisir_ok"] = ~(
    (agent_roster["sabah_calisir_flg"] == 1) &
    (agent_roster["bit_dk"] > dk("20:00"))
)

# Hamile / süt izni hafta sonu çalışamaz
agent_roster["hafta_sonu"] = agent_roster["tarih_dt"].dt.weekday.isin([5, 6])

agent_roster["hamile_sut_hafta_sonu_ok"] = ~(
    (
        (agent_roster["hamile_flg"] == 1) |
        (agent_roster["sut_izni_flg"] == 1)
    ) &
    (agent_roster["hafta_sonu"])
)

# İzinli günde çalışma kontrolü
agent_roster["izinli_gunde_calisma"] = agent_roster.apply(
    lambda r: pd.to_datetime(r["tarih"]).date() in izin_map.get(r["agent_user_code"], set()),
    axis=1
)

agent_roster["izin_ok"] = ~agent_roster["izinli_gunde_calisma"]


# -------------------------------------------------
# 4) Agent-hafta 5 gün kontrolü
# -------------------------------------------------

agent_week_check = (
    agent_roster
    .groupby(
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "teamleader_name",
            "hafta"
        ],
        as_index=False
    )
    .agg(
        calisilan_gun=("tarih", "nunique"),
        vardiya_sayisi=("vardiya", "count")
    )
)

agent_week_check["haftada_5_gun_ok"] = agent_week_check["calisilan_gun"].eq(5)


# -------------------------------------------------
# 5) Max 6 gün üst üste çalışma kontrolü
# -------------------------------------------------

streak_rows = []

for a, grp in agent_roster.groupby("agent_user_code"):
    grp = grp.sort_values("tarih_dt")
    dates = grp["tarih_dt"].dt.date.tolist()

    max_streak = 0
    current_streak = 0
    prev_date = None

    for d in dates:
        if prev_date is None:
            current_streak = 1
        elif (d - prev_date).days == 1:
            current_streak += 1
        else:
            current_streak = 1

        max_streak = max(max_streak, current_streak)
        prev_date = d

    streak_rows.append({
        "agent_user_code": a,
        "max_ust_uste_gun": max_streak,
        "max_6_gun_ok": max_streak <= 6
    })

streak_check = pd.DataFrame(streak_rows)


# -------------------------------------------------
# 6) Agent aylık özet
# -------------------------------------------------

agent_month_summary = (
    agent_roster
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
        toplam_calisilan_gun=("tarih", "nunique"),
        toplam_vardiya=("vardiya", "count"),
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

agent_month_summary["genel_ok"] = (
    (agent_month_summary["base_vardiya_ihlali"] == 0) &
    (agent_month_summary["dinlenme_11_saat_ihlali"] == 0) &
    (agent_month_summary["sabah_calisir_ihlali"] == 0) &
    (agent_month_summary["hamile_sut_hafta_sonu_ihlali"] == 0) &
    (agent_month_summary["izin_ihlali"] == 0) &
    (agent_month_summary["max_6_gun_ok"] == True)
)


# -------------------------------------------------
# 7) Agent takvim görünümü
# -------------------------------------------------

calendar_tmp = agent_roster.copy()

calendar_tmp["vardiya_gosterim"] = (
    calendar_tmp["vardiya"].astype(str)
    + " | "
    + calendar_tmp["baslangic"].astype(str)
    + "-"
    + calendar_tmp["bitis"].astype(str)
)

agent_calendar = (
    calendar_tmp
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
# 8) Coverage tablosunu kişi kontrol dosyasına eklemek için sadeleştir
# -------------------------------------------------

coverage_for_excel = coverage_df.copy()

coverage_for_excel = coverage_for_excel[
    [
        "tarih",
        "gun",
        "hafta",
        "vardiya",
        "baslangic",
        "bitis",
        "talep",
        "lower_10pct",
        "upper_10pct",
        "atanan",
        "gap",
        "under_buffer",
        "over_buffer",
        "buffer_ici"
    ]
].sort_values(["tarih", "baslangic"])


# -------------------------------------------------
# 9) Excel'e yaz
# -------------------------------------------------

output_path = "vardiya_kisi_bazli_kontrol.xlsx"

with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
    agent_roster.to_excel(writer, sheet_name="01_agent_roster_detail", index=False)
    agent_month_summary.to_excel(writer, sheet_name="02_agent_month_summary", index=False)
    agent_week_check.to_excel(writer, sheet_name="03_agent_week_check", index=False)
    agent_calendar.to_excel(writer, sheet_name="04_agent_calendar", index=False)
    coverage_for_excel.to_excel(writer, sheet_name="05_coverage_buffer", index=False)
    team_base_df.to_excel(writer, sheet_name="06_team_base", index=False)

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

    # Basit format
    for sheet_name, df in {
        "01_agent_roster_detail": agent_roster,
        "02_agent_month_summary": agent_month_summary,
        "03_agent_week_check": agent_week_check,
        "04_agent_calendar": agent_calendar,
        "05_coverage_buffer": coverage_for_excel,
        "06_team_base": team_base_df
    }.items():
        ws = writer.sheets[sheet_name]

        for col_num, value in enumerate(df.columns):
            ws.write(0, col_num, value, header_fmt)

        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)

        for i, col in enumerate(df.columns):
            width = min(max(len(str(col)) + 2, 12), 35)
            ws.set_column(i, i, width)

    # Boolean kontrol kolonlarını renklendir
    for sheet_name, df in {
        "01_agent_roster_detail": agent_roster,
        "02_agent_month_summary": agent_month_summary,
        "03_agent_week_check": agent_week_check,
        "05_coverage_buffer": coverage_for_excel
    }.items():
        ws = writer.sheets[sheet_name]

        for col_name in df.columns:
            if col_name.endswith("_ok") or col_name in ["genel_ok", "buffer_ici", "base_vardiya_ok"]:
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
