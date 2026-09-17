from enum import StrEnum


class Metric(StrEnum):
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    SPEND = "spend"
    PURCHASES = "purchases"
    REVENUE = "revenue"
    CTR = "ctr"
    CPC = "cpc"
    CPA = "cpa"
    ROAS = "roas"


class Dimension(StrEnum):
    CAMPAIGN_ID = "campaign_id"
    CAMPAIGN_NAME = "campaign_name"
    CHANNEL = "channel"
    OBJECTIVE = "objective"


class TimeGranularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class SortDirection(StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"