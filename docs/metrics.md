# Metric Definitions

## Semantic Contract

All analytical metrics are defined in Cube and exposed through the public `marketing_performance` view.

The agent does not calculate metrics from raw ClickHouse records. It requests governed measures from Cube and validates their returned values before composing an answer.

## Base Measures

### Impressions

```
impressions = SUM(impressions)
```

The total number of times advertisements were served.

### Clicks

```
clicks = SUM(clicks)
```

The total number of recorded advertisement clicks.

### Spend

```
spend = SUM(spend)
```

Total advertising cost in USD.

Spend is stored with two-decimal precision in the mock warehouse.

### Purchases

```
purchases = SUM(purchases)
```

The total number of purchases attributed to a campaign.

The mock dataset assumes attribution has already occurred upstream. It does not model attribution windows or multi-touch credit.

### Revenue

```
revenue = SUM(revenue)
```

Total revenue in USD attributed to campaign purchases.

Revenue is stored with two-decimal precision.

## Derived Measures

### Click-Through Rate

```
CTR = SUM(clicks) / SUM(impressions)
```

CTR measures the proportion of served impressions that produced a click.

When total impressions are zero, CTR is null.

The semantic layer calculates the ratio of aggregated totals. It does not average daily CTR values.

### Cost per Click

```
CPC = SUM(spend) / SUM(clicks)
```

CPC measures average advertising spend per click.

When total clicks are zero, CPC is null.

### Cost per Acquisition

```
CPA = SUM(spend) / SUM(purchases)
```

CPA measures average advertising spend per attributed purchase.

When total purchases are zero, CPA is null.

For this assessment, a purchase is treated as the acquisition event.

### Return on Advertising Spend

```
ROAS = SUM(revenue) / SUM(spend)
```

ROAS measures attributed revenue generated for each dollar of advertising spend.

For example, a ROAS of `3.50x` means the campaign generated `$3.50` in attributed revenue for every `$1.00` of spend.

When total spend is zero, ROAS is null.

ROAS is not profit, margin, incrementality, or causal lift. It does not account for product costs, operating expenses, organic conversions, or purchases that would have occurred without advertising.

## Dimensions

### Campaign ID

Stable identifier for one campaign.

### Campaign Name

Human-readable campaign label used in ranked responses.

### Channel

Marketing delivery channel:

- Search
- Social
- Email
- Display

### Objective

Primary campaign objective:

- Acquisition
- Retention
- Awareness

### Event Date

Calendar date of the daily campaign observation.

The mock dataset covers January and February 2026.

## Aggregation Behavior

Metrics are aggregated at the dimensions requested by the agent.

Examples:

- Spend by channel groups daily campaign facts by channel.
- Purchases by campaign groups all applicable daily facts by campaign.
- ROAS by campaign divides each campaign’s aggregated revenue by its aggregated spend.
- A date filter restricts fact rows before aggregation.
- A request without dates uses the full available data period.

Derived ratios must be calculated from aggregated numerator and denominator measures:

```
correct CTR = total clicks / total impressions
```

They must not be calculated as:

```
incorrect CTR = average of daily CTR values
```

The same rule applies to CPC, CPA, and ROAS.

## Numerical Handling

The warehouse stores spend and revenue as fixed-precision decimals.

The Python validation layer converts numeric Cube results to `Decimal` rather than binary floating point. It also rejects non-finite values such as:

- `NaN`
- Positive infinity
- Negative infinity

Null values are preserved for derived metrics whose denominator is zero.

## Interpretation Assumptions

The supported phrases map to metrics as follows:


| User phrase                    | Governed metric                   |
| ------------------------------ | --------------------------------- |
| Spend, cost, or amount spent   | Spend                             |
| Most purchases                 | Purchases                         |
| Result relative to spend       | ROAS                              |
| Best campaign without a metric | Ambiguous; clarification required |


“Best” is not assigned a universal definition because different stakeholders may mean volume, efficiency, revenue, or another business outcome.

## Current Limitations

The available metrics describe observed campaign performance. They do not establish causality.

The dataset does not include:

- Control groups.
- Randomized treatment assignment.
- Incremental conversions.
- Customer-level attribution.
- Gross margin.
- Customer lifetime value.
- Budget constraints.
- Statistical uncertainty.

Consequently, ROAS and purchase totals can support descriptive ranking, but they should not be interpreted as causal campaign impact.