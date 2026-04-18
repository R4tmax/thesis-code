output "dev_name_servers" {
  description = "Values to be used as NS records at the core DNS registrar/zone"
  value       = module.mailgun_dns.name_servers
}