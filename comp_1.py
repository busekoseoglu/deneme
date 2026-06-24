# %% [DEBUG] - WEEK_KEY HANGİ TARİHLERE DENK GELİYOR?

week_map = []

for ds in PLAN_GUNLER:
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    
    week_map.append({
        "tarih": ds,
        "gun_adi": d.day_name(),
        "week_key": f"{iso.year}-W{str(iso.week).zfill(2)}"
    })

week_map_df = pd.DataFrame(week_map)

display(
    week_map_df
    .groupby("week_key")
    .agg(
        start_date=("tarih", "min"),
        end_date=("tarih", "max"),
        gun_sayisi=("tarih", "count"),
        tarihler=("tarih", lambda x: list(x))
    )
    .reset_index()
)
