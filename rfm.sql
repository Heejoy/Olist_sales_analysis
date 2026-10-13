CREATE OR ALTER VIEW dbo.vw_rfm AS
WITH base AS (
    -- one row per real customer: last purchase, number of orders, total paid
    SELECT
        o.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_purchase,
        COUNT(DISTINCT o.order_id)      AS Frequency,
        SUM(p.payment_value)            AS Monetary
    FROM dbo.orders_clean AS o
    LEFT JOIN dbo.order_payments AS p
           ON p.order_id = o.order_id
    GROUP BY o.customer_unique_id
),
recency AS (
    -- days between the dataset's latest purchase and the customer's last purchase
    SELECT
        b.*,
        DATEDIFF(SECOND,
                 b.last_purchase,
                 (SELECT MAX(order_purchase_timestamp) FROM dbo.orders_clean)
        ) / 86400 AS Recency
    FROM base AS b
),
cutoffs AS (
    -- the 20/40/60/80 % points of Recency (one row)
    SELECT DISTINCT
        PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY Recency) OVER () AS p20,
        PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY Recency) OVER () AS p40,
        PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY Recency) OVER () AS p60,
        PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY Recency) OVER () AS p80
    FROM recency
),
scored AS (
    SELECT
        r.customer_unique_id,
        r.Recency,
        r.Frequency,
        r.Monetary,
        CASE WHEN r.Recency <= c.p20 THEN 5
             WHEN r.Recency <= c.p40 THEN 4
             WHEN r.Recency <= c.p60 THEN 3
             WHEN r.Recency <= c.p80 THEN 2
             ELSE 1 END AS R_score,
        CASE WHEN r.Frequency >= 5 THEN 5
             ELSE r.Frequency END AS F_score,
        CASE WHEN r.Monetary < 20  THEN 1
             WHEN r.Monetary < 50  THEN 2
             WHEN r.Monetary < 100 THEN 3
             WHEN r.Monetary < 500 THEN 4
             ELSE 5 END AS M_score
    FROM recency AS r
    CROSS JOIN cutoffs AS c
),
coded AS (
    SELECT
        s.*,
        CAST(s.R_score AS CHAR(1)) + CAST(s.F_score AS CHAR(1)) + CAST(s.M_score AS CHAR(1)) AS RFM_code
    FROM scored AS s
)
SELECT
    customer_unique_id,
    Recency,
    Frequency,
    Monetary,
    R_score,
    F_score,
    M_score,
    RFM_code,
    CASE
        WHEN RFM_code IN ('455', '545', '554', '555') THEN 'VIP'
        WHEN R_score >= 4 AND F_score >= 4           THEN 'Loyal'
        WHEN R_score = 5  AND F_score = 1            THEN 'New'
        WHEN R_score = 1  AND F_score <= 2           THEN 'Churned'
        WHEN R_score = 2  AND F_score IN (2, 3)      THEN 'At-Risk'
        ELSE 'Potentially Loyal'
    END AS Tier
FROM coded;