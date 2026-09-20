output "service_account_email" {
  value = google_service_account.pipeline.email
}

output "bronze_dataset" { value = google_bigquery_dataset.bronze.dataset_id }
output "silver_dataset" { value = google_bigquery_dataset.silver.dataset_id }
output "gold_dataset"   { value = google_bigquery_dataset.gold.dataset_id }

output "sa_key_path" {
  value       = local_file.sa_key.filename
  description = "Point GOOGLE_APPLICATION_CREDENTIALS at this."
}
