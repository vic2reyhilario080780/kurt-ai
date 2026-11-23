"""Opt-in, public-fixture-only Mistral comparison. Never reads chat history.

Default: mock capture only. --live sends only public prompts, neutral persona,
repository policy/tool schemas, and redacted public technical instructions.
No discovery, private persona/memory, tool execution, fallback or model changes.
Outputs only public-fixture results; keys and raw request headers never saved.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import httpx

from kurt.core.router import ModelRouter
from kurt.persona import KurtPersona
from kurt.capabilities.bridge import NativeToolRouter
from kurt.utils.env_loader import load_env

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'mistral-small-latest'
URL = 'https://api.mistral.ai/v1/chat/completions'
VERIFY = ('Independently audit the proposed answer against the original problem. '
          'Check leading order, convergence of every improper integral, validity of '
          'termwise expansions, requested powers and logarithms, and the remainder proof. '
          'Correct errors; explicitly identify anything you cannot establish. '
          'Do not claim to have run a tool or numerical check without evidence.')
FRESH = ('For real n>=2 let J_n=integral from 0 to 1 of x/(1+n*x^2) dx. '
         'Give an exact formula and the first three nonzero asymptotic terms, '
         'a uniform error bound after those terms, and the exact limit of '
         'n^3*(J_n-log(n)/(2*n)-1/(2*n^2)). Justify the remainder.')


async def capture(prompt, fixed):
    captured = []
    def receive(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"fixture"}}]}\n\ndata: [DONE]\n\n')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'persona.md').write_text('You are Kurt, a helpful assistant. Answer in the user\'s language.')
        (root/'memory.md').write_text('')
        if fixed:
            instructions = (ROOT/'kurt/persona/system_instructions.md').read_text()
            # Public technical rigor only; omit personal introductory bridge note.
            instructions = instructions[instructions.index('You are Kurt, a technical problem solver'):]
            (root/'system_instructions.md').write_text(instructions)
        turn = KurtPersona(root).build(prompt, include_history=False)
        # Freeze timestamp text so repeated payloads are byte-identical.
        system = turn['system_prompt'].split('=== CONTEXT ===')[0] + '=== CONTEXT ===\nComparison fixture; mode: '+turn['mode']
        messages = [{'role':'system','content':system}, {'role':'user','content':prompt}]
        router = ModelRouter(); router.mistral_key='synthetic'; router.strict_selection=True
        with patch.object(router, '_http_client', side_effect=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(receive))), \
             patch('kurt.capabilities.bridge._chat_discovery_summary', return_value=''), \
             patch('kurt.core.execution_preferences.media_target', return_value={'status':'not used in this fixture'}):
            _ = [c async for c in NativeToolRouter(router).route('mistral', MODEL, messages, temperature=turn['temperature'])]
        return captured[0]


def evidence(payload):
    return {'model':payload['model'], 'temperature':payload.get('temperature'),
            'stream':payload['stream'], 'roles':[m['role'] for m in payload['messages']],
            'system_sha256':[hashlib.sha256(m['content'].encode()).hexdigest() for m in payload['messages'] if m['role']=='system'],
            'custom_rigor_present':any('Establish the problem before doing algebra.' in str(m.get('content')) for m in payload['messages']),
            'tool_count':len(payload.get('tools',[])),
            'tool_choice':payload.get('tool_choice'),
            'parallel_tool_calls':payload.get('parallel_tool_calls'),
            'unset_settings':[s for s in ('max_tokens','top_p','random_seed','reasoning_effort') if s not in payload]}


async def infer(payload, direct=False):
    router = ModelRouter(); router.strict_selection=True
    if not router.mistral_key: return {'error':'MISTRAL_API_KEY unavailable'}
    observed=[]
    # Adapter and direct requests share the identical recorded payload. Recording
    # the wire body detects differences without saving keys or private state.
    async def observe(request): observed.append(json.loads(request.content))
    if direct:
        chunks=[]; resolved=[]; tool_calls=False
        async with httpx.AsyncClient(timeout=90, event_hooks={'request':[observe]}) as client:
            async with client.stream('POST', URL, headers={'Authorization':'Bearer '+router.mistral_key}, json=payload) as response:
                if response.status_code!=200: return {'http_status':response.status_code}
                async for line in response.aiter_lines():
                    if not line.startswith('data: ') or line=='data: [DONE]': continue
                    body=json.loads(line[6:]); resolved.append(body.get('model'))
                    for choice in body.get('choices',[]):
                        delta=choice.get('delta',{}); chunks.append(delta.get('content') or '')
                        tool_calls=tool_calls or bool(delta.get('tool_calls'))
        result={'answer':''.join(chunks),'response_models':sorted({m for m in resolved if m}), 'tool_call_requested':tool_calls}
    else:
        with patch.object(router, '_http_client', side_effect=lambda **kw: httpx.AsyncClient(timeout=90,event_hooks={'request':[observe]})):
            chunks=[c async for c in router.route('mistral', MODEL, payload['messages'],
                stream=True,native_tools=payload.get('tools'),temperature=payload.get('temperature'))]
        result={'answer':''.join(chunks)}
    result['wire_equal_to_capture']=observed==[payload]
    return result


async def main(args):
    load_env()
    prompt=(ROOT/'tests/fixtures/technical/calculus_prompt.txt').read_text()
    payloads={name:await capture(p, fixed) for name,p,fixed in (
        ('calculus_baseline',prompt,False), ('calculus_fixed',prompt,True),
        ('fresh_baseline',FRESH,False), ('fresh_fixed',FRESH,True))}
    output={'method':'Neutral persona, empty history/memory; no private session replay; first completion only; no tools executed.',
            'evidence':{name:evidence(p) for name,p in payloads.items()},'runs':[]}
    path=Path(args.output)
    def save(): path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
    save()
    if not args.live: return
    if args.supplement:
        # One-variable ablation: tools omitted in both arms. This avoids
        # treating an unexecuted tool request as a mathematical wrong answer.
        for name in ('fresh_baseline','fresh_fixed'):
            payload=json.loads(json.dumps(payloads[name]))
            for key in ('tools','tool_choice','parallel_tool_calls'): payload.pop(key,None)
            for repeat in range(args.repeats):
                try: result=await infer(payload)
                except Exception as exc: result={'error_type':type(exc).__name__}
                label=f'{name}:no_tools:{repeat+1}'
                output['runs'].append({'label':label,**result}); save()
                print(json.dumps({'label':label,'answer_chars':len(result.get('answer',''))}),flush=True)
        original=(ROOT/'tests/fixtures/technical/calculus_supplied_wrong_answer.txt').read_text()
        for repeat in range(args.repeats):
            payload=json.loads(json.dumps(payloads['calculus_baseline']))
            payload['messages'].extend([{'role':'assistant','content':original},{'role':'user','content':VERIFY}])
            try: result=await infer(payload)
            except Exception as exc: result={'error_type':type(exc).__name__}
            label=f'calculus_supplied_answer:verify:{repeat+1}'
            output['runs'].append({'label':label,**result}); save()
            print(json.dumps({'label':label,'answer_chars':len(result.get('answer',''))}),flush=True)
        return
    for name in payloads:
        for direct in ([False,True] if name=='calculus_baseline' else [False]):
            for repeat in range(args.repeats):
                label=f'{name}:{"direct" if direct else "kurt"}:{repeat+1}'
                try: result=await infer(payloads[name],direct=direct)
                except Exception as exc: result={'error_type':type(exc).__name__}  # no exception bodies/headers
                output['runs'].append({'label':label,**result}); save()
                print(json.dumps({'label':label, 'answer_chars':len(result.get('answer','')),**{k:v for k,v in result.items() if k!='answer'}}),flush=True)
    # Verification is a separate experiment; no default runtime change.
    for name in ('calculus_baseline','fresh_baseline'):
        candidates=[r for r in output['runs'] if r['label'].startswith(name+':kurt:') and r.get('answer')]
        if not candidates: continue
        candidate=candidates[0]['answer']
        for repeat in range(args.repeats):
            payload=json.loads(json.dumps(payloads[name]))
            payload['messages'].extend([{'role':'assistant','content':candidate},{'role':'user','content':VERIFY}])
            try: result=await infer(payload)
            except Exception as exc: result={'error_type':type(exc).__name__}
            label=f'{name}:verify:{repeat+1}'
            output['runs'].append({'label':label,**result}); save()
            print(json.dumps({'label':label,'answer_chars':len(result.get('answer','')),**{k:v for k,v in result.items() if k!='answer'}}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--repeats',type=int,default=2)
    parser.add_argument('--supplement',action='store_true')
    parser.add_argument('--output',default='/tmp/kurt-technical-comparison.json')
    asyncio.run(main(parser.parse_args()))
