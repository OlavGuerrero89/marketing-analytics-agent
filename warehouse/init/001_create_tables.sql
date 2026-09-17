-- ClickHouse schema for deterministic marketing campaign data.
CREATE DATABASE IF NOT EXISTS marketing;

CREATE TABLE IF NOT EXISTS marketing.campaigns
(
    campaign_id String,
    campaign_name String,
    channel LowCardinality(String),
    objective LowCardinality(String),
    start_date Date,
    end_date Date,

    CONSTRAINT valid_campaign_dates
        CHECK start_date <= end_date
)
ENGINE = MergeTree
ORDER BY campaign_id;


CREATE TABLE IF NOT EXISTS marketing.campaign_performance_daily
(
    event_date Date,
    campaign_id String,
    impressions UInt64,
    clicks UInt64,
    spend Decimal(12, 2),
    purchases UInt64,
    revenue Decimal(12, 2),

    CONSTRAINT clicks_not_greater_than_impressions
        CHECK clicks <= impressions,

    CONSTRAINT nonnegative_spend
        CHECK spend >= 0,

    CONSTRAINT nonnegative_revenue
        CHECK revenue >= 0
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, campaign_id);