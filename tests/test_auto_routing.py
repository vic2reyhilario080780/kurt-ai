"""Semantic routing contracts; synthetic prompts and providers, no network."""
import asyncio
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from rich.console import Console

from kurt.core import auto_routing as routing
from kurt.core.orchestrator import conversation_analysis, TaskType
from kurt.core.execution_preferences import ExecutionSession


POOL = [
    {'id':0,'provider':'groq','model':'planner','tools':True,'vision':False},
    {'id':1,'provider':'openrouter','model':'reasoner','tools':True,'vision':False},
    {'id':2,'provider':'openrouter','model':'vision','tools':True,'vision':True},
]


class Router:
    excluded_providers = set()
    def __init__(self, response=None):
        self.response = response if response is not None else {'candidate_id':1,'task':'reasoning','complexity':'complex'}
        self.calls = []
        self.strict_selection = False
    def _has_key(self, provider): return provider in ('groq','openrouter')
    async def route(self, provider, model, messages, **options):
        self.calls.append((provider,model,messages,options))
        if isinstance(self.response, Exception): raise self.response
        if options.get('stream') is False:
            yield json.dumps(self.response) if not isinstance(self.response, str) else self.response
        else: yield 'Verified fixture answer.'


class AutoRoutingTests(unittest.TestCase):
    def select(self, router, messages=None):
        with patch.object(routing, 'candidates', return_value=POOL):
            return asyncio.run(routing.select_model(router, conversation_analysis(), messages or [{'role':'user','content':'∫₀¹…; justify the remainder.'}]))

    def test_semantic_decision_can_select_reasoner_without_keyword_classifier(self):
        router = Router()
        result = self.select(router)
        self.assertEqual((result.provider,result.model),('openrouter','reasoner'))
        self.assertEqual(result.task_type, TaskType.CHAT)
        self.assertEqual(result.reason, 'Auto: reasoning/complex')
        self.assertFalse(router.calls[0][3]['stream'])
        self.assertNotIn('native_tools', router.calls[0][3])

    def test_invalid_or_failed_selector_keeps_configured_planner(self):
        for response in ('not json', [], {'candidate_id':True}, {'candidate_id':99,'task':'coding','complexity':'complex'},
                         {'candidate_id':1,'task':'delete files','complexity':'complex'}, httpx.ConnectError('synthetic')):
            with self.subTest(response=type(response).__name__):
                result = self.select(Router(response))
                self.assertEqual(result.model, 'planner')

    def test_image_inputs_require_vision_and_are_not_uploaded_to_selector(self):
        router = Router({'candidate_id':2,'task':'vision','complexity':'complex'})
        messages = [{'role':'system','content':'PRIVATE_PERSONA'}, {'role':'user','content':[
            {'type':'text','text':'Explain this diagram.'},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,PRIVATE_IMAGE'}}]}]
        result = self.select(router, messages)
        self.assertEqual(result.model,'vision')
        self.assertEqual(len(router.calls),0)  # only one compatible candidate
        context = routing.routing_context(messages)
        self.assertNotIn('PRIVATE_IMAGE',str(context))
        self.assertNotIn('PRIVATE_PERSONA',str(context))
        self.assertIn('Image attachment',str(context))

    def test_missing_vision_support_stops_before_any_request(self):
        router=Router()
        with patch.object(routing,'candidates',return_value=POOL[:2]):
            with self.assertRaises(routing.AutoRoutingUnavailable):
                asyncio.run(routing.select_model(router,conversation_analysis(),[
                    {'role':'user','content':[{'type':'image_url','image_url':{'url':'synthetic'}}]}]))
        self.assertEqual(router.calls,[])

    def test_catalog_excludes_missing_credentials_and_non_tool_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'models.json').write_text(json.dumps([
                {'id':'reasoner','supported_parameters':['tools','reasoning'],'architecture':{'input_modalities':['text'],'output_modalities':['text']}},
                {'id':'plain','supported_parameters':[]},
                {'id':'image-generator','supported_parameters':['tools'],'architecture':{'output_modalities':['image']}},
            ]))
            with patch('kurt.models.openrouter.CACHE_DIR',root):
                pool=routing.candidates(Router())
        self.assertIn('reasoner',[c['model'] for c in pool])
        self.assertNotIn('plain',[c['model'] for c in pool])
        self.assertNotIn('image-generator',[c['model'] for c in pool])
        self.assertNotIn('mistral',[c['provider'] for c in pool])

    def test_large_catalog_is_bounded_before_selector_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'models.json').write_text(json.dumps([
                {'id':f'model-{i}','description':'catalog text '*1000,
                 'supported_parameters':['tools','reasoning'] if i%2 else ['tools']}
                for i in range(500)]))
            with patch('kurt.models.openrouter.CACHE_DIR',root):
                pool=routing.candidates(Router())
        self.assertLessEqual(len(pool),25)
        self.assertTrue(all(len(c['description'])<=160 for c in pool))
        self.assertTrue(any(c.get('reasoning') for c in pool))

    def test_excluded_provider_and_oversized_latest_task_are_not_sent(self):
        router=Router(); router.excluded_providers={'openrouter'}
        result=self.select(router)
        self.assertEqual(result.provider,'groq')
        router=Router()
        result=self.select(router,[{'role':'user','content':'∫'*30000}])
        self.assertEqual(len(router.calls),0)
        self.assertIn('context budget',result.reason)

    def test_followup_context_keeps_the_problem_and_omits_system_profile(self):
        router=Router()
        messages=[{'role':'system','content':'PRIVATE_PROFILE'},
                  {'role':'user','content':'Prove the uniform asymptotic remainder.'},
                  {'role':'assistant','content':'The proof is unfinished.'},
                  {'role':'user','content':'Sige, tapusin mo.'}]
        self.select(router,messages)
        payload=json.loads(router.calls[0][2][-1]['content'])
        self.assertEqual(payload['conversation'],messages[1:])
        self.assertNotIn('PRIVATE_PROFILE',str(payload))

    def test_chat_stream_really_calls_selected_model_and_records_it(self):
        from kurt import main
        router=Router(); analysis=conversation_analysis()
        execution=ExecutionSession('auto','auto')
        messages=[{'role':'system','content':'POLICY_SENTINEL'},{'role':'user','content':'∫₀¹…'}]
        with patch.object(main,'ModelRouter',return_value=router), \
             patch.object(main,'console',Console(file=io.StringIO())), \
             patch.object(routing,'candidates',return_value=POOL), \
             patch('kurt.capabilities.bridge._chat_discovery_summary',return_value=''), \
             patch.object(main,'save_message') as save:
            answer=asyncio.run(main.stream_response(analysis,messages,'synthetic',False,False,execution=execution))
        self.assertEqual(answer,'Verified fixture answer.')
        self.assertEqual((router.calls[-1][0],router.calls[-1][1]),('openrouter','reasoner'))
        self.assertIn('POLICY_SENTINEL',str(router.calls[-1][2]))
        self.assertEqual(save.call_args.args[-1],'reasoner')
        self.assertEqual(execution.model,'auto')

    def test_explicit_model_and_cli_skip_semantic_selector(self):
        from kurt import main
        for model,cli in (('mistral-small-latest|mistral','auto'),('auto','claude')):
            with self.subTest(model=model,cli=cli):
                router=Router()
                execution=ExecutionSession(model,cli)
                with patch.object(main,'ModelRouter',return_value=router), \
                     patch.object(main,'console',Console(file=io.StringIO())), \
                     patch.object(routing,'select_model') as select, \
                     patch('kurt.capabilities.bridge._chat_discovery_summary',return_value=''):
                    asyncio.run(main.stream_response(execution.analysis(),[{'role':'user','content':'hello'}],'s',True,False,execution=execution))
                select.assert_not_called()

    def test_auto_fallback_displays_and_records_the_actual_answer_model(self):
        from kurt import main
        class FallbackRouter(Router):
            async def route(self, provider, model, messages, **options):
                if options.get('stream') is not False and model == 'reasoner':
                    request=httpx.Request('POST','https://example.test/chat')
                    response=httpx.Response(404,request=request)
                    raise httpx.HTTPStatusError('synthetic',request=request,response=response)
                async for chunk in super().route(provider,model,messages,**options): yield chunk
        router=FallbackRouter(); analysis=conversation_analysis(); output=io.StringIO()
        with patch.object(main,'ModelRouter',return_value=router), \
             patch.object(main,'console',Console(file=output)), \
             patch.object(routing,'candidates',return_value=POOL), \
             patch('kurt.capabilities.bridge._chat_discovery_summary',return_value=''), \
             patch.object(main,'save_message') as save:
            answer=asyncio.run(main.stream_response(analysis,[{'role':'user','content':'∫₀¹…'}],'s',False,False,execution=ExecutionSession('auto','auto')))
        self.assertEqual(answer,'Verified fixture answer.')
        self.assertIn('Trying fallback: groq/planner',output.getvalue())
        self.assertEqual(analysis.model,'planner')
        self.assertEqual(save.call_args.args[-1],'planner')

