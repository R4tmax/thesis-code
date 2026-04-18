CREATE OR REPLACE VIEW `behavio-bi-sp.test_dwh.view_alert_high_value_projects` AS
SELECT
    ProjectID,
    Client,
    Product,
    CZKValue
FROM
    `behavio-bi-sp.test_dwh.projects_act`
WHERE
    CZKValue > 100000000
ORDER BY
    `End`;

CREATE OR REPLACE VIEW `behavio-bi-sp.test_dwh.view_alert_overdue_partially_paid_invoices` AS
SELECT
    InvoiceType,
    InvoiceDate,
    DueDate,
    TaxableSupplyDate,
    ClientID,
    ProjectID,
    CustomerName,
    TotalAmountCZK,
    RemainingAmountCZK,
    PaymentStatus,
    PaymentDate,
    Currency,
    Description
FROM
    `behavio-bi-sp.test_dwh.invoices_act_nonman`
WHERE
    PaymentStatus = 'Částečně uhrazeno'
    AND DueDate < CURRENT_DATE()
    AND RemainingAmountCZK > 0
ORDER BY
    DueDate ASC;

CREATE OR REPLACE VIEW `behavio-bi-sp.test_dwh.view_alert_overdue_unpaid_invoices` AS
SELECT
    ProjectID,
    ClientID,
    DueDate,
    TotalAmountCZK,
    PaymentStatus
FROM
    `behavio-bi-sp.test_dwh.invoices_act_nonman`
WHERE
    DueDate < CURRENT_DATE()
    AND PaymentStatus IS NULL
ORDER BY
    DueDate ASC;

CREATE OR REPLACE VIEW `behavio-bi-sp.test_dwh.view_alert_projects_ending_soon` AS
SELECT
    ProjectID,
    Client,
    Product,
    `End`
FROM
    `behavio-bi-sp.test_dwh.projects_act`
WHERE
    DATE(`End`) BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY
    `End`;

CREATE OR REPLACE VIEW `behavio-bi-sp.test_dwh.view_alert_projects_started_this_month` AS
SELECT
  ProjectID,
  ClientID,
  Client,
  ico,
  Product,
  CZKValue,
  BookingDate,
  Renewal,
  `Start`,
  `End`,
  ARR
FROM
  `behavio-bi-sp.test_dwh.projects_act`
WHERE
  EXTRACT(YEAR FROM `Start`) = EXTRACT(YEAR FROM CURRENT_DATE())
  AND EXTRACT(MONTH FROM `Start`) = EXTRACT(MONTH FROM CURRENT_DATE());