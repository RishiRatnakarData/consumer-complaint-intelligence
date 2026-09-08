# Power BI build

1. Run the live pipeline.
2. In Power BI Desktop choose **Get Data > Text/CSV** and load `artifacts/monthly_kpis.csv`, `company_benchmark.csv`, and `product_issue_rank.csv`.
3. Create three pages: Executive Overview, Company Benchmark, Product and Issue Detail.
4. Add cards for total complaints, timely-response percentage, disputed percentage, and relief percentage.
5. Add a monthly line chart, company scatter/bar chart, and product-to-issue drilldown.
6. Add a visible subtitle with the data date range and a tooltip explaining that complaint counts are not market-share adjusted.
7. Export one 1600x900 screenshot to `docs/images/dashboard_overview.png` and commit it.

If you instead load the detail-level `complaints.parquet`, create these measures:

```DAX
Complaint Count = COUNTROWS(Complaints)

Timely Response % = DIVIDE(SUM(Complaints[is_timely]), [Complaint Count])

Disputed % = DIVIDE(SUM(Complaints[is_disputed]), [Complaint Count])

Relief % = DIVIDE(SUM(Complaints[has_relief]), [Complaint Count])

Previous Month Complaints =
CALCULATE([Complaint Count], DATEADD('Date'[Date], -1, MONTH))

Complaint MoM % =
DIVIDE([Complaint Count] - [Previous Month Complaints], [Previous Month Complaints])
```

Validate every card against the exported CSV before publishing.

