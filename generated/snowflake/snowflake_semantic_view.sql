CREATE OR REPLACE SEMANTIC VIEW YOUR_DATABASE.SAC_CONFORMANCE.SAC_METRICS
TABLES (
  orders AS YOUR_DATABASE.SAC_CONFORMANCE.SAC_FACT PRIMARY KEY (order_id)
)
DIMENSIONS (
  orders.order_date AS orders.order_date,
  orders.region AS orders.region,
  orders.warehouse_id AS orders.warehouse_id,
  orders.product_id AS orders.product_id,
  orders.order_status AS orders.order_status,
  orders.month AS DATE_TRUNC('MONTH', orders.order_date),
  orders.iso_week_year AS YEAROFWEEKISO(orders.order_date),
  orders.iso_week AS WEEKISO(orders.order_date)
)
METRICS (
  orders.revenue AS SUM(CASE WHEN orders.order_status = 'Completed' THEN orders.net_sales_amount END),
  orders.gross_margin AS SUM(CASE WHEN orders.order_status = 'Completed' THEN (orders.net_sales_amount - orders.cost_of_goods_sold) END),
  orders.fill_rate AS (SUM(CASE WHEN orders.order_status = 'Completed' THEN orders.fulfilled_quantity END)) / NULLIF((SUM(CASE WHEN orders.order_status = 'Completed' THEN orders.ordered_quantity END)), 0),
  orders.inventory_turnover AS (SUM(CASE WHEN orders.order_status = 'Completed' THEN orders.cost_of_goods_sold END)) / NULLIF((AVG(CASE WHEN orders.order_status = 'Completed' THEN orders.inventory_value END)), 0),
  orders.unique_customers AS COUNT(DISTINCT CASE WHEN orders.order_status = 'Completed' THEN orders.customer_id END)
)
COMMENT = 'Generated from vendor-neutral Semantics-as-Code conformance contract';
