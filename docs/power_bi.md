# Power BI build

This dashboard separates full-population complaint volume from metrics calculated on the 5,000-row weekly-stratified detail sample.

## Required files

Run the validated live pipeline first:

```powershell
python -m src.pipeline --limit 5000 --start-date 2025-01-01 --end-date 2025-12-31
```

In Power BI Desktop, select **Get data > Text/CSV** and load:

- `artifacts/official_monthly_counts.csv`
- `artifacts/monthly_kpis.csv`
- `artifacts/company_benchmark.csv`
- `artifacts/product_issue_rank.csv`

In Power Query, confirm that both `received_month` fields use the **Date** data type and numeric fields use whole-number or decimal-number types. Select **Close & Apply**.

## Measures

Create these measures in `official_monthly_counts`:

```DAX
Official Complaint Count =
SUM(official_monthly_counts[official_complaint_count])

Peak Monthly Complaints =
MAX(official_monthly_counts[official_complaint_count])
```

Create these measures in `monthly_kpis`:

```DAX
Detail Sample Rows =
SUM(monthly_kpis[sample_complaint_count])

Sample Relief % =
DIVIDE(
    SUMX(
        monthly_kpis,
        monthly_kpis[sample_complaint_count]
            * monthly_kpis[relief_pct]
    ),
    SUM(monthly_kpis[sample_complaint_count]) * 100
)

Sample Timely Response % =
DIVIDE(
    SUMX(
        monthly_kpis,
        monthly_kpis[sample_complaint_count]
            * monthly_kpis[timely_response_pct]
    ),
    SUM(monthly_kpis[sample_complaint_count]) * 100
)

Sample Narrative % =
DIVIDE(
    SUMX(
        monthly_kpis,
        monthly_kpis[sample_complaint_count]
            * monthly_kpis[narrative_pct]
    ),
    SUM(monthly_kpis[sample_complaint_count]) * 100
)
```

Format the final three measures as percentages with one decimal place.

## Page 1 — Executive overview

Add:

1. A card for `Official Complaint Count`.
2. A card for `Peak Monthly Complaints`.
3. A card for `Detail Sample Rows`.
4. A card for `Sample Relief %`.
5. A line chart with `official_monthly_counts[received_month]` on the x-axis and `Official Complaint Count` on the y-axis.
6. A clustered column chart using `monthly_kpis[received_month]` and the raw `relief_pct`, `narrative_pct`, and `timely_response_pct` fields.

Use this subtitle:

> Official volume: all 5,442,964 CFPB complaints recorded in 2025. Response metrics: 5,000-row weekly-stratified detail sample.

Expected validation values:

- Official complaint count: **5,442,964**
- Peak month: **October 2025**
- Peak monthly complaints: **519,786**
- Detail sample rows: **5,000**
- Sample relief rate: approximately **40.6%**
- Sample timely-response rate: approximately **99.6%**

## Page 2 — Company benchmark

Use `company_benchmark.csv` and add:

1. A horizontal bar chart with company on the y-axis and complaint count on the x-axis.
2. A clustered bar chart comparing relief percentage and narrative percentage by company.
3. A scatter chart with complaint count on the x-axis, relief percentage on the y-axis, sample share as size, and company as details.
4. Tooltips for timely-response percentage and difference from the sample-wide timely-response rate.

Add this visible note:

> Company results describe the detail sample and are not adjusted for company size, market share, customer exposure, or product mix. Relief-category differences are not quality rankings.

Expected validation examples:

- TransUnion relief: **63.3%**
- Equifax relief: **63.2%**
- Experian relief: **0.7%**

## Page 3 — Product and issue detail

Use `product_issue_rank.csv` and add:

1. A product slicer.
2. A matrix with product and issue as hierarchical rows.
3. Matrix values for complaint count, product complaint count, within-product issue share, and issue rank.
4. A bar chart filtered to issue rank 1 for the leading issue within each product.
5. A second bar chart showing the largest product-issue combinations by sampled complaint count.

Expected validation examples:

- Sampled credit-reporting complaints: **4,379**
- Leading credit-reporting issue: **Incorrect information on your report**
- Leading issue share within credit reporting: **58.2%**

## Design

- Use a 16:9 canvas.
- Use a restrained palette such as navy `#183B56`, teal `#008C95`, amber `#F4B942`, and light gray `#F3F5F7`.
- Keep page titles, subtitles, labels, and units visible.
- Label all sample-derived visuals with the word **Sample**.
- Do not include a disputed-rate visual.
- Avoid 3D charts, gauges, and decorative visuals that do not support a decision.

## Validation and evidence

Before publication:

1. Confirm every card against the generated CSV files.
2. Confirm the monthly line chart contains 12 months.
3. Confirm company and product visuals are labeled as sample results.
4. Save the local report as `dashboard/consumer_complaint_intelligence.pbix`. The `.pbix` file is intentionally ignored by Git.
5. Export or capture a readable 1600×900 overview image as `docs/images/dashboard_overview.png`.
6. Replace the README dashboard placeholder with the exported image.
7. Commit the screenshot and updated documentation.
