#!/bin/sh
# Security gate for CI. Runs INSIDE the built image (Jenkins "Security Scan" stage), from /app:
#   pip-audit  every requirements*.txt (all pinned, so --no-deps: audits exactly what is installed)
#   bandit     src/, medium severity and above
# Any finding fails the build. Tool versions are pinned so a new release cannot redden main by itself.
set -eu

pip install --quiet pip-audit==2.10.1 bandit==1.9.4

status=0
for f in requirements*.txt; do
    echo "== pip-audit $f"
    pip-audit -r "$f" --no-deps --disable-pip || status=1
done

echo "== bandit src (medium+)"
bandit -r src -ll -q || status=1

exit $status
