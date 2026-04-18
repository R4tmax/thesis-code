output "dev_name_servers" {
  description = "Values to be used as NS records at the core DNS registrar/zone"
  value       = module.dev_mailgun_dns.name_servers
}