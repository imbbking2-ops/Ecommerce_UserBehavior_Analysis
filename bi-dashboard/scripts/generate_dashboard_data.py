import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "user_behavior_cleaned.csv"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "app" / "dashboard-data.json"

BEHAVIOR_ORDER = ["pv", "fav", "cart", "buy"]
BEHAVIOR_LABELS = {
    "pv": "浏览",
    "fav": "收藏",
    "cart": "加购",
    "buy": "购买",
}


def records(frame):
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def main():
    usecols = [
        "user_id",
        "item_id",
        "category_id",
        "behavior_type",
        "datetime",
        "date",
        "hour",
    ]
    df = pd.read_csv(
        DATA_PATH,
        usecols=usecols,
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
    # 与项目的核心分析窗口保持一致，并排除源数据中的异常日期。
    df = df[
        (df["datetime"] >= "2017-11-25")
        & (df["datetime"] < "2017-12-04")
    ].copy()

    behavior_counts = (
        df["behavior_type"]
        .value_counts()
        .reindex(BEHAVIOR_ORDER, fill_value=0)
    )
    behavior_distribution = [
        {
            "behavior": behavior,
            "label": BEHAVIOR_LABELS[behavior],
            "count": int(behavior_counts[behavior]),
            "ratio": round(float(behavior_counts[behavior] / len(df) * 100), 2),
        }
        for behavior in BEHAVIOR_ORDER
    ]

    daily = (
        df.groupby("date", observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
        )
        .reset_index()
    )
    daily_behavior = (
        df.pivot_table(
            index="date",
            columns="behavior_type",
            values="user_id",
            aggfunc="count",
            fill_value=0,
            observed=True,
        )
        .reindex(columns=BEHAVIOR_ORDER, fill_value=0)
        .reset_index()
    )
    daily = daily.merge(daily_behavior, on="date", how="left")

    hourly = (
        df.groupby("hour", observed=True)
        .agg(event_count=("user_id", "size"), uv=("user_id", "nunique"))
        .reset_index()
    )
    hourly_behavior = (
        df.pivot_table(
            index="hour",
            columns="behavior_type",
            values="user_id",
            aggfunc="count",
            fill_value=0,
            observed=True,
        )
        .reindex(columns=BEHAVIOR_ORDER, fill_value=0)
        .reset_index()
    )
    hourly = hourly.merge(hourly_behavior, on="hour", how="left")

    buy_df = df[df["behavior_type"] == "buy"]
    last_buy = (
        buy_df.groupby(["user_id", "item_id"], observed=True)["datetime"]
        .max()
        .rename("last_buy_datetime")
        .reset_index()
    )
    source_df = df[df["behavior_type"].isin(["pv", "fav", "cart"])][
        ["user_id", "item_id", "behavior_type", "datetime"]
    ]
    source_df = source_df.merge(
        last_buy,
        on=["user_id", "item_id"],
        how="left",
    )
    source_df["converted"] = (
        source_df["last_buy_datetime"] > source_df["datetime"]
    )
    conversion = (
        source_df.groupby("behavior_type", observed=True)
        .agg(
            total=("converted", "size"),
            converted=("converted", "sum"),
        )
        .reindex(["pv", "fav", "cart"])
        .reset_index()
    )
    conversion["rate"] = (
        conversion["converted"] / conversion["total"] * 100
    ).round(2)
    conversion["label"] = conversion["behavior_type"].map(BEHAVIOR_LABELS)

    user_buy_counts = buy_df.groupby("user_id", observed=True).size()
    paying_users = int(user_buy_counts.size)
    repeat_buy_users = int((user_buy_counts >= 2).sum())

    top_item_ids = (
        df.groupby("item_id", observed=True)
        .size()
        .nlargest(10)
        .index
    )
    top_items_df = df[df["item_id"].isin(top_item_ids)]
    top_items = (
        top_items_df.groupby("item_id", observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
            category_id=("category_id", "first"),
        )
        .reset_index()
    )
    top_item_behavior = (
        top_items_df.pivot_table(
            index="item_id",
            columns="behavior_type",
            values="user_id",
            aggfunc="count",
            fill_value=0,
            observed=True,
        )
        .reindex(columns=BEHAVIOR_ORDER, fill_value=0)
        .reset_index()
    )
    top_items = (
        top_items.merge(top_item_behavior, on="item_id", how="left")
        .sort_values("event_count", ascending=False)
    )

    top_item_daily = (
        top_items_df.groupby(["item_id", "date"], observed=True)
        .agg(
            event_count=("user_id", "size"),
            pv=("behavior_type", lambda x: int((x == "pv").sum())),
            uv=("user_id", "nunique"),
            buy=("behavior_type", lambda x: int((x == "buy").sum())),
        )
        .reset_index()
    )
    top_item_hourly = (
        top_items_df.groupby(["item_id", "hour"], observed=True)
        .agg(
            event_count=("user_id", "size"),
            pv=("behavior_type", lambda x: int((x == "pv").sum())),
            uv=("user_id", "nunique"),
            buy=("behavior_type", lambda x: int((x == "buy").sum())),
        )
        .reset_index()
    )

    category = (
        df.groupby("category_id", observed=True)
        .agg(
            event_count=("user_id", "size"),
            uv=("user_id", "nunique"),
            item_count=("item_id", "nunique"),
        )
        .nlargest(10, "event_count")
        .reset_index()
    )

    output = {
        "generatedAt": pd.Timestamp.now().isoformat(),
        "dateRange": {
            "start": str(df["date"].min()),
            "end": str(df["date"].max()),
        },
        "overview": {
            "totalEvents": int(len(df)),
            "totalUsers": int(df["user_id"].nunique()),
            "totalItems": int(df["item_id"].nunique()),
            "totalCategories": int(df["category_id"].nunique()),
            "buyEvents": int(behavior_counts["buy"]),
            "payingUsers": paying_users,
            "repeatBuyUsers": repeat_buy_users,
            "repeatBuyRate": round(
                repeat_buy_users / paying_users * 100 if paying_users else 0,
                2,
            ),
        },
        "behaviorDistribution": behavior_distribution,
        "daily": records(daily),
        "hourly": records(hourly),
        "conversion": records(conversion),
        "topItems": records(top_items),
        "topItemDaily": records(top_item_daily),
        "topItemHourly": records(top_item_hourly),
        "topCategories": records(category),
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
