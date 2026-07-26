--1 数据概览--
SELECT
    COUNT(*) AS total_events,
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT item_id) AS total_items,
    COUNT(DISTINCT category_id) AS total_categories,
    MIN(behavior_datetime) AS start_time,
    MAX(behavior_datetime) AS end_time
FROM user_behavior;
--2 行为分布--
SELECT
    behavior_type,
    COUNT(*) AS event_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS event_ratio
FROM user_behavior
GROUP BY behavior_type
ORDER BY event_count DESC;
--3.1 用户日活跃趋势--
SELECT
    behavior_date,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (WHERE behavior_type = 'pv') AS pv_events,
    COUNT(DISTINCT user_id) AS uv,
    COUNT(*) FILTER (WHERE behavior_type = 'buy') AS buy_events,
    COUNT(DISTINCT user_id) FILTER (WHERE behavior_type = 'buy') AS paying_users
FROM user_behavior
GROUP BY behavior_date
ORDER BY behavior_date;

--3.2 各商品日流量趋势
SELECT
    item_id,
    behavior_date,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (WHERE behavior_type = 'pv') AS pv_events,
    COUNT(DISTINCT user_id) AS uv,
    COUNT(*) FILTER (WHERE behavior_type = 'fav') AS fav_events,
    COUNT(*) FILTER (WHERE behavior_type = 'cart') AS cart_events,
    COUNT(*) FILTER (WHERE behavior_type = 'buy') AS buy_events,
    COUNT(DISTINCT user_id) FILTER (
        WHERE behavior_type = 'buy'
    ) AS paying_users
FROM user_behavior
GROUP BY item_id, behavior_date
ORDER BY item_id, behavior_date;
--4.1 小时活跃趋势--
SELECT
    behavior_hour,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (WHERE behavior_type = 'pv') AS pv,
    COUNT(DISTINCT user_id) AS active_users,
    COUNT(*) FILTER (WHERE behavior_type = 'buy') AS buy_events
FROM user_behavior
GROUP BY behavior_hour
ORDER BY behavior_hour;

--4.2 各商品小时流量分布（按0至23点汇总所有日期）
SELECT
    item_id,
    behavior_hour,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (WHERE behavior_type = 'pv') AS pv,
    COUNT(DISTINCT user_id) AS uv,
    COUNT(*) FILTER (WHERE behavior_type = 'fav') AS fav_events,
    COUNT(*) FILTER (WHERE behavior_type = 'cart') AS cart_events,
    COUNT(*) FILTER (WHERE behavior_type = 'buy') AS buy_events,
    COUNT(DISTINCT user_id) FILTER (
        WHERE behavior_type = 'buy'
    ) AS paying_users
FROM user_behavior
GROUP BY item_id, behavior_hour
ORDER BY item_id, behavior_hour;

--5 转化漏斗--
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
            WHERE last_buy.last_buy_datetime > source.behavior_datetime
        ) AS valid_conversion_count
    FROM user_behavior AS source
    LEFT JOIN last_buy_by_user_item AS last_buy
        ON source.user_id = last_buy.user_id
       AND source.item_id = last_buy.item_id
    WHERE source.behavior_type IN ('pv', 'fav', 'cart')
    GROUP BY source.behavior_type
)
SELECT
    behavior_type,
    total_behavior_count,
    valid_conversion_count,
    ROUND(
        valid_conversion_count * 100.0 / NULLIF(total_behavior_count, 0),
        2
    ) AS conversion_to_buy_rate
FROM behavior_to_buy
ORDER BY
    CASE behavior_type
        WHEN 'pv' THEN 1
        WHEN 'fav' THEN 2
        WHEN 'cart' THEN 3
    END;

--6 复购分析--
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
    COUNT(*) FILTER (WHERE buy_count >= 2) AS repeat_buy_users,
    ROUND(
        COUNT(*) FILTER (WHERE buy_count >= 2) * 100.0 / COUNT(*),
        2
    ) AS repeat_buy_rate
FROM user_buy_counts;

--7 RFM 用户分层--
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
        last_buy_date,
        frequency,
        MAX(last_buy_date) OVER () - last_buy_date AS recency_days
    FROM user_buy
),
rf_median AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY recency_days
        ) AS recency_median,

        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY frequency
        ) AS frequency_median
    FROM user_rf
),
rf_score AS (
    SELECT
        ur.user_id,
        ur.last_buy_date,
        ur.recency_days,
        ur.frequency,

        CASE
            WHEN ur.recency_days <= rm.recency_median THEN 2
            ELSE 1
        END AS r_score,

        CASE
            WHEN ur.frequency >= rm.frequency_median THEN 2
            ELSE 1
        END AS f_score

    FROM user_rf ur
    CROSS JOIN rf_median rm
)

SELECT
    r_score,
    f_score,
    COUNT(*) AS user_count
FROM rf_score
GROUP BY r_score,
         f_score
ORDER BY r_score DESC,
         f_score DESC;

--8 商品与类目分析--
SELECT
    category_id,
    COUNT(*) AS event_count,
    COUNT(*) FILTER (WHERE behavior_type = 'pv') AS pv_count,
    COUNT(*) FILTER (WHERE behavior_type = 'cart') AS cart_count,
    COUNT(*) FILTER (WHERE behavior_type = 'fav') AS fav_count,
    COUNT(*) FILTER (WHERE behavior_type = 'buy') AS buy_count,
    ROUND(
        COUNT(*) FILTER (WHERE behavior_type = 'buy') * 100.0
        / NULLIF(COUNT(*) FILTER (WHERE behavior_type = 'pv'), 0),
        2
    ) AS buy_pv_rate
FROM user_behavior
GROUP BY category_id
HAVING COUNT(*) >= 100
ORDER BY buy_count DESC
LIMIT 20;
WITH behavior_counts AS (
    SELECT
        behavior_type,
        COUNT(DISTINCT user_id) AS user_count
    FROM user_behavior
    GROUP BY behavior_type
)
SELECT
    behavior_type,
    user_count,
    ROUND(user_count * 100.0 / MAX(user_count) OVER (), 2) AS conversion_rate_from_pv
FROM behavior_counts
ORDER BY
    CASE behavior_type
        WHEN 'pv' THEN 1
        WHEN 'fav' THEN 2
        WHEN 'cart' THEN 3
        WHEN 'buy' THEN 4
    END;
