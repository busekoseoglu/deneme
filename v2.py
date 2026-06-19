import pandas as pd
import re


def clean_col_name(col):
    """
    Kolon isimlerini standartlaştırır.
    Örn:
    'Agent User ID' -> 'agent_user_id'
    'süt izni flg' -> 'sut_izni_flg'
    """
    col = str(col).strip().lower()

    tr_map = str.maketrans({
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c"
    })

    col = col.translate(tr_map)
    col = re.sub(r"\s+", "_", col)
    col = re.sub(r"[^a-z0-9_]", "", col)

    return col


def normalize_columns(df):
    df = df.copy()
    df.columns = [clean_col_name(c) for c in df.columns]
    return df


def prepare_employee_data_for_ortools(employee_df):
    """
    Raw employee datasını modelin kullanacağı temiz employee tablosuna çevirir.
    """

    df = normalize_columns(employee_df)

    print("Normalize edilmiş employee kolonları:")
    print(df.columns.tolist())

    required_cols = [
        "agent_user_id",
        "agent_user_code",
        "agent_name",
        "teamleader_name",
        "working_main_group",
        "line_base_main_group",
        "idari_izinli_flg",
        "pazartesi_izinli_flg",
        "cuma_izinli_flg",
        "sabah_calisir_flg",
        "mesaiye_kalamaz_flg",
        "dogum_izni_flg",
        "hamile_flg",
        "sut_izni_flg",
        "kismi_calisan_flg"
    ]

    missing_cols = [c for c in required_cols if c not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Eksik kolonlar var: {missing_cols}\n"
            f"Mevcut kolonlar: {df.columns.tolist()}"
        )

    # ID ve isim alanları
    df["employee_id"] = df["agent_user_id"].astype(str).str.strip()
    df["employee_code"] = df["agent_user_code"].astype(str).str.strip()
    df["employee_name"] = df["agent_name"].astype(str).str.strip()

    # Team bilgisi
    df["team_id"] = (
        df["teamleader_name"]
        .fillna("no_team")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Lokasyon: working_main_group içinden alınır
    # Örn: gebze_kitle -> gebze
    df["location"] = (
        df["working_main_group"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.split("_")
        .str[0]
    )

    # Skill group: line_base_main_group
    # Örn: kitle, gold, kurumsal
    df["skill_group"] = (
        df["line_base_main_group"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Flag kolonlarını 0/1 integer yap
    flag_cols = [
        "idari_izinli_flg",
        "pazartesi_izinli_flg",
        "cuma_izinli_flg",
        "sabah_calisir_flg",
        "mesaiye_kalamaz_flg",
        "dogum_izni_flg",
        "hamile_flg",
        "sut_izni_flg",
        "kismi_calisan_flg"
    ]

    for col in flag_cols:
        df[col] = df[col].fillna(0).astype(int)

    # İlk etapta planlamaya almayacağımız kişiler
    exclude_flags = [
        "idari_izinli_flg",
        "dogum_izni_flg",
        "hamile_flg",
        "kismi_calisan_flg"
    ]

    df["is_plannable"] = 1

    for flag in exclude_flags:
        df.loc[df[flag] == 1, "is_plannable"] = 0

    clean_cols = [
        "employee_id",
        "employee_code",
        "employee_name",
        "team_id",
        "location",
        "skill_group",
        "pazartesi_izinli_flg",
        "cuma_izinli_flg",
        "sabah_calisir_flg",
        "mesaiye_kalamaz_flg",
        "sut_izni_flg",
        "is_plannable"
    ]

    employee_clean_df = df[clean_cols].copy()

    return employee_clean_df
