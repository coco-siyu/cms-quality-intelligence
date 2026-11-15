#!/usr/bin/env bash

set -euo pipefail

api_url="${CMSQI_SMOKE_API_URL:-https://cms-quality-intelligence-api.onrender.com}"
frontend_url="${CMSQI_SMOKE_FRONTEND_URL:-https://cms-quality-intelligence-web.onrender.com}"

CMSQI_SMOKE_API_URL="${api_url}" \
CMSQI_SMOKE_FRONTEND_URL="${frontend_url}" \
"$(dirname "$0")/smoke.sh"

measures="$(
  curl --max-time 120 --fail --silent --show-error \
    "${api_url}/api/measures?from_year=2025&to_year=2026&page_size=100"
)"

node -e '
  const crypto = require("node:crypto");
  const response = JSON.parse(process.argv[1]);
  if (response.pagination?.total_items !== 8 || response.items?.length !== 8) {
    throw new Error("Expected exactly eight published preview measures.");
  }
  const memberships = response.items.reduce(
    (count, measure) => count + measure.performance_years.length,
    0,
  );
  if (memberships !== 14) {
    throw new Error(`Expected fourteen published memberships; received ${memberships}.`);
  }
  if (response.items.some((measure) => String(measure.measure_id).startsWith("DEMO-"))) {
    throw new Error("Fictional DEMO records are exposed by the public preview.");
  }
  const fingerprint = crypto
    .createHash("sha256")
    .update(JSON.stringify(response.items))
    .digest("hex");
  const verified = [...new Set(response.items.map(
    (measure) => measure.freshness?.last_verified_at,
  ))].filter(Boolean);
  console.log("Published roster: 8 measures, 14 memberships");
  console.log(`Roster persistence fingerprint: ${fingerprint}`);
  console.log(`Last-verified markers: ${verified.join(", ") || "unavailable"}`);
' "${measures}"

detail="$(
  curl --max-time 120 --fail --silent --show-error \
    "${api_url}/api/measures/001?from_year=2025&to_year=2026"
)"

node -e '
  const response = JSON.parse(process.argv[1]);
  if (response.versions?.length !== 2) {
    throw new Error("Expected PY2025 and PY2026 versions for measure 001.");
  }
  for (const version of response.versions) {
    const evidence = version.fields?.find((field) => field.field === "measure_set")?.evidence;
    if (!Array.isArray(evidence) || evidence.length !== 2) {
      throw new Error(`Expected two roster evidence links for PY${version.performance_year}.`);
    }
    for (const reference of evidence) {
      const hostname = new URL(reference.official_url).hostname.toLowerCase();
      if (hostname !== "cms.gov" && !hostname.endsWith(".cms.gov")) {
        throw new Error(`Non-CMS evidence URL was published: ${reference.official_url}`);
      }
    }
  }
  console.log("Evidence boundary: two official CMS references per checked year");
' "${detail}"

admin_status="$(
  curl --max-time 120 --silent --show-error --output /dev/null \
    --write-out "%{http_code}" "${api_url}/api/admin/review-summary"
)"
if [[ "${admin_status}" != "401" ]]; then
  echo "Unauthenticated Admin request returned HTTP ${admin_status}; expected 401." >&2
  exit 1
fi

http_frontend_url="http://${frontend_url#https://}"
redirect_headers="$(
  curl --max-time 120 --silent --show-error --head "${http_frontend_url}/"
)"
redirect_headers_lower="$(printf "%s" "${redirect_headers}" | tr "[:upper:]" "[:lower:]")"
if [[ "${redirect_headers}" != *" 301 "* ]] || \
  [[ "${redirect_headers_lower}" != *"location: https://"* ]]; then
  echo "The preview did not return the expected HTTP-to-HTTPS redirect." >&2
  exit 1
fi

echo "Admin boundary: unauthenticated private request rejected"
echo "Transport boundary: HTTP redirects to HTTPS"
echo "Render preview verification passed."
