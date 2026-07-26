import pandas as pd

data_path = r'D:\ecommerce\data\processed\user_behavior_cleaned_sample.csv'

df = pd.read_csv(data_path)

df["datetime"] = pd.to_datetime(df["datetime"])
df["date"] = pd.to_datetime(df["date"]).dt.date

feature_start = "2017-11-25"
feature_end = "2017-12-02"
label_date = "2017-12-03"
label_time = pd.Timestamp(label_date)

feature_df = df[
    (df["datetime"] >= feature_start) &
    (df["datetime"] < label_date)
]

label_df = df[
    (df["date"].astype(str) == label_date) &
    (df["behavior_type"] == "buy")
][["user_id", "item_id"]].drop_duplicates()
#7.3 特征工程
#以 user_id + item_id 为粒度构造特征：

features = feature_df.pivot_table(
    index=["user_id", "item_id"],
    columns="behavior_type",
    values="timestamp",
    aggfunc="count",
    fill_value=0
).reset_index()

features.columns.name = None

for col in ["pv", "fav", "cart", "buy"]:
    if col not in features.columns:
        features[col] = 0

# 分别统计标签日前1天、3天和7天内的各类行为次数
behavior_types = ["pv", "fav", "cart", "buy"]

for window_days in [1, 3, 7]:
    window_start = label_time - pd.Timedelta(days=window_days)
    window_df = feature_df[
        (feature_df["datetime"] >= window_start) &
        (feature_df["datetime"] < label_time)
    ]

    window_features = window_df.pivot_table(
        index=["user_id", "item_id"],
        columns="behavior_type",
        values="timestamp",
        aggfunc="count",
        fill_value=0
    ).reindex(columns=behavior_types, fill_value=0)

    window_features.columns = [
        f"{behavior}_count_{window_days}d"
        for behavior in window_features.columns
    ]
    window_features = window_features.reset_index()

    features = features.merge(
        window_features,
        on=["user_id", "item_id"],
        how="left"
    )

window_feature_cols = [
    f"{behavior}_count_{window_days}d"
    for window_days in [1, 3, 7]
    for behavior in behavior_types
]
features[window_feature_cols] = (
    features[window_feature_cols].fillna(0).astype("int32")
)

# 最近一次行为距离标签日的小时数
# 提取最后一次行为的发生时间和行为类型
last_behavior = (
    feature_df.sort_values(["user_id", "item_id", "datetime"])
    .groupby(["user_id", "item_id"], as_index=False)
    .tail(1)
    [["user_id", "item_id", "datetime", "behavior_type"]]
    .copy()
)

last_behavior["hours_since_last_behavior"] = (
    label_time - last_behavior["datetime"]
).dt.total_seconds() / 3600

# 随机森林需要数值输入：pv=1、fav=2、cart=3、buy=4
behavior_code = {"pv": 1, "fav": 2, "cart": 3, "buy": 4}
last_behavior["last_behavior_type"] = (
    last_behavior["behavior_type"].map(behavior_code).astype("int8")
)

features = features.merge(
    last_behavior[
        [
            "user_id",
            "item_id",
            "hours_since_last_behavior",
            "last_behavior_type"
        ]
    ],
    on=["user_id", "item_id"],
    how="left"
)

# 添加标签
label_df["label"] = 1
dataset = features.merge(label_df, on=["user_id", "item_id"], how="left")
dataset["label"] = dataset["label"].fillna(0).astype(int)
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.ensemble import RandomForestClassifier

X = dataset.drop(columns=["user_id", "item_id", "label"])
y = dataset["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,
    random_state=42,
    class_weight="balanced"
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred))
print("AUC:", roc_auc_score(y_test, y_proba))
