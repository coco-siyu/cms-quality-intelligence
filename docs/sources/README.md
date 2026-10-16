# CMS source inventory

This directory contains the Checkpoint C2.1 research artifacts for the Medicare Shared Savings Program (MSSP) Alternative Payment Model Performance Pathway (APP) Plus measure sets for performance years (PYs) 2025 and 2026.

These files are **review material, not production data**. Every measure row remains a candidate until a reviewer verifies the source files, locators, titles, collection types, and applicable year. Nothing in this directory authorizes publishing records through the public API.

## Artifacts

- [`source-inventory.csv`](source-inventory.csv) records official CMS and CMS-linked source documents, URLs, applicability, revision information, retrieval dates, and review status.
- [`measure-membership-candidates.csv`](measure-membership-candidates.csv) records the proposed PY2025 and PY2026 membership reconciliation.
- [`reconciliation-report.md`](reconciliation-report.md) explains the evidence hierarchy, findings, unresolved questions, verification rules, and proposed PostgreSQL import workflow.

## Current candidate conclusion

| Reconciliation result | Quality IDs | Count |
| --- | --- | ---: |
| PY2025 candidate set | 001, 112, 134, 236, 321, 479 | 6 |
| PY2026 candidate set | 001, 112, 113, 134, 236, 321, 479, 484 | 8 |
| Unchanged membership candidates | 001, 112, 134, 236, 321, 479 | 6 |
| Added membership candidates | 113, 484 | 2 |
| Removed membership candidates | None supported | 0 |

“None supported” is not an inference from absence. It means the reviewed CMS sources positively list all six PY2025 candidates in PY2026 and add two more.

## Review boundary

The inventory was prepared on 2026-10-16. The mutable CMS guidance page and linked bundles must be checked again at verification time. Downloaded artifacts should be retained with content hashes and never overwritten when CMS publishes a new revision.
