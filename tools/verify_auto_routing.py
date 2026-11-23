"""Explicit live selector smoke test using public/synthetic tasks only."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from kurt.core.auto_routing import candidates, select_model
from kurt.core.orchestrator import conversation_analysis
from kurt.core.router import ModelRouter
from kurt.utils.env_loader import load_env


async def main(output):
    load_env()
    router=ModelRouter()
    router.strict_selection=True
    original_route=router.route
    diagnostics=[]
    async def observed_route(*args,**kwargs):
        content=[]
        try:
            async for chunk in original_route(*args,**kwargs):
                content.append(chunk)
                yield chunk
        finally:
            text=''.join(content)
            try:
                body=json.loads(text)
                shape=list(body) if isinstance(body,dict) else type(body).__name__
            except ValueError: shape='not_json'
            diagnostics.append({'chars':len(text),'shape':shape})
    router.route=observed_route
    root=Path(__file__).resolve().parents[1]
    calculus=(root/'tests/fixtures/technical/calculus_prompt.txt').read_text()
    cases={
        'simple_chat':[{'role':'user','content':'Hi Kurt, kumusta?'}],
        'complex_proof':[{'role':'user','content':calculus}],
        'debugging':[{'role':'user','content':'Find and fix the race condition in a Python asyncio cache shared by 20 concurrent tasks. Explain how cancellation can leave stale in-flight entries and design a deterministic test.'}],
        'context_followup':[{'role':'user','content':calculus},
                            {'role':'assistant','content':'The remainder proof remains unresolved.'},
                            {'role':'user','content':'Sige, tapusin mo ang natitirang patunay.'}],
    }
    result={'method':'Selector only; public/synthetic prompts; no private history/persona; no selected task execution.',
            'candidate_count':len(candidates(router)), 'cases':[]}
    for name,messages in cases.items():
        chosen=await select_model(router,conversation_analysis(),messages)
        row={'case':name,'prompt_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest(),
             'provider':chosen.provider,'model':chosen.model,'reason':chosen.reason,
             'selector_diagnostics':diagnostics[-1:]}
        result['cases'].append(row)
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(row,ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',required=True,help='Authorize provider requests/credits for these public fixtures.')
    parser.add_argument('--output',default='/tmp/kurt-auto-routing-live.json')
    asyncio.run(main(parser.parse_args().output))
