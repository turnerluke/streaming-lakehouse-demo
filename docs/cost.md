# Cost notes

Target: **$0/mo** on BigQuery free tier. Realistic ceiling if you leave it running: **$5–10/mo**.

## Free-tier budget

- BigQuery: 1 TB query bytes/month, 10 GB storage/month.
- GitHub Events firehose: ~5 events/sec, each ~2 KB gzipped. ~40 MB/day → ~1.2 GB/month.
  At those sizes bronze storage is trivial and query bytes stay well under 1 TB
  as long as gold tables are partitioned + clustered (they are).

## Non-negotiables before running in cloud

1. **Set a $20 billing alert on the GCP project.** GCP console -> Billing ->
   Budgets & alerts.
2. **Do not use Kinesis or MSK.** Both bill per-hour of idle capacity. Use
   Redpanda locally, or Confluent Cloud serverless if you want a hosted broker.
3. **Do not switch dbt materializations to `table` in silver.** Views over
   the partitioned bronze table are cheap; materialized tables in silver
   duplicate storage.
4. **Turn off the dashboard's auto-refresh** when you're not demoing. Every
   refresh is a BigQuery job.

## Traps

| Thing                           | Cost if you forget                                  |
| ------------------------------- | --------------------------------------------------- |
| BigQuery streaming inserts      | $0.01/200MB — fine at demo scale, $$$ at prod scale |
| Storage API reads from Evidence | metered separately; small at demo scale             |
| Cloud Logging default retention | free tier: 50 GB/mo ingestion                       |
| Service-account keys in git     | not a bill, but a P1 incident                       |
