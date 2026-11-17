"""Isolated entry point for the installed deepseek_agent package (not a new agent implementation)."""
import contextlib
import json
import os
from pathlib import Path
import sys


def main():
    # The package CLI adds automatic test/bug-fix follow-ups even for a simple
    # question. Its public AgentOptions API lets Kurt pass only the user's task.
    from deepseek_cli.agent import AgentOptions, agent_loop
    from openai import OpenAI
    transcript = Path(sys.argv[1])
    prompt = sys.stdin.read()
    options = AgentOptions(model=os.environ['DEEPSEEK_MODEL'],
        system_prompt='You are Kurt\'s DeepSeek agent. Follow only the supplied conversation/task. Filesystem is read-only. Do not run unsolicited tests or change files. Be honest about unavailable tools and incomplete actions.',
        user_prompt=prompt, follow_up=[], workspace=Path.cwd(), read_only=True,
        allow_global_access=False, max_steps=8, verbose=False,
        transcript_path=transcript, tavily_api_key=os.environ.get('TAVILY_API_KEY', 'not-configured'))
    from functools import partial
    client = OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'], base_url=os.environ['DEEPSEEK_BASE_URL'], max_retries=0)
    # This older package omits reasoning_content when replaying tool calls.
    # Use the documented non-thinking mode instead of corrupting tool history.
    client.chat.completions.create = partial(client.chat.completions.create, extra_body={'thinking': {'type': 'disabled'}})
    with contextlib.redirect_stdout(sys.stderr):
        agent_loop(client, options)
    last = json.loads(transcript.read_text().splitlines()[-1])['message'] if transcript.exists() else {}
    if last.get('role') != 'assistant' or last.get('tool_calls') or not last.get('content', '').strip():
        raise RuntimeError('DeepSeek agent returned no final answer; task completion is unverified.')
    print(json.dumps({'status': 'completed', 'final_text': last['content']}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        reason = type(exc).__name__ + ': ' + str(exc)
        for name in ('DEEPSEEK_API_KEY', 'TAVILY_API_KEY'):
            if os.environ.get(name): reason = reason.replace(os.environ[name], '[REDACTED]')
        print(json.dumps({'status': 'failed', 'reason': reason[:1200],
                          'provider_http_status': getattr(exc, 'status_code', None)}))
        raise SystemExit(1)
