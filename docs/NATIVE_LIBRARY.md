# Kurt-native executable data library

This edition has **10,000 skills, 10,000 workflow-agent definitions and 10,000
plugin recipes**. They are designed specifically for Kurt's native runtime.
Each definition has a concrete domain, metric, operation, input contract and
execution entrypoint. The pack stores complete instructions and agent plans,
not only names or descriptions.

The count represents **100 dataset contracts × 10 metrics × 10 operations per
kind**. It is a set of domain specializations sharing ten analytic algorithms.
It does **not** represent 30,000 independently invented algorithms, 30,000
external app integrations, or 30,000 unrelated general-purpose capabilities.
This scope matters when assessing the count and the tests.

## What works

All three entry types can run locally against user-supplied CSV or JSON records:

| Type | Execution |
|---|---|
| Plugin | Runs its declared analytic operation on its declared measurement |
| Skill | Includes detailed model instructions and binds to an executable plugin |
| Workflow agent | Audits input, stops on invalid measurements, runs its analysis, and returns both reports |

The workflow agents execute declared plans. Their local runner does not use
autonomous LLM reasoning. The existing Kurt AI agent can discover and execute
these workflows through `search_native` and `run_native`; that path still
requires the user's model/provider configuration. Applying a native skill with
`/skill` injects its instructions, but ordinary chat does not automatically
become a tool-executing agent. Use `/library run` for direct execution, or
`kurt agent`/`kurt do` for model-driven tool selection.

The ten operations are descriptive statistics, data quality audit, group
comparison, UTC daily trends, record rankings, IQR outlier review, five-bin
histograms, contribution accounting, normalization, and sequential changes.

Dataset contracts include Shopee/Lazada/TikTok Shop orders, inventory, delivery,
ad performance, content analytics, customer support, SaaS usage, pull requests,
CI pipelines, APIs, cloud costs, n8n/Zapier execution exports, LLM usage,
invoices, project budgets, restaurant orders and nonprofit programs.

These analyze exported records; they do not log into any of those services.
Operations are descriptive and never automatically change prices, place trades,
send messages, publish content or execute external workflows.

## Quick start

```sh
kurt library stats
kurt library search "shopee gross_sales" --kind plugin
kurt library show kurt-plugin--shopee-orders--gross_sales--describe
```

Generate explicitly synthetic input and run a complete example:

```sh
kurt library example kurt-plugin--shopee-orders--gross_sales--describe --output sample-orders.json
kurt plugin run kurt-plugin--shopee-orders--gross_sales--describe --input sample-orders.json --output sales-report.json
```

The sample has eight records and a gross-sales sum of 1160. It is a test
fixture, not actual store revenue. Output paths must be new files.

Use a real UTF-8 export with the exact column names shown by `library show`.
The example Shopee workflow requires `order_id` and numeric `gross_sales`.
Group comparisons also require `shop`. Temporal operations require `ordered_at`
as ISO 8601 strings. Other metrics in the source file are ignored unless the
selected workflow uses them.

```sh
kurt library run kurt-plugin--shopee-orders--gross_sales--group --input orders.csv
kurt skill run kurt-skill--shopee-orders--gross_sales--describe --input orders.csv
kurt agent "analyze these orders" --profile kurt-agent--shopee-orders--gross_sales--describe --data orders.csv
```

With `--profile`, the selected declared plan controls execution; the task text
is only a label and does not change the plan or infer a different metric.
Use `kurt agent` without `--profile` for the existing model-driven agent loop.

In Kurt chat:

```text
/library stats
/library search shopee gross_sales
/library run kurt-agent--shopee-orders--gross_sales--describe "orders.csv"
/skill kurt-skill--shopee-orders--gross_sales--describe
```

The existing skill manager can resolve all 10,000 native skill prompts.
Skill listings show a bounded preview and the full count. Plugin listings show
the 10,000 native plugin count and the search command.

Native plugins support existing enable/disable commands. Disabling a plugin
also blocks skills and agent steps that depend on it:

```sh
kurt plugin disable kurt-plugin--shopee-orders--gross_sales--describe
kurt plugin enable kurt-plugin--shopee-orders--gross_sales--describe
```

## Data rules and interpretation

- Input files are UTF-8 CSV or JSON arrays of record objects, at most 10 MiB,
  100,000 records and 200 columns per record.
- Numeric strings from CSV are accepted. Booleans, blanks, currency symbols,
  thousands separators, nonfinite numbers and nonzero values outside the
  magnitude range 1e-100 to 1e100 are rejected rather than guessed or coerced.
- Duplicate JSON keys and duplicate CSV headers are rejected. Repeated entity
  identifiers are flagged for review, since repeated observations may be valid.
- Dates use UTC calendar days. Naive timestamps are interpreted as UTC. Missing
  periods are not filled. Percentage changes after zero are undefined (`null`).
- Constant-valued normalization returns zero; sample standard deviation needs
  two records and IQR outlier review needs four. Outlier flags are not proof of
  invalid records.
- Source units are not inferred or converted. Sums of scores/rates are sums of
  observations, not business totals. An unweighted mean of recorded rates is
  not a pooled conversion rate. Mixed currencies must be separated upstream.
- No input files are modified; report output refuses implicit overwrites.
- No network calls or arbitrary code execution occur in the native runtime.

## Validation and reproducible authoring

```sh
kurt library verify --output verification.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m kurt.capabilities.authoring
```

The last command rebuilds the checked-in pack from versioned authored domain
contracts, operation procedures and full prompt templates. The resulting
compressed files use deterministic serialization and include integrity hashes.
The pack is bundled in the installable wheel; copying JSON files into the
user's home directory is not required.

The full verification executes **all 30,000 definitions**, checks unique IDs,
bound plugin references, instruction length, completed status, JSON output and
known arithmetic results for every operation. Additional tests cover invalid
input, timezones, zero denominators, signed/constant data, agent stop behavior,
disable propagation, non-destructive files and CLI/chat/agent-tool routing.

See [the recorded verification report](native-library-verification.json).
This proves deterministic local execution against supplied fixtures. It does
not prove the quality of every model's interpretation, correctness of the
user's source data, causal explanations, live integrations, or suitability of
every metric/operation pair for a particular business decision.
