output "dataset_id" {
  value = google_bigquery_dataset.main.dataset_id
}

output "table_id" {
  value = google_bigquery_table.test_table.table_id
}