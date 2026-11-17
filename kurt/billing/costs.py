"""Provider receipts and optional explicitly configured rate arithmetic; no markup."""
from decimal import Decimal
import json
from .ledger import units


def events(raw, content_type):
    if 'text/event-stream' in content_type:
        for line in raw.decode('utf-8').splitlines():
            if not line.startswith('data:'): continue
            data=line[5:].strip()
            if not data or data=='[DONE]': continue
            try: yield json.loads(data,parse_float=Decimal)
            except ValueError: continue
    else:
        value=json.loads(raw,parse_float=Decimal)
        if isinstance(value,list): yield from value
        else: yield value


def receipt(raw, content_type, provider):
    usage, cost, identity = {}, None, None
    for data in events(raw,content_type):
        if not isinstance(data,dict): continue
        if isinstance(data.get('response'),dict): data=data['response']
        identity=data.get('id') or identity
        if isinstance(data.get('message'),dict): data=data['message']
        metrics=data.get('usage') or data.get('usageMetadata') or {}
        if not isinstance(metrics,dict): continue
        source={}
        if provider=='google' and 'promptTokenCount' in metrics:
            source={'input_tokens':metrics.get('promptTokenCount',0),
                    **({'output_tokens':metrics.get('candidatesTokenCount',0)+metrics.get('thoughtsTokenCount',0)} if 'candidatesTokenCount' in metrics or 'thoughtsTokenCount' in metrics else {}),
                    'cached_tokens':metrics.get('cachedContentTokenCount',0)}
        elif provider=='anthropic':
            source={**({'input_tokens':metrics['input_tokens']} if 'input_tokens' in metrics else {}),
                    **({'output_tokens':metrics['output_tokens']} if 'output_tokens' in metrics else {}),
                    'cached_tokens':metrics.get('cache_read_input_tokens',0), 'cache_write_tokens':metrics.get('cache_creation_input_tokens',0)}
        elif metrics:
            details=metrics.get('prompt_tokens_details') or metrics.get('input_tokens_details') or {}
            source={**({'input_tokens':metrics.get('prompt_tokens',metrics.get('input_tokens'))} if 'prompt_tokens' in metrics or 'input_tokens' in metrics else {}),
                    **({'output_tokens':metrics.get('completion_tokens',metrics.get('output_tokens'))} if 'completion_tokens' in metrics or 'output_tokens' in metrics else {}),
                    'cached_tokens':metrics.get('prompt_cache_hit_tokens',details.get('cached_tokens',0)),
                    'cache_write_tokens':details.get('cache_write_tokens',0)}
        for key,value in source.items():
            if type(value) is int and value>=0: usage[key]=max(value,usage.get(key,0))
        if provider=='openrouter' and 'cost' in metrics:
            # Zero is a valid actual cost. Do not replace it with an estimate.
            cost=units(str(metrics['cost']))
    return {'usage':usage,'cost_units':cost,'provider_id':identity if isinstance(identity,str) else None}
