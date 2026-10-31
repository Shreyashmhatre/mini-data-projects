# Mini Data Projects

Small, reproducible data-analysis exercises. Each project includes its input contract,
fictional sample data, runnable code, tests, and limits—not just a screenshot or a notebook
that depends on hidden files.

## Available project: API Log Explorer

[`api_log_explorer/`](api_log_explorer/) turns a sanitized CSV request log into JSON and
Markdown reports. It summarizes HTTP outcomes, latency percentiles, per-route counts,
and requests per UTC minute.

```bash
python -m api_log_explorer --input data/sample_requests.csv --output output
python -m unittest discover -s tests -v
```

Python 3.12+, standard library only. Generated reports are written to
`output/summary.json` and `output/report.md` (ignored by Git).

### Sample findings

For the **10 invented requests** in the included fixture:

- 6 successful responses, 3 client errors, and 1 server error.
- Overall 4xx/5xx response rate: 40%.
- Mean latency: 19.9 ms; nearest-rank p95: 100 ms.
- `/products` is the most frequent route (5 requests).

These describe the fixture, **not a real service, security experiment, or benchmark**.
An HTTP error does not by itself prove an attack. Percentiles from ten observations
are useful for testing formulas, not capacity planning.

### Input contract

| Column | Meaning |
| --- | --- |
| `timestamp` | ISO 8601 timestamp with an explicit timezone; normalized to UTC |
| `method` | Standard HTTP method such as GET/POST |
| `route` | Sanitized route template beginning `/`; no query string, user IDs, or secrets |
| `status` | Integer HTTP status from 100 to 599 |
| `latency_ms` | Finite, nonnegative numeric measurement |

The program rejects malformed input rather than silently changing denominators.
Missing, extra, or incorrectly ordered headers are errors. It does not collect traffic
or contact external hosts.

### Definitions

- Error rate = responses with status ≥400 / all rows. Redirects are not errors.
- Success count = 2xx responses only.
- Percentiles use **nearest rank**: sorted value at `ceil(p × n)`, starting at one.
- Latency is whatever the source measured; the tool cannot distinguish network time
  from backend processing. The schema is not a gateway-overhead benchmark.

## Next ideas

Compare two saved traffic windows and add a static chart export. These are planned
extensions, not implemented features. AI/ML mini projects will be listed only when
there is corresponding runnable code and evaluation.
