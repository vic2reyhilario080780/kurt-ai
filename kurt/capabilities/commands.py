"""Native library terminal and chat entrypoints."""

import json
from pathlib import Path
import shlex
from typing import Optional

import typer
from rich.table import Table
from rich.text import Text

from . import runtime


def summary():
    data = runtime.manifest()
    return (f"Kurt native data library: {data['counts']['skill']:,} skills, "
            f"{data['counts']['agent']:,} workflow agents, {data['counts']['plugin']:,} plugins.\n"
            f"{data['domains']} dataset domains; {data['metric_contracts']:,} metric contracts; "
            f"{len(data['operations'])} shared operations.\n{data['scope']}\n"
            "Works on supplied CSV/JSON files. No API key required for local execution. "
            "Natural-language skill interpretation still uses Kurt's configured AI model.")


def save_json(path, data):
    path = Path(path).expanduser()
    # Never overwrite an existing report or a source dataset implicitly.
    content = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


def run_and_write(identity, input_path, output=None, expected_kind=None):
    item = runtime.get_capability(identity)
    if expected_kind and item["kind"] != expected_kind:
        raise ValueError(f"This command requires a {expected_kind} ID.")
    if output and Path(output).expanduser().resolve() == Path(input_path).expanduser().resolve():
        raise ValueError("Output must not be the input file.")
    result = runtime.run_capability(identity, input_path=input_path)
    if output:
        save_json(output, result)
    return result


def chat_command(arguments):
    parts = shlex.split(arguments)
    if not parts or parts[0] == "stats":
        return summary()
    command = parts[0]
    if command == "search":
        return "\n".join(f"{e['id']} | {e['name']}" for e in runtime.search(" ".join(parts[1:]))) or "No matching native workflows."
    if command == "show" and len(parts) == 2:
        return json.dumps(runtime.get_capability(parts[1]), indent=2)
    if command == "run" and len(parts) == 3:
        result = run_and_write(parts[1], parts[2])
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if len(text) > 16000:
            return text[:16000] + "\n[Preview truncated. Use kurt library run --output for the complete report.]"
        return text
    return "Usage: /library stats | search <words> | show <id> | run <id> <quoted-input-path>"


def register_commands(main_app, skill_app, plugin_app, console):
    app = typer.Typer(help="Run Kurt's 30,000 native data workflows (CSV/JSON)")
    main_app.add_typer(app, name="library")

    @app.command("stats")
    def stats():
        console.print(summary(), markup=False)

    @app.command("search")
    def search(query: str = typer.Argument(""), kind: Optional[str] = typer.Option(None),
               limit: int = typer.Option(20, min=1, max=30000)):
        try:
            rows = runtime.search(query, kind, limit)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        table = Table(title=f"Native workflows: {len(rows)} results (limit {limit})")
        table.add_column("ID", overflow="fold")
        table.add_column("Name", overflow="fold")
        for e in rows:
            table.add_row(Text(e["id"]), Text(e["name"]))
        console.print(table)

    @app.command("show")
    def show(identity: str):
        try:
            print(json.dumps(runtime.get_capability(identity), indent=2))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    @app.command("example")
    def example(identity: str, output: Path = typer.Option(..., "--output", "-o")):
        """Write sample input to a new .json file; never treat sample data as live data."""
        try:
            if output.suffix.lower() != ".json":
                raise ValueError("Example output needs a .json extension.")
            save_json(output, runtime.example(identity))
            console.print(f"Wrote sample data: {output}", markup=False)
        except (OSError, ValueError) as exc:
            raise typer.BadParameter(str(exc)) from exc

    def execute(identity, input_path, output, kind=None):
        try:
            result = run_and_write(identity, input_path, output, kind)
        except (OSError, ValueError) as exc:
            raise typer.BadParameter(str(exc)) from exc
        if output:
            console.print(f"Saved {result['status']} report: {output}", markup=False)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        if result["status"] != "completed":
            raise typer.Exit(1)

    @app.command("run")
    def run(identity: str, input_path: Path = typer.Option(..., "--input", "-i"),
            output: Optional[Path] = typer.Option(None, "--output", "-o")):
        """Execute a native plugin, a skill's bound operation, or a workflow agent."""
        execute(identity, input_path, output)

    @skill_app.command("run")
    def skill_run(identity: str, input_path: Path = typer.Option(..., "--input", "-i"),
                  output: Optional[Path] = typer.Option(None, "--output", "-o")):
        """Run a native skill's bound deterministic operation on supplied data."""
        execute(identity, input_path, output, "skill")

    @plugin_app.command("run")
    def plugin_run(identity: str, input_path: Path = typer.Option(..., "--input", "-i"),
                   output: Optional[Path] = typer.Option(None, "--output", "-o")):
        """Execute a native plugin on supplied records."""
        execute(identity, input_path, output, "plugin")

    @app.command("verify")
    def verify(output: Optional[Path] = typer.Option(None, "--output", "-o")):
        """Execute all 30,000 local fixture cases; does not test AI judgment or accounts."""
        report = runtime.verify_library()
        if output:
            save_json(output, report)
        print(json.dumps(report, indent=2))
        if report["errors"]:
            raise typer.Exit(1)
