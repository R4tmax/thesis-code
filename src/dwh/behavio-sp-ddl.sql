--- source tables are read as live connection from Data Warehouse source drive
-- take note that the data can only be read with read rights for the source drive
-- this condition applies to all SA working via BQ

--- invoice table, manual entry is not linked, refer to manual for further clarification
CREATE OR REPLACE VIEW test_dwh.invoices_act_nonman AS (
SELECT
    id AS InvoiceID,
    typ_faktury AS InvoiceType,
    vystaveno AS  InvoiceDate,
    splatnost AS  DueDate,
    datum_zdan_plneni AS TaxableSupplyDate,
    CAST(REGEXP_REPLACE(zaklad_celkem_kc, r'[^0-9\.]', '') AS NUMERIC) AS TotalBaseAmountCZK,
    SPLIT(REGEXP_EXTRACT(uvodni_text_tiskne_se_pred_polozkami, r'^Client ID:\s*([a-zA-Z0-9,\s]*)\n*\s*Project ID:\s*[a-zA-Z0-9,\s]*\n*$'), ', ')AS ClientID,
    SPLIT(REGEXP_EXTRACT(uvodni_text_tiskne_se_pred_polozkami, r'^Client ID:\s*[a-zA-Z0-9,\s]*\n*\s*Project ID:\s*([a-zA-Z0-9,\s]*)\n*$'), ', ') AS ProjectID,
    nazev_firmy_nebo_jmeno_osoby AS CustomerName,
    ico AS CustomerIDAlt,
    CAST(REGEXP_REPLACE(celkem_kc, r'[^0-9\.]', '') AS NUMERIC) AS TotalAmountCZK,
    stav_uhrady_dokladu AS PaymentStatus,
    CAST(REGEXP_REPLACE(zbyva_uhradit_kc, r'[^0-9\.]', '') AS NUMERIC) AS RemainingAmountCZK,
    datum_uhrady AS PaymentDate,
    CAST(REGEXP_REPLACE(celkem_bez_zaloh_kc, r'[^0-9\.]', '') AS NUMERIC) AS TotalWithoutAdvancesCZK,
    CAST(REGEXP_REPLACE(dph_celkem_kc, r'[^0-9\.]', '') AS NUMERIC) AS TotalVATAmountCZK,
    cislo_objednavky AS OrderNumber,
    popis AS Description,
    mena AS Currency,
    CAST(REGEXP_REPLACE(kurz, r'[^0-9\.]', '') AS NUMERIC) AS ExchangeRate,
    CAST(REGEXP_REPLACE(celkem_mena, r'[^0-9\.]', '') AS NUMERIC) AS TotalAmountCurrency,
    forma_uhrady AS PaymentMethod
FROM `behavio-bi-sp.test_dwh.invoices_act_src`

--- account view
CREATE OR REPLACE VIEW test_dwh.projects_act AS (
SELECT
    ProjID AS ProjectID,
    ClientID,
    Client,
    ICO AS ico,
    Product,
    CAST(REGEXP_REPLACE(CZK_Value, r'[^0-9\.]', '') AS NUMERIC) AS CZKValue,
    Booking_Date AS BookingDate,
    Renewal,
    Start,
    `End`,
    ARR
FROM `behavio-bi-sp.test_dwh.projects_act_src`);