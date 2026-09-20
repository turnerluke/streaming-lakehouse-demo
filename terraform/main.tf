terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.3"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------- BigQuery datasets ----------

resource "google_bigquery_dataset" "bronze" {
  dataset_id                 = "bronze"
  location                   = var.region
  description                = "Raw landed events; append-only."
  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset" "silver" {
  dataset_id                 = "silver"
  location                   = var.region
  description                = "Cleaned, typed, deduplicated staging models."
  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset" "gold" {
  dataset_id                 = "gold"
  location                   = var.region
  description                = "Business-ready facts and dimensions (incl. SCD2)."
  delete_contents_on_destroy = true
}

# ---------- Bronze landing table ----------

resource "google_bigquery_table" "raw_events" {
  dataset_id          = google_bigquery_dataset.bronze.dataset_id
  table_id            = "raw_events"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "ingested_at"
  }

  clustering = ["event_type", "repo_name"]

  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "event_type", type = "STRING", mode = "NULLABLE" },
    { name = "actor_login", type = "STRING", mode = "NULLABLE" },
    { name = "repo_name", type = "STRING", mode = "NULLABLE" },
    { name = "event_created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "payload", type = "JSON", mode = "NULLABLE" },
  ])
}

# ---------- Service account for the consumer + dbt ----------

resource "google_service_account" "pipeline" {
  account_id   = "streaming-lakehouse"
  display_name = "Streaming Lakehouse pipeline"
}

resource "google_project_iam_member" "bq_user" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_service_account_key" "pipeline_key" {
  service_account_id = google_service_account.pipeline.name
}

resource "local_file" "sa_key" {
  filename        = "${path.module}/../.secrets/sa-key.json"
  content         = base64decode(google_service_account_key.pipeline_key.private_key)
  file_permission = "0600"
}
