resource "google_bigquery_dataset" "main" {
  dataset_id    = "financial_${var.environment}"
  friendly_name = "Main Application Dataset"
  description   = "Dataset for the ${var.environment} environment"
  location      = var.location
  project       = var.project_id

  delete_contents_on_destroy = var.delete_contents_on_destroy
}

resource "google_bigquery_table" "invoices_table" {
  dataset_id = google_bigquery_dataset.main.dataset_id
  table_id   = "invoices"
  project    = var.project_id

  deletion_protection = var.deletion_protection

}

resource "google_bigquery_table" "alert_view" {
  dataset_id = google_bigquery_dataset.main.dataset_id
  table_id   = "view_alert_total_invoices"
  project    = var.project_id

  deletion_protection = false

  view {
    query          = "SELECT * FROM `${var.project_id}.${google_bigquery_dataset.main.dataset_id}.${google_bigquery_table.invoices_table.table_id}`"
    use_legacy_sql = false
  }
}