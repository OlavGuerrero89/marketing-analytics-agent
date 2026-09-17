"""Generate deterministic fake marketing-performance data."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RANDOM_SEED = 42
EXPECTED_PERFORMANCE_ROWS = 436
MONEY_PRECISION = Decimal("0.01")
OUTPUT_DIRECTORY = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    campaign_name: str
    channel: str
    objective: str
    start_date: date
    end_date: date
    base_impressions: int
    ctr: float
    conversion_rate: float
    cpc: Decimal
    average_order_value: Decimal


CAMPAIGNS = (
    Campaign(
        "CMP001",
        "Search Brand",
        "Search",
        "Acquisition",
        date(2026, 1, 1),
        date(2026, 2, 28),
        4_500,
        0.060,
        0.085,
        Decimal("1.20"),
        Decimal("82.00"),
    ),
    Campaign(
        "CMP002",
        "Search Non-Brand",
        "Search",
        "Acquisition",
        date(2026, 1, 1),
        date(2026, 2, 28),
        8_000,
        0.045,
        0.050,
        Decimal("2.10"),
        Decimal("90.00"),
    ),
    Campaign(
        "CMP003",
        "Social Prospecting",
        "Social",
        "Acquisition",
        date(2026, 1, 1),
        date(2026, 2, 28),
        10_000,
        0.025,
        0.030,
        Decimal("1.40"),
        Decimal("76.00"),
    ),
    Campaign(
        "CMP004",
        "Social Retargeting",
        "Social",
        "Retention",
        date(2026, 1, 1),
        date(2026, 2, 28),
        5_500,
        0.042,
        0.065,
        Decimal("1.25"),
        Decimal("88.00"),
    ),
    Campaign(
        "CMP005",
        "Email Loyalty",
        "Email",
        "Retention",
        date(2026, 1, 1),
        date(2026, 2, 28),
        7_000,
        0.075,
        0.095,
        Decimal("0.18"),
        Decimal("74.00"),
    ),
    Campaign(
        "CMP006",
        "Email Reactivation",
        "Email",
        "Retention",
        date(2026, 1, 15),
        date(2026, 2, 28),
        4_000,
        0.055,
        0.060,
        Decimal("0.24"),
        Decimal("68.00"),
    ),
    Campaign(
        "CMP007",
        "Display Awareness",
        "Display",
        "Awareness",
        date(2026, 1, 1),
        date(2026, 2, 15),
        18_000,
        0.009,
        0.006,
        Decimal("0.80"),
        Decimal("70.00"),
    ),
    Campaign(
        "CMP008",
        "Display Retargeting",
        "Display",
        "Acquisition",
        date(2026, 1, 10),
        date(2026, 2, 28),
        6_500,
        0.020,
        0.045,
        Decimal("0.95"),
        Decimal("79.00"),
    ),
)


def inclusive_dates(start: date, end: date):
    """Yield every date between start and end, including both boundaries."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""
    return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def generate_performance_rows() -> list[dict[str, object]]:
    """Generate reproducible daily campaign-performance records."""
    rng = random.Random(RANDOM_SEED)
    records: list[dict[str, object]] = []

    for campaign in CAMPAIGNS:
        for event_date in inclusive_dates(
            campaign.start_date,
            campaign.end_date,
        ):
            weekend_factor = 0.82 if event_date.weekday() >= 5 else 1.0
            volume_variation = rng.uniform(0.88, 1.12)
            rate_variation = rng.uniform(0.92, 1.08)

            impressions = round(
                campaign.base_impressions
                * weekend_factor
                * volume_variation
            )

            clicks = round(
                impressions
                * campaign.ctr
                * rate_variation
            )
            clicks = min(max(clicks, 0), impressions)

            conversion_rate = campaign.conversion_rate

            if (
                campaign.campaign_id == "CMP004"
                and event_date >= date(2026, 2, 1)
            ):
                conversion_rate *= 1.35

            purchase_variation = rng.uniform(0.90, 1.10)
            purchases = round(
                clicks
                * conversion_rate
                * purchase_variation
            )
            purchases = min(max(purchases, 0), clicks)

            if (
                campaign.campaign_id == "CMP007"
                and date(2026, 1, 1)
                <= event_date
                <= date(2026, 1, 7)
            ):
                purchases = 0

            spend = money(
                Decimal(clicks)
                * campaign.cpc
                * Decimal(str(rng.uniform(0.96, 1.04)))
            )

            revenue = money(
                Decimal(purchases)
                * campaign.average_order_value
                * Decimal(str(rng.uniform(0.95, 1.05)))
            )

            records.append(
                {
                    "event_date": event_date.isoformat(),
                    "campaign_id": campaign.campaign_id,
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": spend,
                    "purchases": purchases,
                    "revenue": revenue,
                }
            )

    return records


def validate_campaigns() -> None:
    """Validate campaign configuration before generating files."""
    campaign_ids = [campaign.campaign_id for campaign in CAMPAIGNS]

    if len(campaign_ids) != len(set(campaign_ids)):
        raise ValueError("Campaign IDs must be unique.")

    for campaign in CAMPAIGNS:
        if campaign.start_date > campaign.end_date:
            raise ValueError(
                f"Invalid date range for {campaign.campaign_id}."
            )

        if campaign.base_impressions < 0:
            raise ValueError(
                f"Negative impressions for {campaign.campaign_id}."
            )

        if not 0 <= campaign.ctr <= 1:
            raise ValueError(
                f"Invalid CTR for {campaign.campaign_id}."
            )

        if not 0 <= campaign.conversion_rate <= 1:
            raise ValueError(
                f"Invalid conversion rate for {campaign.campaign_id}."
            )


def validate_performance_rows(
    records: list[dict[str, object]],
) -> None:
    """Validate grain, ranges, relationships, and expected volume."""
    if len(records) != EXPECTED_PERFORMANCE_ROWS:
        raise ValueError(
            "Unexpected performance row count: "
            f"expected {EXPECTED_PERFORMANCE_ROWS}, "
            f"received {len(records)}."
        )

    campaign_by_id = {
        campaign.campaign_id: campaign
        for campaign in CAMPAIGNS
    }

    observed_keys: set[tuple[str, str]] = set()

    for record in records:
        campaign_id = str(record["campaign_id"])
        event_date_text = str(record["event_date"])
        event_date = date.fromisoformat(event_date_text)
        key = (event_date_text, campaign_id)

        if key in observed_keys:
            raise ValueError(f"Duplicate fact grain: {key}.")

        observed_keys.add(key)

        campaign = campaign_by_id.get(campaign_id)
        if campaign is None:
            raise ValueError(
                f"Unknown campaign ID: {campaign_id}."
            )

        if not campaign.start_date <= event_date <= campaign.end_date:
            raise ValueError(
                f"Date outside campaign validity: {key}."
            )

        impressions = int(record["impressions"])
        clicks = int(record["clicks"])
        purchases = int(record["purchases"])
        spend = Decimal(str(record["spend"]))
        revenue = Decimal(str(record["revenue"]))

        if min(impressions, clicks, purchases) < 0:
            raise ValueError(f"Negative count found in {key}.")

        if clicks > impressions:
            raise ValueError(
                f"Clicks exceed impressions in {key}."
            )

        if purchases > clicks:
            raise ValueError(
                f"Purchases exceed clicks in {key}."
            )

        if spend < 0 or revenue < 0:
            raise ValueError(
                f"Negative monetary value found in {key}."
            )


def write_campaigns_csv() -> None:
    """Write the public campaign attributes."""
    output_path = OUTPUT_DIRECTORY / "campaigns.csv"
    fieldnames = (
        "campaign_id",
        "campaign_name",
        "channel",
        "objective",
        "start_date",
        "end_date",
    )

    with output_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for campaign in CAMPAIGNS:
            writer.writerow(
                {
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.campaign_name,
                    "channel": campaign.channel,
                    "objective": campaign.objective,
                    "start_date": campaign.start_date.isoformat(),
                    "end_date": campaign.end_date.isoformat(),
                }
            )


def write_performance_csv(
    records: list[dict[str, object]],
) -> None:
    """Write daily performance records."""
    output_path = (
        OUTPUT_DIRECTORY
        / "campaign_performance_daily.csv"
    )
    fieldnames = (
        "event_date",
        "campaign_id",
        "impressions",
        "clicks",
        "spend",
        "purchases",
        "revenue",
    )

    with output_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    """Generate, validate, and write both datasets."""
    validate_campaigns()
    performance_records = generate_performance_rows()
    validate_performance_rows(performance_records)

    write_campaigns_csv()
    write_performance_csv(performance_records)

    print(f"Generated {len(CAMPAIGNS)} campaign records.")
    print(
        "Generated "
        f"{len(performance_records)} daily performance records."
    )
    print(f"Random seed: {RANDOM_SEED}.")


if __name__ == "__main__":
    main()