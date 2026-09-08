CREATE OR REPLACE VIEW monthly_kpis AS
SELECT
    received_month,
    COUNT(*) AS complaint_count,
    ROUND(100.0 * AVG(is_timely), 1) AS timely_response_pct,
    ROUND(100.0 * AVG(is_disputed), 1) AS disputed_pct,
    ROUND(100.0 * AVG(has_relief), 1) AS relief_pct
FROM complaints
GROUP BY received_month;

CREATE OR REPLACE VIEW company_benchmark AS
WITH company_stats AS (
    SELECT
        company,
        COUNT(*) AS complaint_count,
        AVG(is_timely) AS timely_rate,
        AVG(is_disputed) AS dispute_rate
    FROM complaints
    GROUP BY company
), overall AS (
    SELECT AVG(is_timely) AS overall_timely_rate FROM complaints
)
SELECT
    company,
    complaint_count,
    ROUND(100.0 * timely_rate, 1) AS timely_response_pct,
    ROUND(100.0 * dispute_rate, 1) AS disputed_pct,
    ROUND(100.0 * (timely_rate - overall_timely_rate), 1) AS timely_vs_overall_pp
FROM company_stats CROSS JOIN overall;

CREATE OR REPLACE VIEW product_issue_rank AS
WITH counts AS (
    SELECT product, issue, COUNT(*) AS complaint_count
    FROM complaints
    GROUP BY product, issue
)
SELECT
    product,
    issue,
    complaint_count,
    DENSE_RANK() OVER (PARTITION BY product ORDER BY complaint_count DESC) AS issue_rank
FROM counts;

