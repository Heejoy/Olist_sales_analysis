USE olist;
GO

/* How many customers are in each customer tier,
and how much sales does each tier generate? */
CREATE OR ALTER VIEW dbo.vw_sales_by_tier AS
SELECT
    Tier,
    COUNT(*)                                           AS Customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS Customer_share_pct,
    ROUND(SUM(Monetary), 0)                            AS Sales,
    CASE Tier
        WHEN 'VIP' THEN 1
        WHEN 'Loyal' THEN 2
        WHEN 'Potentially Loyal' THEN 3
        WHEN 'New' THEN 4
        WHEN 'At-Risk' THEN 5
        ELSE 6
    END AS Tier_order
FROM dbo.vw_rfm
GROUP BY Tier;
GO

/* What are the sales and number of orders for each year and month? */
CREATE OR ALTER VIEW dbo.vw_sales_monthly AS
SELECT
    YEAR(o.order_purchase_timestamp)   AS Order_year,
    MONTH(o.order_purchase_timestamp)  AS Order_month,
    ROUND(SUM(p.payment_value), 0)     AS Sales,
    COUNT(DISTINCT o.order_id)         AS Orders
FROM dbo.orders_clean AS o
JOIN dbo.order_payments AS p
  ON p.order_id = o.order_id
GROUP BY YEAR(o.order_purchase_timestamp), MONTH(o.order_purchase_timestamp);
GO

/* How much sales does each product category generate? */
CREATE OR ALTER VIEW dbo.vw_sales_by_category AS
SELECT
    COALESCE(pr.product_category_name_english, 'Unknown') AS Category,
    ROUND(SUM(oi.price + oi.freight_value), 0)            AS Sales,
    COUNT(DISTINCT oi.order_id)                           AS Orders
FROM dbo.order_items AS oi
JOIN dbo.orders_clean AS o
  ON o.order_id = oi.order_id
LEFT JOIN dbo.products AS pr
  ON pr.product_id = oi.product_id
GROUP BY COALESCE(pr.product_category_name_english, 'Unknown');
GO

/* What are the sales and number of customers for each state (region)? */
CREATE OR ALTER VIEW dbo.vw_sales_by_state AS
WITH customer_state AS (
    -- one state per real customer (a few customers moved and appear with 2-3 states)
    SELECT customer_unique_id, MIN(customer_state) AS State
    FROM dbo.customers
    GROUP BY customer_unique_id
)
SELECT
    cs.State,
    COUNT(DISTINCT o.customer_unique_id) AS Customers,
    ROUND(SUM(p.payment_value), 0)       AS Sales
FROM dbo.orders_clean AS o
JOIN dbo.order_payments AS p
  ON p.order_id = o.order_id
JOIN customer_state AS cs
  ON cs.customer_unique_id = o.customer_unique_id
GROUP BY cs.State;
GO





SELECT TABLE_NAME AS view_name
FROM INFORMATION_SCHEMA.VIEWS
ORDER BY TABLE_NAME;