import pandas as pd
import re
import unicodedata


def clean_col_name(col):
    """
    Kolon isimlerini sadeleştirir:
    - küçük harfe çevirir
    - Türkçe karakterleri sadeleştirir
    - boşlukları _ yapar
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


def parse_shift_times(shift_value):
    start_time, end_time = str(shift_value).split("-")
    return start_time.strip(), end_time.strip()


def prepare_shift_data_for_ortools(shift_df):
    df = normalize_columns(shift_df)

    print("Normalize edilmiş kolonlar:")
    print(df.columns.tolist())

    # Beklenen kolonları kontrol et
    required_base_cols = ["tarih", "shift", "kitle_inhouse", "gold", "kurumsal"]

    missing_cols = [c for c in required_base_cols if c not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Eksik kolonlar var: {missing_cols}\n"
            f"Mevcut kolonlar: {df.columns.tolist()}"
        )

    df["date"] = pd.to_datetime(df["tarih"]).dt.date

    df[["shift_start", "shift_end"]] = df["shift"].apply(
        lambda x: pd.Series(parse_shift_times(x))
    )

    df["shift_start_dt"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["shift_start"]
    )

    df["shift_end_dt"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["shift_end"]
    )

    # Geceye sarkan vardiyalar için: 17:00-01:00 gibi
    df.loc[
        df["shift_end_dt"] <= df["shift_start_dt"],
        "shift_end_dt"
    ] = df["shift_end_dt"] + pd.Timedelta(days=1)

    df["duration_minutes"] = (
        (df["shift_end_dt"] - df["shift_start_dt"])
        .dt.total_seconds() // 60
    ).astype(int)

    df["shift_id"] = (
        df["date"].astype(str)
        + "_"
        + df["shift_start"]
        + "_"
        + df["shift_end"]
    )

    demand_columns = {
        "kitle_inhouse": "kitle",
        "gold": "gold",
        "kurumsal": "kurumsal"
    }

    rows = []

    for _, row in df.iterrows():
        for col_name, skill_group in demand_columns.items():
            required_count = int(row[col_name])

            if required_count > 0:
                rows.append({
                    "date": str(row["date"]),
                    "shift_id": row["shift_id"],
                    "shift_start": row["shift_start"],
                    "shift_end": row["shift_end"],
                    "shift_start_dt": row["shift_start_dt"],
                    "shift_end_dt": row["shift_end_dt"],
                    "duration_minutes": row["duration_minutes"],
                    "skill_group": skill_group,
                    "required_count": required_count
                })

    return pd.DataFrame(rows)
