resource "google_dns_managed_zone" "mailgun_dns_zone" {
  project     = var.project_id
  name        = var.zone_name
  dns_name    = var.domain_name
  description = var.description
}

data "google_secret_manager_secret_version" "mailgun_dkim_payload" {
  project = var.project_id
  secret  = "mailgun-dkim-${var.environment}"
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
  rrdatas = [
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

  rrdatas = ["\"k=rsa; p=${data.google_secret_manager_secret_version.mailgun_dkim_payload.secret_data}\""]
}