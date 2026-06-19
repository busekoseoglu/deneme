import pandas as pd


def normalize_columns(df):
    """
    Kolon isimlerini standart hale getirir.
    Örn:
    'kitle inhouse' -> 'kitle_inhouse'
    'INH Total' -> 'inh_total'
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def parse_shift_times(shift_value):
    """
    '07:00-16:00' gibi bir SHIFT değerini start ve end olarak böler.
    """
    start_time, end_time = str(shift_value).split("-")
    return start_time.strip(), end_time.strip()


def prepare_shift_data_for_ortools(shift_df):
    """
    Wide shift demand tablosunu OR-Tools için long formata çevirir.

    Input:
        TARIH
        SHIFT
        kitle inhouse
        gold
        kurumsal

    Output:
        date
        shift_id
        shift_start
        shift_end
        shift_start_dt
        shift_end_dt
        duration_minutes
        skill_group
        required_count
    """

    df = normalize_columns(shift_df)

    # Tarih formatı
    df["date"] = pd.to_datetime(df["tarih"]).dt.date

    # SHIFT kolonundan başlangıç ve bitiş saatlerini çıkar
    df[["shift_start", "shift_end"]] = df["shift"].apply(
        lambda x: pd.Series(parse_shift_times(x))
    )

    # Datetime başlangıç
    df["shift_start_dt"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["shift_start"]
    )

    # Datetime bitiş
    df["shift_end_dt"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["shift_end"]
    )

    # Geceye sarkan shiftler için:
    # Örn 17:00-01:00 ise end ertesi gün olmalı
    df.loc[
        df["shift_end_dt"] <= df["shift_start_dt"],
        "shift_end_dt"
    ] = df["shift_end_dt"] + pd.Timedelta(days=1)

    # Shift süresi
    df["duration_minutes"] = (
        (df["shift_end_dt"] - df["shift_start_dt"])
        .dt.total_seconds() // 60
    ).astype(int)

    # OR-Tools tarafında kullanacağımız unique shift id
    df["shift_id"] = (
        df["date"].astype(str)
        + "_"
        + df["shift_start"]
        + "_"
        + df["shift_end"]
    )

    # Sadece inhouse ilgilendiğimiz kolonlar
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

    shift_demand_long_df = pd.DataFrame(rows)

    return shift_demand_long_df