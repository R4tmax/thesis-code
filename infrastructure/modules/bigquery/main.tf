# 1. Create the Dataset
resource "google_bigquery_dataset" "main" {
  # Naming it cleanly: e.g., my_app_data_dev
  dataset_id                 = "my_app_data_${var.environment}"
  friendly_name              = "Main Application Dataset"
  description                = "Dataset for the ${var.environment} environment"
  location                   = var.location
  project                    = var.project_id

  # Because this is DEV, we want Terraform to be able to destroy it easily
  # In PROD, you would set this to false to protect your data!
  delete_contents_on_destroy = true
}

# 2. Create the Table with a strict schema
resource "google_bigquery_table" "test_table" {
  dataset_id = google_bigquery_dataset.main.dataset_id
  table_id   = "users_test_data"
  project    = var.project_id

  # Defining the columns using a JSON heredoc
  schema = <<EOF
[
  {
    "name": "user_id",
    "type": "INTEGER",
    "mode": "REQUIRED"
  },
  {
    "name": "username",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "role",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

# 3. Inject Test Data (The Bootstrapper)
resource "google_bigquery_job" "inject_test_data" {
  job_id     = "inject_dummy_data_${var.environment}_${timestamp()}"
  project    = var.project_id
  location   = var.location

  query {
    query = <<EOF
      INSERT INTO `${var.project_id}.${google_bigquery_dataset.main.dataset_id}.${google_bigquery_table.test_table.table_id}` (user_id, username, role)
      VALUES
        (1, 'alice_admin', 'admin'),
        (2, 'bob_tester', 'user'),
        (3, 'charlie_dev', 'user')
    EOF

    use_legacy_sql = false
  }

  # This ensures the table actually exists before Terraform tries to insert data into it
  depends_on = [google_bigquery_table.test_table]
}