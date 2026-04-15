resource "google_dns_managed_zone" "mailgun_dns_zone" {
  project     = var.project_id
  name        = var.zone_name
  dns_name    = var.domain_name
  description = var.description
}

data "google_secret_manager_secret" "mailgun_dkim_secret" {
  secret_id = "mailgun-dkim-${var.environment}"
  project   = var.project_id
}

resource "google_secret_manager_secret_iam_member" "dkim_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.mailgun_dkim_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:sa-alerting-${var.environment}"
}

# CNAME Record
resource "google_dns_record_set" "mailgun_cname" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.mailgun_dns_zone.name
  name         = "email.mg.${google_dns_managed_zone.mailgun_dns_zone.dns_name}"
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["eu.mailgun.org."]
}

# TXT Record (SPF)
resource "google_dns_record_set" "mailgun_spf" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.mailgun_dns_zone.name
  name         = "mg.${google_dns_managed_zone.mailgun_dns_zone.dns_name}"
  type         = "TXT"
  ttl          = 300
  rrdatas      = ["\"v=spf1 include:mailgun.org ~all\""]
}

# MX Records
resource "google_dns_record_set" "mailgun_mx" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.mailgun_dns_zone.name
  name         = "mg.${google_dns_managed_zone.mailgun_dns_zone.dns_name}"
  type         = "MX"
  ttl          = 300
  rrdatas      = [
    "10 mxa.eu.mailgun.org.",
    "10 mxb.eu.mailgun.org."
  ]
}

# TXT Record (DKIM)
resource "google_dns_record_set" "mailgun_dkim" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.mailgun_dns_zone.name
  name         = "mta._domainkey.mg.${google_dns_managed_zone.mailgun_dns_zone.dns_name}"
  type         = "TXT"
  ttl          = 300
  rrdatas      = ["\"k=rsa; p=${var.mailgun_dkim_key}\""] 
}