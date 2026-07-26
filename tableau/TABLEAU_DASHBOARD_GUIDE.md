# Tableau 电商用户行为分析看板搭建指南

## 1. 作品集目标

本 Tableau 项目用于展示以下能力：

- 多数据源连接与 Relationship 数据建模；
- KPI、趋势图、漏斗图、热力图和用户分层图；
- LOD 表达式、表计算、参数和计算字段；
- Dashboard Filter Action、Highlight Action 与跳转导航；
- 业务指标口径定义和可行动洞察表达。

建议最终保存为：

```text
tableau/Ecommerce_User_Behavior_Analysis.twbx
```

并将四张仪表板截图保存到：

```text
docs/images/tableau/
├── 01_executive_overview.png
├── 02_conversion_retention.png
├── 03_user_segmentation.png
└── 04_product_insight.png
```

## 2. 生成 Tableau 数据集

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe `
  tableau\generate_tableau_data.py
```

生成文件位于 `tableau/data/`：

| 文件 | 用途 |
|---|---|
| `overview_kpis.csv` | 核心 KPI |
| `behavior_distribution.csv` | 行为数量和占比 |
| `daily_traffic.csv` | 日流量趋势 |
| `hourly_traffic.csv` | 0—23 时流量 |
| `conversion_funnel.csv` | 有效行为到购买转化 |
| `repeat_purchase.csv` | 复购指标 |
| `retention_cohort.csv` | 留存 Cohort |
| `rf_segments.csv` | RF 用户分层 |
| `top_categories.csv` | Top 50 类目 |
| `top_products.csv` | Top 100 商品 |
| `product_daily_traffic.csv` | Top 商品日流量 |
| `product_hourly_traffic.csv` | Top 商品小时流量 |

所有 CSV 使用 UTF-8 with BOM，避免 Tableau 中文字段或内容乱码。

## 3. Tableau 数据连接

### 3.1 推荐方式

1. 打开 Tableau Public 或 Tableau Desktop。
2. 选择 **连接 → 文本文件**。
3. 首先连接 `overview_kpis.csv`。
4. 使用左侧“添加”依次加入其他 CSV。
5. 每张聚合表保留为独立逻辑表，不要进行物理 Join。

这些表粒度不同，强行 Join 会造成 KPI 重复。推荐每组工作表使用对应的数据源。

### 3.2 数据类型检查

| 字段 | Tableau 类型 |
|---|---|
| `date`、`analysis_start`、`analysis_end`、`cohort_date` | 日期 |
| `hour`、`day_number`、`funnel_order` | 整数 |
| 各类 Count | 整数 |
| `event_ratio`、`repeat_buy_rate`、`retention_rate`、`conversion_to_buy_rate` | 数字（小数） |
| `user_id`、`item_id`、`category_id` | 字符串维度 |

将 ID 转为字符串，避免 Tableau 对 ID 求和。

## 4. 通用计算字段

### 4.1 行为中文名称

```tableau
CASE [behavior_type]
WHEN "pv" THEN "浏览"
WHEN "fav" THEN "收藏"
WHEN "cart" THEN "加购"
WHEN "buy" THEN "购买"
END
```

### 4.2 行为颜色分组

```tableau
CASE [behavior_type]
WHEN "pv" THEN "流量"
WHEN "fav" THEN "兴趣"
WHEN "cart" THEN "意向"
WHEN "buy" THEN "成交"
END
```

### 4.3 购买行为占比

在 `overview_kpis.csv` 中：

```tableau
SUM([buy_events]) / SUM([total_events])
```

格式设置为百分比，保留两位小数。

### 4.4 有效行为到购买转化率

在 `conversion_funnel.csv` 中：

```tableau
SUM([valid_conversion_count])
/
SUM([total_behavior_count])
```

该指标口径是同一用户、同一商品且购买时间晚于来源行为。

### 4.5 商品购买/浏览率

```tableau
IF SUM([pv]) = 0 THEN 0
ELSE SUM([buy]) / SUM([pv])
END
```

### 4.6 日环比

在日行为量视图中创建快速表计算：

```tableau
(SUM([event_count])
 - LOOKUP(SUM([event_count]), -1))
/
ABS(LOOKUP(SUM([event_count]), -1))
```

计算方向设置为“表（横向）”。

### 4.7 高潜商品分类

```tableau
IF SUM([pv]) >= WINDOW_MEDIAN(SUM([pv]))
AND SUM([buy]) / SUM([pv])
    < WINDOW_MEDIAN(SUM([buy]) / SUM([pv]))
THEN "高浏览低转化"
ELSEIF SUM([cart]) >= WINDOW_MEDIAN(SUM([cart]))
THEN "高购买意向"
ELSE "一般商品"
END
```

## 5. Dashboard 01：经营概览

建议尺寸：`1366 × 768`，布局使用 Tiled。

### 5.1 工作表

#### KPI 卡片

数据源：`overview_kpis.csv`

分别建立：

- 总行为量；
- 活跃用户数；
- 商品数；
- 购买事件数；
- 复购率。

将指标拖到 Text，使用大号字体，并在标题中说明口径。

#### 日流量趋势

数据源：`daily_traffic.csv`

```text
Columns：date
Rows：event_count
Marks：Line
```

将 `pv`、`cart`、`buy` 加入 Measure Values，可通过参数切换指标。

#### 行为结构

数据源：`behavior_distribution.csv`

```text
Rows：行为中文名称
Columns：event_count
Color：行为中文名称
Label：event_ratio
Marks：Bar
```

#### 小时活跃热力

数据源：`hourly_traffic.csv`

```text
Columns：hour
Color：event_count
Label：hour
Marks：Square
```

### 5.2 分析价值

- 快速判断平台样本规模和行为结构；
- 识别日期趋势和小时高峰；
- 为活动排期、推送时段和资源配置提供依据。

## 6. Dashboard 02：转化与留存

### 6.1 有效行为转化漏斗

数据源：`conversion_funnel.csv`

```text
Rows：行为中文名称
Columns：valid_conversion_count
Sort：funnel_order 升序
Label：conversion_to_buy_rate
Marks：Bar
```

使用居中条形图或标准横向条形图。Tooltip 同时显示：

- 行为总次数；
- 有效转化次数；
- 有效转化率；
- 指标口径说明。

### 6.2 留存 Cohort 热力图

数据源：`retention_cohort.csv`

```text
Rows：cohort_date
Columns：day_number
Color：retention_rate
Label：retention_rate
Marks：Square
```

颜色使用单色渐变，Day 0 可保留为 100%，重点观察 Day 1、Day 3 和 Day 7。

### 6.3 复购指标

数据源：`repeat_purchase.csv`

展示：

- 购买用户数；
- 复购用户数；
- 一次购买用户数；
- 复购率。

### 6.4 分析价值

- 判断收藏、加购等行为的交易意图强度；
- 判断新增活跃用户在后续日期的回访情况；
- 识别平台是依赖一次性购买还是重复购买。

## 7. Dashboard 03：用户分层

数据源：`rf_segments.csv`

### 7.1 RF 分层矩阵

```text
Columns：r_score
Rows：f_score
Color：user_count
Label：segment + user_count
Marks：Square
```

Tooltip 加入平均最近购买间隔和平均购买频率。

### 7.2 用户结构条形图

```text
Rows：segment
Columns：user_count
Color：segment
Label：user_count
```

### 7.3 用户运营建议文本

| 用户层级 | 运营建议 |
|---|---|
| 高价值用户 | 会员权益、提前购、重点维护 |
| 潜力用户 | 关联推荐、加购激励 |
| 重要召回用户 | 定向优惠、流失召回 |
| 一般/沉睡用户 | 低成本触达、控制营销成本 |

### 7.4 分析价值

- 展示用户价值分层能力；
- 将分析结果直接映射到差异化运营策略；
- 避免对所有用户使用同一种营销方式。

## 8. Dashboard 04：商品洞察

### 8.1 商品热度排行

数据源：`top_products.csv`

```text
Rows：item_id
Columns：event_count
Color：buy_pv_rate
Label：event_count、buy
Filter：Top 20 by event_count
```

### 8.2 商品日流量

数据源：`product_daily_traffic.csv`

```text
Columns：date
Rows：event_count
Color：item_id
Marks：Line
```

### 8.3 商品小时流量

数据源：`product_hourly_traffic.csv`

```text
Columns：hour
Rows：event_count
Color：event_count
Marks：Bar
```

### 8.4 类目排行

数据源：`top_categories.csv`

```text
Rows：category_id
Columns：event_count
Color：buy_pv_rate
Label：item_count、buy
```

### 8.5 Dashboard Action

在 Dashboard 中设置：

```text
源工作表：商品热度排行
运行操作：选择
目标工作表：商品日流量、商品小时流量
目标筛选器：item_id
清除选择：显示所有值
```

点击某个商品后，日流量和小时流量联动更新。这是作品集中展示 Tableau 交互能力的重要环节。

## 9. 参数与交互设计

### 9.1 指标切换参数

创建参数 `p_traffic_metric`：

```text
数据类型：字符串
允许值：列表
总行为量
浏览量
加购量
购买量
```

计算字段：

```tableau
CASE [p_traffic_metric]
WHEN "总行为量" THEN SUM([event_count])
WHEN "浏览量" THEN SUM([pv])
WHEN "加购量" THEN SUM([cart])
WHEN "购买量" THEN SUM([buy])
END
```

### 9.2 动态标题

```tableau
"日趋势｜" + [p_traffic_metric]
```

### 9.3 全局筛选器

建议提供：

- 日期；
- 商品 ID；
- 类目 ID；
- 行为类型。

筛选器采用下拉或紧凑列表，不要占用过多画布。

### 9.4 导航按钮

四张 Dashboard 之间添加导航：

```text
经营概览
转化与留存
用户分层
商品洞察
```

## 10. 视觉规范

建议配色：

| 用途 | 色值 |
|---|---|
| 主色 | `#7458EE` |
| 浏览 | `#7C5CFF` |
| 收藏 | `#EC6E9A` |
| 加购 | `#E7A33E` |
| 购买 | `#25A979` |
| 深色文本 | `#171822` |
| 浅色背景 | `#F4F1EB` |

格式建议：

- 百分比保留两位小数；
- 大数字使用“万”或 K/M 缩写；
- Tooltip 必须解释业务口径；
- 图表标题使用结论式表达，而不是仅写图表名称；
- 同一行为在所有页面保持一致颜色；
- 单张仪表板控制在 4—6 个关键视图。

## 11. 发布到 Tableau Public

完成工作簿后：

1. 隐藏无关字段；
2. 检查所有筛选器和 Action；
3. 将数据提取为 Extract；
4. 选择 **Server → Tableau Public → Save to Tableau Public**；
5. 补充作品标题、项目说明和 GitHub 链接；
6. 为每张 Dashboard 导出 PNG；
7. 将 Tableau Public 链接和截图更新到项目 `README.md`。

发布前确认数据中只有匿名 ID，不包含个人敏感信息。

## 12. 求职展示重点

介绍项目时建议按以下结构表达：

1. 先解释业务问题和指标口径；
2. 展示数据清洗及 SQL 分析能力；
3. 说明 Tableau 的数据模型为什么使用多个聚合数据源；
4. 演示指标参数切换、商品筛选联动和 Dashboard 导航；
5. 讲解有效转化率与普通漏斗口径的差异；
6. 最后给出可执行运营建议，而不是只展示图表。
