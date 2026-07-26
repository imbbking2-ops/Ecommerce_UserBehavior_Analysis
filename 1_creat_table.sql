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
--导入 CSV--
COPY user_behavior
FROM 'D:\ecommerce\data\processed\user_behavior_cleaned.csv'
DELIMITER ','
CSV HEADER;