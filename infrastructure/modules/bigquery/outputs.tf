output "dataset_id" {
  value = google_bigquery_dataset.main.dataset_id
}

output "table_id" {
  value = google_bigquery_table.invoices_table.table_id
}