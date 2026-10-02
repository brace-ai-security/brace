#!/bin/sh
set -eu
for ns in payments payments-batch search identity identity-admin; do
  TEAM_NAMESPACE="$ns" envsubst < "$(dirname "$0")/workload-rbac.yaml"
  echo "---"
done
