import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kurt.core import media_auto_routing as routing
from kurt.core import persona
from kurt.core.assistant_tools import invoke_assistant
from kurt.core.media_artifacts import I2V_MODELS, REFERENCE_IMAGES


class Router:
    def __init__(self, decision=1, fail_generation=False):
        self.calls=[]; self.decision=decision; self.fail_generation=fail_generation
    def _has_key(self, provider): return provider in ('fal','mistral')
    async def route(self, provider, model, messages, **kwargs):
        self.calls.append((provider,model,messages,kwargs))
        if kwargs.get('stream') is False:
            yield json.dumps({'candidate_id':self.decision})
        elif self.fail_generation: raise RuntimeError('synthetic timeout after submission')
        else: yield 'https://example.org/result.mp4'


class MediaAutoRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        for name,value in (('KURT_DIR',root),('PERSONA_PATH',root/'persona.json')):
            context=patch.object(persona,name,value); context.start(); self.addCleanup(context.stop)
        context=patch('kurt.models.fal.CACHE_DIR',root/'fal'); context.start(); self.addCleanup(context.stop)

    def test_pinned_generator_bypasses_selector(self):
        router=Router()
        settings={'default_video_model':'fal-ai/kling-video/v3/standard/text-to-video|fal'}
        chosen=asyncio.run(routing.select_media_target('video','A cinematic scene',False,router,settings))
        self.assertEqual(chosen['model'],'fal-ai/kling-video/v3/standard/text-to-video')
        self.assertEqual(router.calls,[])

    def test_reference_auto_only_offers_supported_image_to_video(self):
        router=Router()
        pool=routing.media_candidates('video',True,router)
        self.assertEqual({r['model'] for r in pool},I2V_MODELS)
        self.assertEqual(routing.media_candidates('image',True,router),[])
        text_pool=routing.media_candidates('video',False,router)
        self.assertTrue(all(r['model'] not in I2V_MODELS for r in text_pool))

    def test_semantic_selection_uses_prompt_and_validates_id(self):
        router=Router(1)
        result=asyncio.run(routing.select_media_target('image','A precise product photograph',False,router,{}))
        self.assertEqual(result['model'],'google/nano-banana-2.1')
        self.assertEqual(result['routing'],'Auto: semantic media selection')
        data=json.loads(router.calls[0][2][-1]['content'])
        self.assertEqual(data['kind'],'image')
        self.assertIn('product photograph',data['prompt'])
        invalid=asyncio.run(routing.select_media_target('image','A bird',False,Router(999),{}))
        self.assertEqual(invalid['model'],'fal-ai/flux/schnell')
        self.assertIn('selector unavailable',invalid['routing'])

    def test_real_tool_path_generates_once_using_selected_model(self):
        router=Router(1)
        with patch('kurt.core.router.ModelRouter',return_value=router), \
             patch('kurt.core.media_artifacts.finalize_artifact',return_value={'file_verified':True,'path':'/tmp/fixture.mp4'}):
            result=invoke_assistant('generate_media',{'kind':'video','prompt':'A cinematic landscape'})
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['model'],router.calls[-1][1])
        self.assertEqual(len([c for c in router.calls if c[3].get('media_kind')=='video']),1)
        self.assertEqual(router.calls[-1][0],'fal')

    def test_generation_failure_is_not_retried(self):
        router=Router(0,True)
        with patch('kurt.core.router.ModelRouter',return_value=router):
            result=invoke_assistant('generate_media',{'kind':'video','prompt':'A bird'})
        self.assertEqual(result['status'],'unverified')
        self.assertFalse(result['retry_safe'])
        self.assertEqual(len([c for c in router.calls if c[3].get('media_kind')=='video']),1)

    def test_reference_bytes_never_reach_selector_but_reach_generation(self):
        from kurt.core.media_artifacts import FAL_REFERENCE
        class ReferenceRouter(Router):
            async def route(self,*args,**kwargs):
                if kwargs.get('media_kind')=='video':
                    self.reference=FAL_REFERENCE.get()
                async for chunk in super().route(*args,**kwargs):yield chunk
        router=ReferenceRouter(0)
        image='data:image/png;base64,SYNTHETIC_REFERENCE'
        token=REFERENCE_IMAGES.set((image,))
        try:
            with patch('kurt.core.router.ModelRouter',return_value=router), \
                 patch('kurt.core.media_artifacts.finalize_artifact',return_value={'file_verified':True,'path':'/tmp/fixture.mp4'}):
                result=invoke_assistant('generate_media',{'kind':'video','prompt':'Animate this photo','reference_image':0})
        finally:REFERENCE_IMAGES.reset(token)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(result['reference_used'])
        self.assertEqual(router.reference,image)
        self.assertNotIn(image,str(router.calls[0][2]))
        self.assertIn(result['model'],I2V_MODELS)
