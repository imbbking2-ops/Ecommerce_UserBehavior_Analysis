import pandas as pd

data_path = r"D:\ecommerce\data\processed\user_behavior_cleaned_sample.csv"

df = pd.read_csv(data_path)

df["datetime"] = pd.to_datetime(df["datetime"])
df["date"] = pd.to_datetime(df["date"]).dt.date

feature_start = "2017-11-25"
feature_end = "2017-12-02"
label_date = "2017-12-03"

feature_df = df[
    (df["datetime"] >= feature_start) &
    (df["datetime"] < label_date)
]

label_df = df[
    (df["date"].astype(str) == label_date) &
    (df["behavior_type"] == "buy")
][["user_id", "item_id"]].drop_duplicates()


### 7.3 特征工程


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

# 最近一次行为距离标签日的小时数
last_behavior = feature_df.groupby(["user_id", "item_id"])["datetime"].max().reset_index()
last_behavior["hours_since_last_behavior"] = (
    pd.to_datetime(label_date) - last_behavior["datetime"]
).dt.total_seconds() / 3600

features = features.merge(
    last_behavior[["user_id", "item_id", "hours_since_last_behavior"]],
    on=["user_id", "item_id"],
    how="left"
)

# 添加标签
label_df["label"] = 1
dataset = features.merge(label_df, on=["user_id", "item_id"], how="left")
dataset["label"] = dataset["label"].fillna(0).astype(int)


### 7.4 模型训练


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