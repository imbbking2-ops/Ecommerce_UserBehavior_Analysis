# 淘宝电商用户行为分析与购买预测

本项目基于淘宝 `UserBehavior` 用户行为数据，完成从数据清洗、关系型数据库建模、SQL 指标分析、购买预测建模到 BI 可视化的完整分析链路。项目围绕浏览（PV）、收藏（Fav）、加购（Cart）和购买（Buy）行为，帮助业务理解用户如何从“产生兴趣”逐步走向“完成购买”。

> 在线看板：[Commerce Pulse｜电商用户行为 BI](https://commerce-pulse-bi.imbbking2.chatgpt.site)  
> 当前看板分析窗口：2017-11-25 至 2017-12-03

![Commerce Pulse BI 看板](docs/images/bi-dashboard.png)

## 目录

- [1. 项目背景](#1-项目背景)
- [2. 数据来源](#2-数据来源)
- [3. 技术栈](#3-技术栈)
- [4. 分析问题](#4-分析问题)
- [5. 数据清洗](#5-数据清洗)
- [6. SQL 分析](#6-sql-分析)
- [7. 机器学习建模](#7-机器学习建模)
- [8. BI 看板](#8-bi-看板)
- [9. 结论与业务建议](#9-结论与业务建议)
- [10. 项目结构与运行方式](#10-项目结构与运行方式)

## 1. 项目背景

电商平台每天会产生大量浏览、收藏、加购和购买记录。单纯查看销售额或订单量，只能看到已经发生的结果，无法解释用户为什么购买、为什么流失，以及哪些商品具有潜在增长机会。

用户行为分析可以帮助平台回答以下业务问题：

- 用户从浏览到购买经历了怎样的行为路径？
- 浏览、收藏、加购分别有多大概率转化为购买？
- 用户通常在哪些日期和时段更加活跃？
- 哪些商品和类目获得了较高关注，但购买转化仍然偏低？
- 哪些用户已经形成复购习惯，哪些用户需要召回？
- 能否利用用户近期行为预测其下一阶段可能购买的商品？

因此，本项目将描述性分析、诊断性分析和预测性分析结合起来，为流量运营、商品运营、用户运营和精准营销提供数据依据。

## 2. 数据来源

数据来自阿里云天池公开的[淘宝用户购物行为数据集](https://tianchi.aliyun.com/dataset/649)。原始 `UserBehavior.csv` 记录了匿名用户在淘宝商品上的行为，核心观察期为 **2017-11-25 至 2017-12-03**。

原始文件不包含表头，每一行表示一次用户行为：

| 字段 | 类型 | 说明 |
|---|---|---|
| `user_id` | BIGINT | 匿名用户 ID |
| `item_id` | BIGINT | 匿名商品 ID |
| `category_id` | BIGINT | 商品类目 ID |
| `behavior_type` | VARCHAR | 用户行为类型 |
| `timestamp` | BIGINT | Unix 时间戳，单位为秒 |

行为类型定义如下：

| 行为值 | 中文含义 | 业务解释 |
|---|---|---|
| `pv` | 浏览 | 用户查看商品详情页 |
| `fav` | 收藏 | 用户收藏商品 |
| `cart` | 加购 | 用户将商品加入购物车 |
| `buy` | 购买 | 用户完成购买 |

读取原始数据时为无表头 CSV 指定字段：

```python
import pandas as pd

data_path = r"data/row/UserBehavior.csv"
cols = [
    "user_id",
    "item_id",
    "category_id",
    "behavior_type",
    "timestamp",
]

df = pd.read_csv(
    data_path,
    names=cols,
    header=None,
    nrows=1_000_000,  # 本地开发时可先读取部分数据
)
```

> 数据规模说明：官方数据集规模较大。本项目的数据清洗脚本支持通过 `nrows` 生成开发样本；已发布 BI 看板使用当前项目清洗文件，并限制到 2017-11-25 至 2017-12-03。看板结果代表当前项目数据子集，不应直接外推为淘宝平台整体表现。

## 3. 技术栈

| 环节 | 技术 | 用途 |
|---|---|---|
| 数据处理 | Python、pandas | CSV 读取、清洗、时间处理、特征构造 |
| 数据存储 | PostgreSQL | 保存行为明细并执行聚合分析 |
| SQL 兼容 | MySQL | 可通过 `SUM(CASE WHEN ...)` 改写 PostgreSQL 的 `FILTER` |
| 机器学习 | scikit-learn | 数据切分、随机森林、交叉验证与模型评估 |
| BI 分析 | Power BI / Tableau | 连接 SQL 结果，构建业务分析页面 |
| Web BI | React、TypeScript | 项目内已实现的 Commerce Pulse 交互式看板 |
| 版本管理 | Git | 管理分析代码和看板代码 |

项目采用以下数据链路：

```text
UserBehavior.csv
        ↓
pandas 数据清洗
        ↓
清洗后的 CSV / PostgreSQL
        ↓
SQL 指标分析 ─────────→ BI 看板
        ↓
用户—商品特征工程
        ↓
随机森林购买预测
```

## 4. 分析问题

### 4.1 流量与活跃度

- 整体行为量、用户数、商品数和类目数是多少？
- DAU、PV、UV 和购买用户数如何随日期变化？
- 用户在一天中的哪些时段最活跃？
- 各商品的日流量和小时流量有何差异？

### 4.2 转化分析

- 浏览、收藏、加购到购买的有效转化率分别是多少？
- 哪种购买前行为代表更强的购买意愿？
- 哪些商品存在“高浏览、低购买”的转化损失？

本项目的有效转化定义为：

```text
同一用户 + 同一商品 + 购买时间晚于来源行为时间
```

事件级转化率定义为：

```text
行为到购买转化率
= 有效转化到购买的行为次数 / 该行为总次数 × 100%
```

### 4.3 留存与复购

- 用户在首次活跃后是否在后续日期再次访问？
- 次日留存率、3 日留存率和 7 日留存率分别是多少？
- 购买用户中有多少人发生了两次及以上购买？
- 高复购用户集中在哪些商品或类目？

### 4.4 用户分层

- 用户距离最近一次购买有多久？
- 用户购买频率如何？
- 如何利用 R（Recency）和 F（Frequency）划分高价值、潜力、沉睡和一般用户？

数据集没有订单金额，因此本项目采用 RF 分层，而不是完整的 RFM。

### 4.5 商品偏好

- 哪些商品和类目的浏览、收藏、加购、购买量最高？
- 哪些商品在特定日期或小时具有明显流量峰值？
- 哪些类目具有较高的购买/浏览比？

### 4.6 购买预测

- 用户是否会在标签日购买某件历史交互商品？
- 近期 1、3、7 天行为能否反映购买意图变化？
- 最后一次行为类型和距最后一次行为的时间是否有预测价值？

## 5. 数据清洗

数据清洗代码位于 [`data_cleaning.py`](data_cleaning.py)，主要处理重复记录、缺失值、异常时间戳、时间维度拆分和非法行为类型。

### 5.1 删除重复记录

重复行为会放大 PV、转化率和用户活跃度，因此先进行整行去重：

```python
df = df.drop_duplicates()
```

### 5.2 检查缺失值

```python
missing = df.isna().sum()
print(missing)
```

对于关键字段，推荐执行：

```python
required_cols = [
    "user_id",
    "item_id",
    "category_id",
    "behavior_type",
    "timestamp",
]

df = df.dropna(subset=required_cols)
```

不直接用均值或众数填补用户、商品和时间字段，因为这会人为制造不存在的行为。

### 5.3 时间戳转换

先将非法时间戳转成缺失值，再删除并转换为整数：

```python
df["timestamp"] = pd.to_numeric(
    df["timestamp"],
    errors="coerce",
)
df = df.dropna(subset=["timestamp"])
df["timestamp"] = df["timestamp"].astype("int64")
```

将 Unix 时间戳拆分为可分析的时间维度：

```python
df["datetime"] = pd.to_datetime(
    df["timestamp"],
    unit="s",
)
df["date"] = df["datetime"].dt.date
df["hour"] = df["datetime"].dt.hour
df["weekday"] = df["datetime"].dt.day_name()
```

### 5.4 行为类型过滤

```python
valid_behaviors = ["pv", "fav", "cart", "buy"]
df = df[df["behavior_type"].isin(valid_behaviors)]
```

### 5.5 限定分析时间窗口

原始数据可能混入极少量异常日期。正式分析时统一限制到目标观察期：

```python
analysis_start = pd.Timestamp("2017-11-25")
analysis_end = pd.Timestamp("2017-12-04")

df = df[
    (df["datetime"] >= analysis_start)
    & (df["datetime"] < analysis_end)
].copy()
```

使用左闭右开的区间 `[2017-11-25, 2017-12-04)`，可以完整包含 12 月 3 日，同时避免时分秒边界问题。

### 5.6 输出清洗结果

```python
df.to_csv(
    "data/processed/user_behavior_cleaned_sample.csv",
    index=False,
)
```

## 6. SQL 分析

建表脚本位于 [`1_creat_table.sql`](1_creat_table.sql)，核心指标脚本位于 [`2_overview_metrics.sql`](2_overview_metrics.sql)。

### 6.1 建立行为明细表

```sql
CREATE TABLE user_behavior (
    user_id BIGINT,
    item_id BIGINT,
    category_id BIGINT,
    behavior_type VARCHAR(10),
    behavior_timestamp BIGINT,
    behavior_datetime TIMESTAMP,
    behavior_date DATE,
    behavior_hour INT,
    weekday VARCHAR(20)
);
```

PostgreSQL 导入示例：

```sql
COPY user_behavior
FROM 'D:\ecommerce\data\processed\user_behavior_cleaned.csv'
DELIMITER ','
CSV HEADER;
```

### 6.2 核心规模指标

```sql
SELECT
    COUNT(*) AS total_events,
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT item_id) AS total_items,
    COUNT(DISTINCT category_id) AS total_categories,
    MIN(behavior_datetime) AS start_time,
    MAX(behavior_datetime) AS end_time
FROM user_behavior;
```

这些指标用于确定数据规模、覆盖范围和时间边界，也是 BI 看板的顶部 KPI。

### 6.3 日流量分析

```sql
SELECT
    behavior_date,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (
        WHERE behavior_type = 'pv'
    ) AS pv_events,
    COUNT(DISTINCT user_id) AS uv,
    COUNT(*) FILTER (
        WHERE behavior_type = 'buy'
    ) AS buy_events,
    COUNT(DISTINCT user_id) FILTER (
        WHERE behavior_type = 'buy'
    ) AS paying_users
FROM user_behavior
GROUP BY behavior_date
ORDER BY behavior_date;
```

商品级日流量则增加 `item_id` 分组：

```sql
SELECT
    item_id,
    behavior_date,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (
        WHERE behavior_type = 'pv'
    ) AS pv_events,
    COUNT(DISTINCT user_id) AS uv,
    COUNT(*) FILTER (
        WHERE behavior_type = 'fav'
    ) AS fav_events,
    COUNT(*) FILTER (
        WHERE behavior_type = 'cart'
    ) AS cart_events,
    COUNT(*) FILTER (
        WHERE behavior_type = 'buy'
    ) AS buy_events
FROM user_behavior
GROUP BY item_id, behavior_date
ORDER BY item_id, behavior_date;
```

### 6.4 小时流量分析

```sql
SELECT
    behavior_hour,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (
        WHERE behavior_type = 'pv'
    ) AS pv,
    COUNT(DISTINCT user_id) AS active_users,
    COUNT(*) FILTER (
        WHERE behavior_type = 'buy'
    ) AS buy_events
FROM user_behavior
GROUP BY behavior_hour
ORDER BY behavior_hour;
```

商品小时流量使用：

```sql
GROUP BY item_id, behavior_hour
```

从而识别不同商品的高峰时段，而不是只观察平台整体高峰。

### 6.5 有效行为到购买转化率

为了保证行为和购买属于同一个用户、同一个商品，并且购买发生在行为之后，先计算每个用户—商品组合的最后购买时间：

```sql
WITH last_buy_by_user_item AS (
    SELECT
        user_id,
        item_id,
        MAX(behavior_datetime) AS last_buy_datetime
    FROM user_behavior
    WHERE behavior_type = 'buy'
    GROUP BY user_id, item_id
),
behavior_to_buy AS (
    SELECT
        source.behavior_type,
        COUNT(*) AS total_behavior_count,
        COUNT(*) FILTER (
            WHERE last_buy.last_buy_datetime
                  > source.behavior_datetime
        ) AS valid_conversion_count
    FROM user_behavior AS source
    LEFT JOIN last_buy_by_user_item AS last_buy
        ON source.user_id = last_buy.user_id
       AND source.item_id = last_buy.item_id
    WHERE source.behavior_type IN (
        'pv',
        'fav',
        'cart'
    )
    GROUP BY source.behavior_type
)
SELECT
    behavior_type,
    total_behavior_count,
    valid_conversion_count,
    ROUND(
        valid_conversion_count * 100.0
        / NULLIF(total_behavior_count, 0),
        2
    ) AS conversion_to_buy_rate
FROM behavior_to_buy;
```

这里使用 `MAX(behavior_datetime)` 可以判断行为之后是否至少存在一次购买，同时避免把一条来源行为与多条购买记录连接后重复计数。

### 6.6 复购分析

```sql
WITH user_buy_counts AS (
    SELECT
        user_id,
        COUNT(*) AS buy_count
    FROM user_behavior
    WHERE behavior_type = 'buy'
    GROUP BY user_id
)
SELECT
    COUNT(*) AS paying_users,
    COUNT(*) FILTER (
        WHERE buy_count >= 2
    ) AS repeat_buy_users,
    ROUND(
        COUNT(*) FILTER (
            WHERE buy_count >= 2
        ) * 100.0 / COUNT(*),
        2
    ) AS repeat_buy_rate
FROM user_buy_counts;
```

当前定义是“观察期内发生至少两次购买行为的用户”为复购用户。如果业务需要更加严格的口径，可以改为“至少在两个不同日期购买”或“至少完成两个不同订单”。

### 6.7 RF 用户分层

由于数据没有订单金额，本项目使用最近购买间隔 R 和购买频率 F：

```sql
WITH user_buy AS (
    SELECT
        user_id,
        MAX(behavior_date) AS last_buy_date,
        COUNT(*) AS frequency
    FROM user_behavior
    WHERE behavior_type = 'buy'
    GROUP BY user_id
),
user_rf AS (
    SELECT
        user_id,
        MAX(last_buy_date) OVER ()
            - last_buy_date AS recency_days,
        frequency
    FROM user_buy
)
SELECT
    user_id,
    recency_days,
    frequency
FROM user_rf;
```

再利用中位数对 R、F 打分：

| R 得分 | F 得分 | 用户类型 | 运营策略 |
|---:|---:|---|---|
| 2 | 2 | 高价值用户 | 会员权益、提前购、重点维护 |
| 2 | 1 | 潜力用户 | 关联推荐、加购激励 |
| 1 | 2 | 重要召回用户 | 定向优惠、流失预警 |
| 1 | 1 | 一般/沉睡用户 | 低成本触达、控制营销成本 |

### 6.8 MySQL 改写说明

项目 SQL 使用 PostgreSQL 的 `FILTER` 语法。如果使用 MySQL，可改写为：

```sql
SUM(
    CASE
        WHEN behavior_type = 'buy' THEN 1
        ELSE 0
    END
) AS buy_events
```

## 7. 机器学习建模

购买预测代码位于 [`purchase_prediction_ml.py`](purchase_prediction_ml.py)，调参代码位于 [`GridsearchCV.py`](GridsearchCV.py)。

### 7.1 预测目标与样本粒度

预测粒度为：

```text
user_id + item_id
```

特征窗口：

```text
2017-11-25 00:00:00
至
2017-12-03 00:00:00（不包含）
```

标签窗口：

```text
2017-12-03 当天
```

标签定义：

```python
feature_df = df[
    (df["datetime"] >= "2017-11-25")
    & (df["datetime"] < "2017-12-03")
]

label_df = df[
    (df["date"].astype(str) == "2017-12-03")
    & (df["behavior_type"] == "buy")
][["user_id", "item_id"]].drop_duplicates()

label_df["label"] = 1
dataset = features.merge(
    label_df,
    on=["user_id", "item_id"],
    how="left",
)
dataset["label"] = (
    dataset["label"]
    .fillna(0)
    .astype(int)
)
```

- `label = 1`：用户在标签日购买了该商品。
- `label = 0`：用户在特征窗口与该商品有交互，但标签日没有购买。

特征和标签按时间隔离，避免把标签日行为泄漏到模型输入中。

### 7.2 基础行为次数

```python
features = feature_df.pivot_table(
    index=["user_id", "item_id"],
    columns="behavior_type",
    values="timestamp",
    aggfunc="count",
    fill_value=0,
).reset_index()
```

得到用户对商品的历史浏览、收藏、加购和购买次数。

### 7.3 多时间窗口特征

分别统计标签日前 1、3、7 天的四类行为：

```python
behavior_types = ["pv", "fav", "cart", "buy"]

for window_days in [1, 3, 7]:
    window_start = (
        label_time
        - pd.Timedelta(days=window_days)
    )
    window_df = feature_df[
        (feature_df["datetime"] >= window_start)
        & (feature_df["datetime"] < label_time)
    ]

    window_features = window_df.pivot_table(
        index=["user_id", "item_id"],
        columns="behavior_type",
        values="timestamp",
        aggfunc="count",
        fill_value=0,
    ).reindex(
        columns=behavior_types,
        fill_value=0,
    )

    window_features.columns = [
        f"{behavior}_count_{window_days}d"
        for behavior in window_features.columns
    ]
```

最终包括：

```text
pv_count_1d    fav_count_1d    cart_count_1d    buy_count_1d
pv_count_3d    fav_count_3d    cart_count_3d    buy_count_3d
pv_count_7d    fav_count_7d    cart_count_7d    buy_count_7d
```

多窗口特征可以帮助模型区分长期兴趣和近期购买意图。

### 7.4 最后一次行为序列特征

```python
last_behavior = (
    feature_df
    .sort_values(
        ["user_id", "item_id", "datetime"]
    )
    .groupby(
        ["user_id", "item_id"],
        as_index=False,
    )
    .tail(1)
)

last_behavior["hours_since_last_behavior"] = (
    label_time - last_behavior["datetime"]
).dt.total_seconds() / 3600

behavior_code = {
    "pv": 1,
    "fav": 2,
    "cart": 3,
    "buy": 4,
}

last_behavior["last_behavior_type"] = (
    last_behavior["behavior_type"]
    .map(behavior_code)
    .astype("int8")
)
```

其中：

- `hours_since_last_behavior`：最后一次行为距离标签日的小时数。
- `last_behavior_type`：最后一次行为类型。

### 7.5 模型选择

本项目使用随机森林作为基线模型：

```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,
    random_state=42,
    class_weight="balanced",
)

model.fit(X_train, y_train)
```

选择随机森林的原因：

- 能处理非线性关系和特征交互；
- 对特征缩放不敏感；
- 能处理行为次数、时间间隔等混合数值特征；
- 可通过特征重要性解释模型；
- `class_weight="balanced"` 能缓解购买样本稀少的问题。

### 7.6 数据切分

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
)
```

`stratify=y` 保证训练集和测试集维持相近的正负样本比例。更严格的生产评估应使用滚动时间窗口，而不是仅使用随机切分。

### 7.7 参数搜索

```python
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
)

param_grid = {
    "n_estimators": [200, 500, 800],
    "max_depth": [6, 10, 15],
    "min_samples_leaf": [1, 5, 10],
    "max_features": ["sqrt", "log2", 0.5],
    "class_weight": [
        "balanced",
        "balanced_subsample",
    ],
}

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42,
)

gs = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    scoring="average_precision",
    cv=cv,
    n_jobs=-1,
    verbose=2,
)

gs.fit(X_train, y_train)
```

购买预测属于类别高度不平衡任务，因此不使用 Accuracy 作为主要调参指标。一个全部预测为“不购买”的模型可能拥有很高的准确率，但没有业务价值。

### 7.8 评估指标

```python
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(classification_report(
    y_test,
    y_pred,
    digits=4,
    zero_division=0,
))
print("ROC-AUC:", roc_auc_score(
    y_test,
    y_proba,
))
print("PR-AUC:", average_precision_score(
    y_test,
    y_proba,
))
print(confusion_matrix(y_test, y_pred))
```

重点指标：

| 指标 | 分析价值 |
|---|---|
| Precision | 被模型判为会购买的样本中，有多少真实购买 |
| Recall | 所有真实购买样本中，模型识别出了多少 |
| F1-score | Precision 与 Recall 的综合表现 |
| ROC-AUC | 模型对正负样本的整体排序能力 |
| PR-AUC | 极度不平衡场景下更重要的正样本识别能力 |

## 8. BI 看板

项目提供两种 BI 落地方式：

1. 将 PostgreSQL/MySQL 聚合结果导入 Power BI 或 Tableau；
2. 使用项目内已经搭建并发布的 Commerce Pulse Web BI。

在线地址：

<https://commerce-pulse-bi.imbbking2.chatgpt.site>

### 8.1 数据快照生成

Web BI 的指标数据由 [`bi-dashboard/scripts/generate_dashboard_data.py`](bi-dashboard/scripts/generate_dashboard_data.py) 从清洗数据生成：

```python
daily = (
    df.groupby("date", observed=True)
    .agg(
        event_count=("user_id", "size"),
        uv=("user_id", "nunique"),
    )
    .reset_index()
)

hourly = (
    df.groupby("hour", observed=True)
    .agg(
        event_count=("user_id", "size"),
        uv=("user_id", "nunique"),
    )
    .reset_index()
)
```

商品级数据：

```python
top_item_daily = (
    top_items_df
    .groupby(
        ["item_id", "date"],
        observed=True,
    )
    .agg(
        event_count=("user_id", "size"),
        pv=(
            "behavior_type",
            lambda x: int((x == "pv").sum()),
        ),
        uv=("user_id", "nunique"),
        buy=(
            "behavior_type",
            lambda x: int((x == "buy").sum()),
        ),
    )
    .reset_index()
)
```

### 8.2 看板模块及分析价值

当前看板采用单页经营驾驶舱设计，各模块相当于传统 BI 中的不同分析页：

| 看板模块 | 展示指标 | 分析价值 |
|---|---|---|
| 全局概览 | 总行为量、活跃用户、覆盖商品、复购率 | 快速判断业务规模和用户质量 |
| 行为结构 | PV、收藏、加购、购买量及占比 | 识别用户主要行为及漏斗结构 |
| 日流量 | 日行为量、PV、购买量 | 发现流量增长、异常波动和重点日期 |
| 小时流量 | 0—23 时行为热度 | 识别投放、推送和活动运营时段 |
| 转化分析 | PV/Fav/Cart 到购买的有效转化率 | 判断哪些行为代表更强购买意图 |
| 商品流量 | 商品日流量、小时流量、UV 和购买量 | 识别高热商品及商品流量峰值 |
| 商品排行 | Top 商品行为量、UV、加购、购买 | 支持商品运营资源分配 |
| 类目分析 | Top 类目行为量 | 判断用户兴趣和流量集中方向 |

在 Power BI/Tableau 中，可将以下字段设置为筛选器：

- 日期；
- 小时；
- 商品 ID；
- 类目 ID；
- 行为类型。

并建立以下核心度量：

```text
PV = 浏览事件数
UV = 去重访问用户数
购买用户数 = 发生购买的去重用户数
行为转化率 = 有效转化行为数 / 行为总数
复购率 = 复购用户数 / 购买用户数
```

## 9. 结论与业务建议

以下结论基于当前看板数据窗口和项目数据子集，不代表淘宝整体平台表现。

1. **用户行为以浏览为主，购买仍是稀疏事件。** 当前窗口约有 215.1 万条行为，其中浏览约占 89.5%，购买约占 2.0%。业务应把优化重点放在浏览后的兴趣承接，而不是只关注最终订单量。

2. **越接近交易的行为，购买转化信号越强。** 浏览、收藏、加购后的有效购买转化率约为 2.47%、4.41% 和 6.33%。建议对加购未购买用户优先使用库存提醒、限时优惠和购物车召回，对收藏用户使用降价提醒。

3. **流量在观察期后段明显增强。** 12 月 2 日行为量达到窗口峰值，12 月 3 日仍处于高位。建议将活动资源、客服排班、广告预算和库存准备向高流量日期倾斜，同时比较活动前后的购买转化率，而不仅是流量增幅。

4. **小时流量集中在中午至下午早段。** 当前数据中 12—14 时较活跃，13 时达到小时行为峰值。消息推送和促销触达可在峰值前进行预热，但需要通过 A/B 测试验证增量效果，避免高峰期自然流量造成因果误判。

5. **观察期内复购用户占比较高。** 当前复购率约为 66.03%，说明购买用户中存在较强的重复购买行为。建议进一步区分“同日多次购买”“跨日复购”和“跨类目复购”，并针对高频用户建立会员或忠诚度运营策略。

6. **高流量商品不一定具有高购买效率。** 商品运营不应只按 PV 排名，应同时观察 UV、加购率、购买率以及商品的日/小时流量。对高浏览低购买商品，应优先检查价格、详情页、评价、库存和履约因素；对高加购商品，应加强临门转化策略。

## 10. 项目结构与运行方式

```text
ecommerce/
├── data/
│   ├── row/
│   │   └── UserBehavior.csv
│   └── processed/
│       ├── user_behavior_cleaned.csv
│       └── user_behavior_cleaned_sample.csv
├── docs/
│   └── images/
│       └── bi-dashboard.png
├── bi-dashboard/
│   ├── app/
│   └── scripts/
│       └── generate_dashboard_data.py
├── 1_creat_table.sql
├── 2_overview_metrics.sql
├── data_cleaning.py
├── purchase_prediction_ml.py
├── GridsearchCV.py
└── README.md
```

### 10.1 创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pandas scikit-learn
```

### 10.2 执行数据清洗

```powershell
python data_cleaning.py
```

### 10.3 导入 PostgreSQL 并执行分析

依次执行：

```text
1_creat_table.sql
2_overview_metrics.sql
```

### 10.4 训练购买预测模型

```powershell
python purchase_prediction_ml.py
```

运行网格搜索：

```powershell
python GridsearchCV.py
```

### 10.5 更新 BI 数据

```powershell
.\.venv\Scripts\python.exe `
  bi-dashboard\scripts\generate_dashboard_data.py
```

生成新的数据快照后，需要重新构建或发布 BI 看板。

## 后续优化方向

- 使用滚动时间窗口构造多个训练日、验证日和测试日；
- 增加次日、3 日和 7 日留存分析；
- 加入行为转换序列、活跃天数、行为间隔和趋势比例特征；
- 使用 LightGBM/XGBoost 与随机森林进行对比；
- 使用时间切分和阈值优化提升离线评估可靠性；
- 将 BI 从数据快照升级为数据库或数据仓库定时刷新；
- 增加模型特征重要性、SHAP 解释和用户购买概率分层。

## 数据与结论使用说明

数据中的用户、商品和类目 ID 均经过匿名化处理。本项目用于学习和分析演示，不涉及用户真实身份识别。业务结论来自当前数据样本和观察窗口，应结合线上实验、完整订单口径及业务成本进一步验证。
