import pandas as pd

data_path = r"D:\ecommerce\data\row\UserBehavior.csv"

cols = ["user_id", "item_id", "category_id", "behavior_type", "timestamp"]

df = pd.read_csv(
    data_path,
    names=cols,
    header=None,
    nrows=1_000_000
)

print(df.shape)
print(df.head())
print(df["behavior_type"].value_counts())

# 去重
df = df.drop_duplicates()

# 缺失值检查
missing = df.isna().sum()

# 类型转换
df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp"])
df["timestamp"] = df["timestamp"].astype("int64")

# 时间字段拆分
df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
df["date"] = df["datetime"].dt.date
df["hour"] = df["datetime"].dt.hour
df["weekday"] = df["datetime"].dt.day_name()

# 行为类型过滤
valid_behaviors = ["pv", "fav", "cart", "buy"]
df = df[df["behavior_type"].isin(valid_behaviors)]

#输出清洗后数据.
df.to_csv("data/processed/user_behavior_cleaned_sample.csv", index=False)