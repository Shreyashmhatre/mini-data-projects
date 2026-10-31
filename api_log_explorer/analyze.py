import csv
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

FIELDS = ["timestamp", "method", "route", "status", "latency_ms"]
METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "TRACE",
    "CONNECT",
}


def read_requests(source: Path) -> list[dict]:
    records = []
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV header must be exactly: " + ",".join(FIELDS))
        for number, row in enumerate(reader, start=2):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("wrong number of columns")
                timestamp = datetime.fromisoformat(row["timestamp"])
                if timestamp.tzinfo is None:
                    raise ValueError("timestamp must include a timezone")
                status, latency = int(row["status"]), float(row["latency_ms"])
                if (
                    not 100 <= status <= 599
                    or not math.isfinite(latency)
                    or latency < 0
                ):
                    raise ValueError("invalid HTTP status or latency")
                method, route = row["method"].strip(), row["route"].strip()
                if method not in METHODS:
                    raise ValueError("unknown HTTP method")
                if (
                    not route.startswith("/")
                    or len(route) > 200
                    or any(c in route for c in "?#\r\n|")
                ):
                    raise ValueError(
                        "use a sanitized route template without query/fragment"
                    )
                records.append(
                    {
                        "timestamp": timestamp.astimezone(UTC),
                        "method": method,
                        "route": route,
                        "status": status,
                        "latency_ms": latency,
                    }
                )
            except (ValueError, OverflowError) as exc:
                raise ValueError(f"Row {number}: {exc}") from exc
    return records


def percentile(values: list[float], fraction: float) -> float | None:
    if not 0 < fraction <= 1:
        raise ValueError("percentile fraction must be in (0, 1]")
    if not values:
        return None
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


def summarize(records: list[dict]) -> dict:
    total = len(records)
    latencies = [r["latency_ms"] for r in records]
    statuses = Counter(str(r["status"]) for r in records)
    minutes = Counter(r["timestamp"].strftime("%Y-%m-%dT%H:%M:00Z") for r in records)
    routes = []
    for route in sorted({r["route"] for r in records}):
        rows = [r for r in records if r["route"] == route]
        routes.append(
            {
                "route": route,
                "requests": len(rows),
                "errors": sum(r["status"] >= 400 for r in rows),
                "mean_latency_ms": round(mean(r["latency_ms"] for r in rows), 3),
            }
        )
    return {
        "requests": total,
        "successes": sum(200 <= r["status"] < 300 for r in records),
        "client_errors": sum(400 <= r["status"] < 500 for r in records),
        "server_errors": sum(r["status"] >= 500 for r in records),
        "error_rate": sum(r["status"] >= 400 for r in records) / total if total else 0,
        "mean_latency_ms": round(mean(latencies), 3) if latencies else None,
        "p50_ms": percentile(latencies, 0.5),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "percentile_method": "nearest-rank",
        "statuses": dict(sorted(statuses.items())),
        "routes": routes,
        "requests_per_utc_minute": dict(sorted(minutes.items())),
    }


def markdown_report(summary: dict) -> str:
    lines = [
        "# API Log Explorer report",
        "",
        "Offline descriptive analysis; not an attack detector.",
        "",
        f"- Requests: {summary['requests']}",
        f"- HTTP error rate (4xx + 5xx): {summary['error_rate']:.1%}",
        f"- Mean latency: {summary['mean_latency_ms']} ms",
        f"- Nearest-rank p95: {summary['p95_ms']} ms",
        "",
        "## Routes",
        "",
        "| Route | Requests | Errors | Mean latency (ms) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in summary["routes"]:
        lines.append(
            f"| {row['route']} | {row['requests']} | {row['errors']} | {row['mean_latency_ms']} |"
        )
    lines += [
        "",
        "## Volume by UTC minute",
        "",
        "| UTC minute | Requests |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| {minute} | {count} |"
        for minute, count in summary["requests_per_utc_minute"].items()
    )
    lines += [
        "",
        "Empty input has null latency values. Small samples do not establish service capacity.",
        "",
    ]
    return "\n".join(lines)
