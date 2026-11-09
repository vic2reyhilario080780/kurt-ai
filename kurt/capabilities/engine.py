"""Deterministic analytic operations for Kurt's native recipe library.

No shell, network, account access, generated code or source-file modification.
Rows are supplied explicitly by the user. Domain schemas never infer units.
"""

import csv
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import statistics

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200

METHODS = {
    "describe": ("Descriptive statistics", "Compute count, sum, mean, median, quartiles and sample standard deviation; do not infer causes."),
    "quality": ("Data quality audit", "Locate missing and nonnumeric measurements, missing identifiers and duplicate entity identifiers; preserve row numbers."),
    "group": ("Group comparison", "Aggregate counts, totals and means by the declared group; separate group size from per-record performance."),
    "trend": ("Daily trend", "Aggregate measurements by UTC calendar day; compare totals only between observed days and disclose date gaps."),
    "rank": ("Record ranking", "Rank records by the declared measurement descending, preserving ties in input order and identifying each source row."),
    "outliers": ("IQR outlier review", "Flag values outside inclusive-quartile 1.5-IQR fences; flags are review candidates, not proof of mistakes."),
    "histogram": ("Distribution histogram", "Count records in five equal-width value bins with a closed final bin; keep constant-valued samples in one bin."),
    "contribution": ("Contribution accounting", "Report each record's signed share of the sum; return undefined shares when the total is zero and disclose negative values."),
    "normalize": ("Measurement normalization", "Return min-max values and population z-scores; constant inputs receive zero for both transformations."),
    "changes": ("Sequential change review", "Order observations by timestamp and report absolute and percentage changes; percentage change is undefined after zero."),
}


def load_rows(path):
    """Bounded CSV/JSON loading; never execute spreadsheet formulas."""
    path = Path(path).expanduser()
    if path.suffix.lower() not in (".csv", ".json"):
        raise ValueError("Input must be a .csv or .json file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Input exceeds 10 MiB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Input must use UTF-8 encoding.") from exc
    if path.suffix.lower() == ".csv":
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV requires distinct column names.")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("CSV row has more values than column names.")
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise ValueError("Input exceeds 100,000 rows.")
    else:
        def pairs(items):
            output = {}
            for key, value in items:
                if key in output:
                    raise ValueError("JSON contains duplicate keys.")
                output[key] = value
            return output
        rows = json.loads(text, object_pairs_hook=pairs)
    validate_rows(rows)
    return rows


def validate_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Input must be a nonempty list of record objects.")
    if len(rows) > MAX_ROWS:
        raise ValueError("Input exceeds 100,000 rows.")
    if any(not isinstance(row, dict) or len(row) > MAX_COLUMNS or
           any(not isinstance(k, str) for k in row) for row in rows):
        raise ValueError("Each record must have at most 200 string-named columns.")


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Measurement is not numeric.")
    try:
        parsed = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Measurement is not numeric.") from exc
    if not math.isfinite(parsed) or abs(parsed) > 1e100 or (parsed != 0 and abs(parsed) < 1e-100):
        raise ValueError("Measurement must be zero or finite with magnitude between 1e-100 and 1e100.")
    return parsed


def scalar(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)) or str(value).strip() == "":
        raise ValueError("Identifier/group must be a nonempty string or number.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Identifier/group must be finite.")
    return str(value)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamps must be ISO 8601 strings.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Timestamps must be valid ISO 8601 strings.") from exc
    # A date or naive timestamp is interpreted as UTC, explicitly in the output.
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def audit(rows, profile, metric):
    issues = []
    seen = {}
    for index, row in enumerate(rows, 1):
        if row.get(metric) is None or row.get(metric) == "":
            issues.append({"row": index, "field": metric, "issue": "missing_measurement"})
        else:
            try:
                number(row[metric])
            except ValueError:
                issues.append({"row": index, "field": metric, "issue": "invalid_measurement"})
        try:
            entity = scalar(row.get(profile["entity"]))
            if entity in seen:
                issues.append({"row": index, "field": profile["entity"], "issue": "repeated_entity", "first_row": seen[entity]})
            else:
                seen[entity] = index
        except ValueError:
            issues.append({"row": index, "field": profile["entity"], "issue": "missing_or_invalid_entity"})
    return {"row_count": len(rows), "issue_count": len(issues), "issues": issues,
            "note": "Repeated entities can be valid repeated observations; review before deduplicating."}


def analyze(rows, profile, metric, method):
    validate_rows(rows)
    if method not in METHODS or metric not in profile["metrics"]:
        raise ValueError("Unknown metric or operation for this dataset contract.")
    base = {"domain": profile["id"], "metric": metric, "method": method,
            "input_rows": len(rows), "notes": ["Descriptive analysis of supplied records; no live service access.",
            "Metric units are supplied by the caller; no currency or unit conversions are inferred."]}
    if method == "quality":
        return {**base, "result": audit(rows, profile, metric)}
    values, ids = [], []
    for index, row in enumerate(rows, 1):
        try:
            values.append(number(row.get(metric)))
            ids.append(scalar(row.get(profile["entity"])))
        except ValueError as exc:
            raise ValueError(f"Row {index}: {exc} Run the quality recipe to locate input problems.") from exc
    total = math.fsum(values)
    if method == "describe":
        quartiles = statistics.quantiles(values, method="inclusive") if len(values) >= 2 else [values[0]] * 3
        result = {"count": len(values), "sum": total, "mean": statistics.fmean(values),
                  "median": statistics.median(values), "minimum": min(values), "maximum": max(values),
                  "q1": quartiles[0], "q3": quartiles[2],
                  "sample_stdev": statistics.stdev(values) if len(values) >= 2 else None}
    elif method == "group":
        groups = {}
        for index, (row, value) in enumerate(zip(rows, values), 1):
            try:
                key = scalar(row.get(profile["group"]))
            except ValueError as exc:
                raise ValueError(f"Row {index}: missing or invalid {profile['group']}.") from exc
            groups.setdefault(key, []).append(value)
        result = [{"group": k, "count": len(v), "sum": math.fsum(v), "mean": statistics.fmean(v)}
                  for k, v in sorted(groups.items())]
    elif method in ("trend", "changes"):
        timed = []
        for index, (row, value) in enumerate(zip(rows, values), 1):
            try:
                dt = timestamp(row.get(profile["date"]))
            except ValueError as exc:
                raise ValueError(f"Row {index}: invalid {profile['date']}; use ISO 8601.") from exc
            timed.append((dt, index, value))
        timed.sort(key=lambda item: (item[0], item[1]))
        base["notes"].append("Dates are grouped in UTC; naive timestamps are interpreted as UTC. Missing dates are not filled.")
        result = []
        if method == "trend":
            days = {}
            for dt, index, value in timed:
                days.setdefault(dt.date(), []).append(value)
            previous, previous_day = None, None
            for day, group_values in sorted(days.items()):
                subtotal = math.fsum(group_values)
                result.append({"date": day.isoformat(), "count": len(group_values), "sum": subtotal,
                               "mean": statistics.fmean(group_values),
                               "change": None if previous is None else subtotal - previous,
                               "days_since_previous": None if previous_day is None else (day - previous_day).days})
                previous, previous_day = subtotal, day
        else:
            previous = None
            for dt, index, value in timed:
                result.append({"row": index, "entity": ids[index - 1], "timestamp": dt.isoformat(), "value": value,
                               "change": None if previous is None else value - previous,
                               "percent_change": None if previous in (None, 0) else 100 * (value - previous) / abs(previous)})
                previous = value
            base["notes"].append("Percent change uses abs(previous) as denominator; it is undefined after zero.")
    elif method == "rank":
        order = sorted(range(len(values)), key=lambda i: (-values[i], i))
        result = [{"position": pos, "row": i + 1, "entity": ids[i], "value": values[i]}
                  for pos, i in enumerate(order, 1)]
        base["notes"].append("Positions are ordinal; equal values retain input order.")
    elif method == "outliers":
        if len(values) < 4:
            result = {"status": "insufficient_data", "minimum_rows": 4, "flagged": []}
        else:
            q1, _, q3 = statistics.quantiles(values, method="inclusive")
            iqr = q3 - q1
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            result = {"status": "computed", "q1": q1, "q3": q3, "lower_fence": low, "upper_fence": high,
                      "flagged": [{"row": i + 1, "entity": ids[i], "value": v}
                                  for i, v in enumerate(values) if v < low or v > high]}
        base["notes"].append("Outlier flags identify review candidates and are not evidence of invalid data.")
    elif method == "histogram":
        low, high = min(values), max(values)
        if low == high:
            result = [{"lower": low, "upper": high, "upper_inclusive": True, "count": len(values)}]
        else:
            width = (high - low) / 5
            bins = [0] * 5
            for value in values:
                bins[min(4, max(0, int((value - low) / width)))] += 1
            result = [{"lower": low + i * width, "upper": high if i == 4 else low + (i + 1) * width,
                       "upper_inclusive": i == 4, "count": bins[i]} for i in range(5)]
    elif method == "contribution":
        result = {"total": total, "records": [{"row": i + 1, "entity": ids[i], "value": v,
                  "share_percent": None if total == 0 else 100 * (v / total)} for i, v in enumerate(values)]}
        if total == 0:
            base["notes"].append("Shares are undefined because the signed total is zero.")
        if any(v < 0 for v in values):
            base["notes"].append("Negative values produce signed shares, which may lie outside 0–100 percent.")
    elif method == "normalize":
        low, high, mean, sd = min(values), max(values), statistics.fmean(values), statistics.pstdev(values)
        result = [{"row": i + 1, "entity": ids[i], "value": v,
                   "min_max": 0 if high == low else (v - low) / (high - low),
                   "z_score": 0 if sd == 0 else (v - mean) / sd} for i, v in enumerate(values)]
    return {**base, "result": result}


def sample_rows(profile):
    """Shared deterministic fixture with zeros, ties and an extreme."""
    numbers = [0, 10, 10, 20, 30, 40, 50, 1000]
    return [{profile["entity"]: f"record-{i + 1}", profile["group"]: "A" if i % 2 == 0 else "B",
             profile["date"]: f"2026-01-{i + 1:02d}T12:00:00Z",
             **{metric: value for metric in profile["metrics"]}}
            for i, value in enumerate(numbers)]
