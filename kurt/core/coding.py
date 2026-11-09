"""Repository coding workflow: inspect, implement, verify and report evidence."""
import asyncio
import json
from pathlib import Path
import uuid

from kurt.utils.security import redact, write_private_text
from kurt.utils.workspace import workspace


def run_coding_task(task, *, cwd='.', backend='kurt', router=None, max_steps=25, checks=None):
    if not isinstance(task,str) or not task.strip():raise ValueError('A coding task is required')
    if backend not in ('kurt','codex'):raise ValueError('Backend must be kurt or codex')
    from kurt.core.coding_tools import git_inspect, run_checks
    with workspace(cwd) as root:
        before=git_inspect('status')
        if backend=='codex':
            from kurt.core.codex_adapter import run_codex
            result=run_codex(task,cwd=root,mode='workspace-write')
            completed=result['status']=='completed'
            summary=result.get('final_text','')
            observations=[]
        else:
            from kurt.core.orchestrator import analyze_task
            from kurt.core.router import ModelRouter
            from kurt.core.agent_loop import run_agent
            analysis=analyze_task(task)
            result=asyncio.run(run_agent(task,analysis,router or ModelRouter(),cwd=str(root),max_steps=max_steps,tool_profile="coding"))
            completed,summary=result.success,result.final_summary
            observations=[]
            for step in result.steps:
                if step.tool_name=='run_checks':
                    try:check=json.loads(step.tool_result)
                    except (ValueError,TypeError):continue
                    observations.append(check)
        explicit=[run_checks(argv) for argv in (checks or [])]
        # Latest actual result for each distinct check; earlier failed attempts
        # remain visible in the steps but can be repaired and rerun successfully.
        latest={}
        for item in observations+explicit:
            if isinstance(item,dict) and 'argv' in item:latest[json.dumps(item['argv'])]=item
        verification=list(latest.values())
        verified=bool(verification) and all(c.get('status')=='passed' for c in verification)
        after,diff=git_inspect('status'),git_inspect('diff')
        return redact({'id':str(uuid.uuid4()),'backend':backend,'workspace':str(root),
                       'status':'completed' if completed else 'incomplete','summary':summary,
                       'verification':'passed' if verified else 'failed' if verification else 'not_run',
                       'checks':verification,'review':'available' if diff['status']=='passed' else 'unavailable','git_before':before,'git_after':after,'diff':diff,
                       'note':'Git state includes pre-existing edits; untracked file contents are not included in git diff. Completion is separate from verification.'})


def register_commands(app):
    import typer
    @app.command('code')
    def code(task: str, cwd: Path=typer.Option(Path('.'),'--cwd'), backend: str=typer.Option('kurt','--backend'),
             steps: int=typer.Option(25,'--steps',min=1,max=100),
             check: list[str]=typer.Option(None,'--check',help='Repeatable JSON argv array, e.g. ["python3","-m","pytest"]'),
             output: Path=typer.Option(None,'--output',help='Write the redacted report to a private JSON file')):
        """Implement a repository task with real tool results and verification."""
        from kurt.utils.env_loader import load_env
        load_env()
        try:
            checks=[json.loads(value) for value in (check or [])]
            from kurt.core.coding_tools import run_checks
            # Validate all commands before starting a task with side effects.
            for argv in checks:
                if not isinstance(argv,list) or not argv or any(not isinstance(a,str) or '\0' in a for a in argv):
                    raise ValueError('--check must be a nonempty JSON argument array')
            if output:
                from kurt.utils.security import require_public_file
                require_public_file(output)
            report=run_coding_task(task,cwd=cwd,backend=backend,max_steps=steps,checks=checks)
            if output:
                from kurt.utils.security import require_public_file
                require_public_file(output)
                write_private_text(output,json.dumps(report,ensure_ascii=False,indent=2))
            typer.echo(json.dumps(report,ensure_ascii=False,indent=2))
            if report['status']!='completed' or report['verification']=='failed':raise typer.Exit(1)
        except (ValueError,OSError,RuntimeError) as exc:
            typer.echo(redact(str(exc)),err=True);raise typer.Exit(1)
