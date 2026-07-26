"""Generate Tableau-ready CSV data marts from the cleaned behavior data."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "user_behavior_cleaned.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"

ANALYSIS_START = pd.Timestamp("2017-11-25")
ANALYSIS_END = pd.Timestamp("2017-12-04")
BEHAVIOR_ORDER = ["pv", "fav", "cart", "buy"]


def export(frame: pd.DataFrame, filename: str) -> None:
    path = OUTPUT_DIR / filename
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"{filename}: {len(frame):,} rows")


def behavior_pivot(
    frame: pd.DataFrame,
    index: list[str],
) -> pd.DataFrame:
    result = (
        frame.pivot_table(
            index=index,
            columns="behavior_type",
            values="user_id",
            aggfunc="count",
            fill_value=0,
            observed=True,
        )
        .reindex(columns=BEHAVIOR_ORDER, fill_value=0)
        .reset_index()
    )
    result.columns.name = None
    return result


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        INPUT_PATH,
        usecols=[
            "user_id",
            "item_id",
            "category_id",
            "behavior_type",
            "datetime",
            "date",
            "hour",
        ],
        dtype={
            "user_id": "int64",
            "item_id": "int64",
            "category_id": "int64",
            "behavior_type": "category",
            "date": "string",
            "hour": "int8",
        },
    )
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df[
        (df["datetime"] >= ANALYSIS_START)
        & (df["datetime"] < ANALYSIS_END)
    ].copy()
    df["date"] = pd.to_datetime(df["date"])

    behavior_counts = (
        df["behavior_type"]
        .value_counts()
        .reindex(BEHAVIOR_ORDER, fill_value=0)
    )
    buy_df = df[df["behavior_type"] == "buy"].copy()
    user_buy_counts = buy_df.groupby("user_id", observed=True).size()
    paying_users = int(user_buy_counts.size)
    repeat_buy_users = int((user_buy_counts >= 2).sum())

    overview = pd.DataFrame(
        [
            {
                "analysis_start": ANALYSIS_START.date(),
                "analysis_end": (ANALYSIS_END - pd.Timedelta(days=1)).date(),
                "total_events": len(df),
                "total_users": df["user_id"].nunique(),
                "total_items": df["item_id"].nunique(),
                "total_categories": df["category_id"].nunique(),
                "buy_events": int(behavior_counts["buy"]),
                "paying_users": paying_users,
                "repeat_buy_users": repeat_buy_users,
                "repeat_buy_rate": (
                    repeat_buy_users / paying_users
                    if paying_users
                    else 0
                ),
            }
        ]
    )
    export(overview, "overview_kpis.csv")

    behavior_distribution = behavior_counts.rename("event_count").reset_index()
    behavior_distribution.columns = ["behavior_type", "event_count"]
    behavior_distribution["event_ratio"] = (
        behavior_distribution["event_count"] / len(df)
    )
    export(behavior_distribution, "behavior_distribution.csv")

    daily = (
        df.groupby("date", observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
            active_items=("item_id", "nunique"),
        )
        .reset_index()
        .merge(behavior_pivot(df, ["date"]), on="date", how="left")
    )
    export(daily, "daily_traffic.csv")

    hourly = (
        df.groupby("hour", observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
            active_items=("item_id", "nunique"),
        )
        .reset_index()
        .merge(behavior_pivot(df, ["hour"]), on="hour", how="left")
    )
    export(hourly, "hourly_traffic.csv")

    last_buy = (
        buy_df.groupby(["user_id", "item_id"], observed=True)["datetime"]
        .max()
        .rename("last_buy_datetime")
        .reset_index()
    )
    source = df[df["behavior_type"].isin(["pv", "fav", "cart"])][
        ["user_id", "item_id", "behavior_type", "datetime"]
    ].merge(
        last_buy,
        on=["user_id", "item_id"],
        how="left",
    )
    source["is_valid_conversion"] = (
        source["last_buy_datetime"] > source["datetime"]
    )
    conversion = (
        source.groupby("behavior_type", observed=True)
        .agg(
            total_behavior_count=("is_valid_conversion", "size"),
            valid_conversion_count=("is_valid_conversion", "sum"),
        )
        .reindex(["pv", "fav", "cart"])
        .reset_index()
    )
    conversion["conversion_to_buy_rate"] = (
        conversion["valid_conversion_count"]
        / conversion["total_behavior_count"]
    )
    conversion["funnel_order"] = [1, 2, 3]
    export(conversion, "conversion_funnel.csv")

    repeat_purchase = pd.DataFrame(
        [
            {
                "paying_users": paying_users,
                "repeat_buy_users": repeat_buy_users,
                "one_time_buyers": paying_users - repeat_buy_users,
                "repeat_buy_rate": (
                    repeat_buy_users / paying_users
                    if paying_users
                    else 0
                ),
            }
        ]
    )
    export(repeat_purchase, "repeat_purchase.csv")

    user_rf = (
        buy_df.groupby("user_id", observed=True)
        .agg(
            last_buy_date=("date", "max"),
            frequency=("user_id", "size"),
        )
        .reset_index()
    )
    user_rf["recency_days"] = (
        buy_df["date"].max() - user_rf["last_buy_date"]
    ).dt.days
    recency_median = user_rf["recency_days"].median()
    frequency_median = user_rf["frequency"].median()
    user_rf["r_score"] = (
        user_rf["recency_days"] <= recency_median
    ).astype(int) + 1
    user_rf["f_score"] = (
        user_rf["frequency"] >= frequency_median
    ).astype(int) + 1
    segment_map = {
        (2, 2): "高价值用户",
        (2, 1): "潜力用户",
        (1, 2): "重要召回用户",
        (1, 1): "一般/沉睡用户",
    }
    user_rf["segment"] = [
        segment_map[(r, f)]
        for r, f in zip(user_rf["r_score"], user_rf["f_score"])
    ]
    rf_segments = (
        user_rf.groupby(
            ["r_score", "f_score", "segment"],
            observed=True,
        )
        .agg(
            user_count=("user_id", "nunique"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
        )
        .reset_index()
    )
    export(rf_segments, "rf_segments.csv")

    activity = df[["user_id", "date"]].drop_duplicates()
    first_active = (
        activity.groupby("user_id", observed=True)["date"]
        .min()
        .rename("cohort_date")
        .reset_index()
    )
    retention = activity.merge(first_active, on="user_id", how="left")
    retention["day_number"] = (
        retention["date"] - retention["cohort_date"]
    ).dt.days
    cohort_size = (
        first_active.groupby("cohort_date", observed=True)["user_id"]
        .nunique()
        .rename("cohort_users")
        .reset_index()
    )
    retention = (
        retention.groupby(
            ["cohort_date", "day_number"],
            observed=True,
        )["user_id"]
        .nunique()
        .rename("retained_users")
        .reset_index()
        .merge(cohort_size, on="cohort_date", how="left")
    )
    retention["retention_rate"] = (
        retention["retained_users"] / retention["cohort_users"]
    )
    export(retention, "retention_cohort.csv")

    category = (
        df.groupby("category_id", observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
            item_count=("item_id", "nunique"),
        )
        .reset_index()
        .merge(
            behavior_pivot(df, ["category_id"]),
            on="category_id",
            how="left",
        )
    )
    category["buy_pv_rate"] = category["buy"] / category["pv"].where(
        category["pv"] > 0
    )
    category = category.nlargest(50, "event_count")
    export(category, "top_categories.csv")

    top_item_ids = (
        df.groupby("item_id", observed=True)
        .size()
        .nlargest(100)
        .index
    )
    top_items = df[df["item_id"].isin(top_item_ids)].copy()
    product_summary = (
        top_items.groupby("item_id", observed=True)
        .agg(
            category_id=("category_id", "first"),
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
        )
        .reset_index()
        .merge(
            behavior_pivot(top_items, ["item_id"]),
            on="item_id",
            how="left",
        )
    )
    product_summary["buy_pv_rate"] = (
        product_summary["buy"]
        / product_summary["pv"].where(product_summary["pv"] > 0)
    )
    export(product_summary, "top_products.csv")

    product_daily = (
        top_items.groupby(["item_id", "date"], observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
        )
        .reset_index()
        .merge(
            behavior_pivot(top_items, ["item_id", "date"]),
            on=["item_id", "date"],
            how="left",
        )
    )
    export(product_daily, "product_daily_traffic.csv")

    product_hourly = (
        top_items.groupby(["item_id", "hour"], observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
        )
        .reset_index()
        .merge(
            behavior_pivot(top_items, ["item_id", "hour"]),
            on=["item_id", "hour"],
            how="left",
        )
    )
    export(product_hourly, "product_hourly_traffic.csv")

    # A single, sparse analysis table simplifies Tableau workbook authoring.
    # Each worksheet filters record_type before using its relevant dimensions.
    master_frames = [
        overview.assign(record_type="overview"),
        behavior_distribution.assign(record_type="behavior"),
        daily.assign(record_type="daily"),
        hourly.assign(record_type="hourly"),
        conversion.assign(record_type="conversion"),
        repeat_purchase.assign(record_type="repeat_purchase"),
        rf_segments.assign(record_type="rf_segment"),
        retention.assign(record_type="retention"),
        category.assign(record_type="category"),
        product_summary.assign(record_type="product"),
        product_daily.assign(record_type="product_daily"),
        product_hourly.assign(record_type="product_hourly"),
    ]
    tableau_master = pd.concat(
        master_frames,
        ignore_index=True,
        sort=False,
    )
    first_column = ["record_type"]
    remaining_columns = [
        column
        for column in tableau_master.columns
        if column not in first_column
    ]
    tableau_master = tableau_master[first_column + remaining_columns]
    export(tableau_master, "tableau_master.csv")


if __name__ == "__main__":
    main()
