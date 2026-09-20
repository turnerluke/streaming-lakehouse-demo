#!/usr/bin/env bash
# Reminder script. GCP budgets can be created via the API, but for a one-off
# personal project the console is faster and less error-prone.
set -euo pipefail

cat <<'EOF'
Set your GCP billing alert BEFORE running `terraform apply`:

  1. https://console.cloud.google.com/billing/budgets
  2. "Create Budget" on the billing account linked to this project
  3. Amount: $20 (or your risk tolerance)
  4. Alerts: 50%, 90%, 100% of budget
  5. Email: your address

Do this now. It takes 90 seconds. It has saved every cloud demo I have
ever built from a bad Tuesday.
EOF
