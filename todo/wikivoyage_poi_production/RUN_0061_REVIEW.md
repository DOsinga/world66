# Wikivoyage POI production run 0061

Processed batches: 0600

## Result

- Rows reviewed: 50
- Accepted POIs: 0
- Rejected candidates: 50
- Cumulative rows reviewed: 30,000
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 22,365

The final shard was an all-reject batch. Every row had a candidate score of 0.47, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0600 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 50`
- Batch/reject inventory: `batch_files 600`, `reject_files 600`, `missing_rejects 0`, `extra_rejects 0`
- Duplicate sweep: skipped because no POI markdown files were created.
