CREATE MATERIALIZED VIEW `dataproject-458415.dwh_develop.mv_unpaid_invoices`
AS
SELECT
    invoice_id,
    customer_id,
    customer_name,
    issue_date,
    due_date,
    amount,
    currency,
    status,
    paid_date
FROM `dataproject-458415.dwh_develop.synth_invoices`
WHERE paid_date IS NULL;

CREATE MATERIALIZED VIEW `dataproject-458415.dwh_develop.mv_high_value_invoices`
AS
SELECT
    invoice_id,
    customer_id,
    customer_name,
    issue_date,
    due_date,
    amount,
    currency,
    status,
    paid_date
FROM `dataproject-458415.dwh_develop.synth_invoices`
WHERE amount > 5000;
