# Partial week debug kolonları
    "partial_week": False,
    "partial_type": (
        week_boundary_df
        .loc[week_boundary_df["week"] == wk, "partial_type"]
        .iloc[0]
        if "week_boundary_df" in globals()
        and len(week_boundary_df.loc[week_boundary_df["week"] == wk]) > 0
        else None
    ),
    "partial_week_reason": None,
