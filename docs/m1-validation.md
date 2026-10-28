# M1 public explorer validation

This checklist validates the M1 public roster explorer from the guarded verified
seed through PostgreSQL, FastAPI, and the rendered React routes. M1 publishes
only the source-backed APP Plus roster baseline. Collection-specific clinical
fields remain private until their individual review and publication steps are
complete.

## Automated validation

From the repository root, run the complete backend and frontend suite:

```sh
UV_CACHE_DIR=/tmp/cmsqi-uv-cache make check
```

The M1 cross-stack coverage specifically verifies that:

- the verified seed and guarded publication produce eight public identities and
  14 program-year memberships;
- `GET /api/performance-years` returns the published years;
- list, detail, and filtered navigation endpoints expose only public records;
- each published year for a roster measure carries two official CMS evidence
  references;
- a direct measure route renders the approved roster fields and source links;
- draft collection variants and clinical field candidates do not appear on the
  public page; and
- URL filters survive list-to-detail and Previous/Next navigation.

## Local manual inspection

Prepare the local preview database once, then launch the full application:

```sh
make preview-data
make dev
```

Open `http://localhost:5173` and review the following:

1. The Dashboard and Measure Explorer show the published API badge, not the demo
   badge.
2. The year selectors are populated by `GET /api/performance-years`. The current
   verified inventory provides PY2025 and PY2026.
3. The Measure Explorer contains exactly these eight public IDs: `001`, `112`,
   `113`, `134`, `236`, `321`, `479`, and `484`.
4. Open `/measures/001?from=2025&to=2026`. Confirm both published roster years
   appear, each with official source links and without unreviewed clinical
   specification wording.
5. Apply a search or year filter in Measure Explorer, open a result, and use
   Previous/Next. The position and neighboring IDs must reflect that filtered
   list, and returning to Measures must preserve the URL filters.
6. Open `/admin` separately. Private variants and pending candidates may be
   present there after authentication, but they must not affect public counts or
   public API responses.

The API can also be inspected directly at `http://127.0.0.1:8000/docs` or with:

```sh
curl -s http://127.0.0.1:8000/api/performance-years
curl -s 'http://127.0.0.1:8000/api/measures?from_year=2025&to_year=2026&page_size=100'
curl -s 'http://127.0.0.1:8000/api/measures/001?from_year=2025&to_year=2026'
curl -s 'http://127.0.0.1:8000/api/measures/001/navigation?from_year=2025&to_year=2026'
```

## M1 boundary

An `unknown` comparison status is expected until M2 publishes authoritative
comparison records. M1 does not infer added, removed, modified, or unchanged
states from roster absence or draft extraction. The What's New feed and AI
Impact content also remain unavailable in API mode rather than presenting
fictional claims as production data.
