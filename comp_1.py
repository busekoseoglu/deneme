# =================================================
# 13) AGENT AYLIK ÖZET - SADE
# =================================================
# Her agent için günler tek kategoriye ayrılır:
# WORK -> normal çalışma
# NORMAL_MESAI -> normal mesai
# ARIFE_09_13 / ARIFE_MESAI -> arife günü
# RESMI_TATIL_MESAI / RESMI_TATIL_KISITLI_IHLAL -> resmi tatil günü
# OFF -> off
# İZİN -> izin
#
# Toplam = normal çalışma + normal mesai + arife + resmi tatil + off + izin
# Haziran için toplam 30 olmalı.

agent_monthly_base = agent_day_plan_df.copy()

def monthly_status_group(status):
    status = str(status).strip()

    if status == "WORK":
        return "normal_calisma_gun"

    if status == "NORMAL_MESAI":
        return "normal_mesai_gun"

    if status in ["ARIFE_09_13", "ARIFE_MESAI"]:
        return "arife_gun"

    if status in ["RESMI_TATIL_MESAI", "RESMI_TATIL_KISITLI_IHLAL"]:
        return "resmi_tatil_gun"

    if status == "OFF":
        return "off_gun"

    if status == "İZİN":
        return "izin_gun"

    return "diger_gun"


agent_monthly_base["aylik_kategori"] = agent_monthly_base["status"].apply(monthly_status_group)

agent_monthly_counts = (
    agent_monthly_base
    .pivot_table(
        index=["agent_user_code", "agent_name", "takim", "teamleader_name"],
        columns="aylik_kategori",
        values="date",
        aggfunc="count",
        fill_value=0
    )
    .reset_index()
)

agent_monthly_counts.columns = [str(c) for c in agent_monthly_counts.columns]

required_monthly_cols = [
    "normal_calisma_gun",
    "normal_mesai_gun",
    "arife_gun",
    "resmi_tatil_gun",
    "off_gun",
    "izin_gun",
    "diger_gun",
]

for col in required_monthly_cols:
    if col not in agent_monthly_counts.columns:
        agent_monthly_counts[col] = 0

agent_monthly_counts["toplam_gun"] = (
    agent_monthly_counts["normal_calisma_gun"]
    + agent_monthly_counts["normal_mesai_gun"]
    + agent_monthly_counts["arife_gun"]
    + agent_monthly_counts["resmi_tatil_gun"]
    + agent_monthly_counts["off_gun"]
    + agent_monthly_counts["izin_gun"]
    + agent_monthly_counts["diger_gun"]
)

agent_monthly_counts["toplam_30_mu"] = agent_monthly_counts["toplam_gun"] == len(PLAN_GUNLER)

agent_monthly_df = agent_monthly_counts[
    [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "normal_calisma_gun",
        "normal_mesai_gun",
        "arife_gun",
        "resmi_tatil_gun",
        "off_gun",
        "izin_gun",
        "diger_gun",
        "toplam_gun",
        "toplam_30_mu",
    ]
].copy()

agent_monthly_df = agent_monthly_df.sort_values(
    ["takim", "teamleader_name", "agent_user_code"]
)


{"metric": "Aylık özette toplam günü 30 olmayan agent", "value": (agent_monthly_df["toplam_30_mu"] == False).sum()},
{"metric": "Aylık özette diger_gun toplam", "value": agent_monthly_df["diger_gun"].sum()},