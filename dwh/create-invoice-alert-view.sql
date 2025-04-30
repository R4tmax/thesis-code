-- Dataset: alerts_tmp
-- Table: missing_sales_alert

CREATE OR REPLACE TABLE `your-project.alerts_tmp.missing_sales_alert` AS
SELECT
  '⚠️ Sales data missing for ' || CURRENT_DATE() AS alert_message
WHERE NOT EXISTS (
  SELECT 1
  FROM `your-project.your_dataset.sales`
  WHERE DATE(sale_timestamp) = CURRENT_DATE()
);
