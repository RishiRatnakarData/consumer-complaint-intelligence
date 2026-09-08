CREATE OR REPLACE VIEW monthly_kpis AS
SELECT
    received_month,
    COUNT(*) AS sample_complaint_count,
    ROUND(100.0 * AVG(is_timely), 1) AS timely_response_pct,
    ROUND(100.0 * AVG(has_relief), 1) AS relief_pct,
    ROUND(
        100.0 * AVG(CAST(has_narrative AS INTEGER)),
        1
    ) AS narrative_pct
FROM complaints
GROUP BY received_month
ORDER BY received_month;

CREATE OR REPLACE VIEW company_benchmark AS
WITH company_stats AS (
    SELECT
        company,
        COUNT(*) AS complaint_count,
        AVG(is_timely) AS timely_rate,
        AVG(has_relief) AS relief_rate,
        AVG(CAST(has_narrative AS INTEGER)) AS narrative_rate
    FROM complaints
    GROUP BY company
),
overall AS (
    SELECT
        COUNT(*) AS total_complaints,
        AVG(is_timely) AS overall_timely_rate
    FROM complaints
)
SELECT
    company,
    complaint_count,
    ROUND(
        100.0 * complaint_count / total_complaints,
        2
    ) AS sample_share_pct,
    ROUND(100.0 * timely_rate, 1) AS timely_response_pct,
    ROUND(100.0 * relief_rate, 1) AS relief_pct,
    ROUND(100.0 * narrative_rate, 1) AS narrative_pct,
    ROUND(
        100.0 * (timely_rate - overall_timely_rate),
        1
    ) AS timely_vs_overall_pp
FROM company_stats
CROSS JOIN overall
WHERE complaint_count >= 25
ORDER BY complaint_count DESC;

CREATE OR REPLACE VIEW product_issue_rank AS
WITH counts AS (
    SELECT
        product,
        issue,
        COUNT(*) AS complaint_count
    FROM complaints
    GROUP BY product, issue
),
ranked AS (
    SELECT
        product,
        issue,
        complaint_count,
        SUM(complaint_count) OVER (
            PARTITION BY product
        ) AS product_complaint_count,
        DENSE_RANK() OVER (
            PARTITION BY product
            ORDER BY complaint_count DESC
        ) AS issue_rank
    FROM counts
)
SELECT
    product,
    issue,
    complaint_count,
    product_complaint_count,
    ROUND(
        100.0 * complaint_count / product_complaint_count,
        1
    ) AS issue_share_within_product_pct,
    issue_rank
FROM ranked
ORDER BY product, issue_rank, issue;