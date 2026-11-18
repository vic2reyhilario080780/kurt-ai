import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import httpx
import numpy as np

from kurt.core import speech_recognition as speech, persona, wake_word as voice
from kurt.core.router import ModelRouter
from kurt.utils import env_loader


class SpeechTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.env=self.root/'setup.env';self.env.write_text('GROQ_API_KEY=fixture-speech-key\n')
        for obj,key,value in [(persona,'KURT_DIR',self.root),(persona,'PERSONA_PATH',self.root/'persona.json'),(env_loader,'ENV_PATH',self.env)]:
            p=patch.object(obj,key,value);p.start();self.addCleanup(p.stop)
        p=patch.dict(os.environ,{'KURT_WALLET_MODE':'0'});p.start();self.addCleanup(p.stop)
        self.wav=self.root/'voice.wav'
        with wave.open(str(self.wav),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\0\0'*16000)
        speech.save_options('groq','tl','whisper-large-v3',2.)

    def response(self,**updates):
        return {'text':'Kurt, buksan ang Notes.','language':'tagalog','segments':[{'text':'Kurt, buksan ang Notes.',
                'avg_logprob':-.2,'no_speech_prob':.01,'compression_ratio':1.1}],**updates}

    def test_online_request_uses_shared_key_tagalog_and_bounded_vocabulary(self):
        requests=[]
        def handle(request): requests.append(request);return httpx.Response(200,json=self.response())
        with patch.object(ModelRouter,'_http_client',side_effect=lambda **kw:httpx.AsyncClient(transport=httpx.MockTransport(handle))), \
             patch.dict(os.environ,{'GROQ_API_KEY':'stale-key'}):
            result=asyncio.run(speech.transcribe_online(self.wav))
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0].headers['authorization'],'Bearer fixture-speech-key')
        body=requests[0].content
        for value in (b'name="language"',b'\r\ntl\r\n',b'name="prompt"',b'whisper-large-v3',b'verbose_json',b'voice.wav'):
            self.assertIn(value,body)
        self.assertEqual(result.review_reasons,());self.assertIsNone(result.confidence)
        self.assertLessEqual(len(speech.vocabulary_prompt().encode()),208)

    def test_auto_taglish_omits_fixed_language(self):
        speech.save_options('groq','auto','whisper-large-v3-turbo',2.)
        requests=[]
        with patch.object(ModelRouter,'_http_client',side_effect=lambda **kw:httpx.AsyncClient(transport=httpx.MockTransport(
                lambda r: requests.append(r) or httpx.Response(200,json=self.response())))):
            asyncio.run(speech.transcribe_online(self.wav))
        self.assertNotIn(b'name="language"',requests[0].content)

    def test_provider_error_never_replays_or_falls_back(self):
        requests=[]
        def handle(r):requests.append(r);return httpx.Response(503,json={'error':'unavailable'})
        with patch.object(ModelRouter,'_http_client',side_effect=lambda **kw:httpx.AsyncClient(transport=httpx.MockTransport(handle))), \
             patch.object(voice,'transcribe_local') as local:
            with self.assertRaises(httpx.HTTPStatusError):speech.transcribe(self.wav)
        self.assertEqual(len(requests),1);local.assert_not_called()

    def test_bad_audio_is_not_submitted(self):
        self.wav.write_bytes(b'not audio')
        with patch.object(ModelRouter,'_http_client',return_value=httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request:self.fail('Invalid audio was uploaded')))):
            with self.assertRaises((wave.Error,EOFError)):asyncio.run(speech.transcribe_online(self.wav))

    def test_quality_flags_are_not_fabricated_accuracy(self):
        for metadata in [{'no_speech_prob':.95},{'avg_logprob':-1.5},{'compression_ratio':3.0},{'avg_logprob':float('nan')}]:
            result=speech.checked_transcript(self.response(segments=[metadata]),'fixture')
            self.assertTrue(result.review_reasons);self.assertIsNone(result.confidence)
        self.assertTrue(speech.checked_transcript({'text':'hello'},'fixture').review_reasons)
        self.assertTrue(speech.checked_transcript({'text':''},'fixture').review_reasons)

    def test_unclear_utterance_never_dispatches_and_audio_is_removed(self):
        callback=Mock();listener=voice.WakeWordListener(callback=callback,use_hotkey=False);listener._running=True;listener._conversation_mode=True
        result=speech.Transcript('delete files','fixture',review_reasons=('low quality',))
        with patch.object(voice,'record_until_silence',return_value=str(self.wav)),patch.object(voice,'transcribe_utterance',return_value=result), \
             patch.object(voice,'speak'),patch.object(voice,'_cleanup') as clean:
            listener._capture_command('f5-conversation')
        callback.assert_not_called();clean.assert_called_once();self.assertFalse(listener._turn_busy.is_set())

    def test_transcription_failure_pauses_hands_free_without_action(self):
        callback=Mock();listener=voice.WakeWordListener(callback=callback,use_hotkey=False);listener._running=True;listener._conversation_mode=True
        with patch.object(voice,'record_until_silence',return_value=str(self.wav)),patch.object(voice,'transcribe_utterance',side_effect=RuntimeError('fixture')), \
             patch.object(voice,'_cleanup'):
            listener._capture_command('f5-conversation')
        callback.assert_not_called();self.assertFalse(listener._conversation_mode)

    def test_stopping_during_transcription_suppresses_stale_clarification(self):
        listener=voice.WakeWordListener(use_hotkey=False);listener._running=True
        def stopped(_):listener._running=False;return speech.Transcript('unclear','fixture',review_reasons=('low',))
        with patch.object(voice,'record_until_silence',return_value=str(self.wav)),patch.object(voice,'transcribe_utterance',side_effect=stopped), \
             patch.object(voice,'speak') as speak,patch.object(voice,'_cleanup'):
            listener._capture_command('hotkey')
        speak.assert_not_called()

    def test_unclear_loop_is_bounded(self):
        listener=voice.WakeWordListener(use_hotkey=False);listener._running=True;listener._conversation_mode=True
        with patch.object(voice,'speak'):
            for _ in range(3):listener._clarify()
        self.assertFalse(listener._conversation_mode)

    def test_no_cached_wake_model_means_no_background_upload_or_capture(self):
        listener=voice.WakeWordListener(use_hotkey=False);listener._running=True
        def stop(_):listener._running=False
        with patch.object(speech,'cached_local_model',return_value=False),patch.object(voice.time,'sleep',side_effect=stop), \
             patch.object(voice,'record_until_silence') as record,patch.object(voice,'transcribe_utterance') as transcribe:
            listener._listen_loop()
        record.assert_not_called();transcribe.assert_not_called()

    def test_custom_vocabulary_and_language_settings_persist_without_keys(self):
        speech.add_word('Batangas');speech.slash('language auto')
        self.assertIn('Batangas',speech.vocabulary_prompt());self.assertEqual(speech.options()['language'],'auto')
        self.assertNotIn('fixture-speech-key',json.dumps(speech.status()))
        with patch.object(ModelRouter,'_http_client') as client:speech.status()
        client.assert_not_called()

    def test_local_transcription_never_downloads_model_and_preserves_quality(self):
        speech.save_options('local','tl','whisper-large-v3',2.)
        segment=SimpleNamespace(text='Buksan ang Notes.',avg_logprob=-.2,no_speech_prob=.01,compression_ratio=1.)
        model=Mock();model.transcribe.return_value=([segment],SimpleNamespace(language='tl'))
        with patch.object(voice,'_get_whisper_model',return_value=model):result=voice.transcribe_local(self.wav)
        self.assertFalse(result.review_reasons);self.assertIsNone(result.confidence)
        self.assertEqual(model.transcribe.call_args.kwargs['language'],'tl')

    def test_webrtc_reframes_capture_without_losing_samples(self):
        from kurt.core.voice_activity import WebRTCSpeechDetector
        frames=[];model=Mock();model.is_speech.side_effect=lambda data,rate:frames.append((len(data),rate)) or True
        with patch.dict(sys.modules,{'webrtcvad':SimpleNamespace(Vad=lambda _:model)}):detector=WebRTCSpeechDetector()
        for _ in range(15):detector(np.ones(512,dtype=np.float32)*.01)
        self.assertTrue(all(length==960 and rate==16000 for length,rate in frames))
        self.assertEqual(len(frames)*480+len(detector.pending)//2,15*512)

    def test_online_readiness_does_not_require_local_whisper_packages(self):
        with patch('importlib.util.find_spec',side_effect=lambda name:None if name in ('whisper','faster_whisper','onnxruntime') else object()):
            deps=voice.check_dependencies()
        self.assertTrue(deps['can_transcribe']);self.assertTrue(deps['can_detect_speech'])

    def test_standalone_voice_keeps_context_for_follow_up(self):
        from kurt import main
        seen=[]
        async def respond(analysis,messages,*args,**kwargs):
            seen.append(messages);return 'Reply '+str(len(seen))
        def start(callback,**kwargs):
            callback(voice.VoiceEvent('Buksan ang Notes.'))
            callback(voice.VoiceEvent('Iyon ang gamitin natin.'))
            return Mock()
        with patch.object(main,'load_env'),patch.object(main,'init_db'),patch.object(main,'save_message'), \
             patch.object(main,'_try_local_request',return_value=None),patch.object(main,'stream_response',side_effect=respond), \
             patch.object(voice,'check_dependencies',return_value={'can_record':True,'can_transcribe':True,'can_detect_speech':True}), \
             patch.object(voice,'start_listening',side_effect=start),patch.object(voice,'stop_listening'), \
             patch.object(voice,'speak'),patch.object(main.time,'sleep',side_effect=KeyboardInterrupt):
            main.voice(model=None,speak=False,hotkey_only=True)
        self.assertEqual(len(seen),2)
        self.assertEqual([m['content'] for m in seen[1][-3:]],['Buksan ang Notes.','Reply 1','Iyon ang gamitin natin.'])

    def test_audio_worker_decodes_and_blocks_until_playback_completion(self):
        from kurt.core.audio_playback import play
        driver=SimpleNamespace(play=Mock(),stop=Mock())
        with patch.dict(sys.modules,{'sounddevice':driver}):play(str(self.wav))
        self.assertTrue(driver.play.call_args.kwargs['blocking'])
        self.assertEqual(driver.play.call_args.args[1],16000)
        driver.stop.assert_called_once()

    def test_cancelled_wake_detection_cannot_upload_audio(self):
        listener=voice.WakeWordListener(use_hotkey=False);listener._running=True
        def local(_):listener._running=False;return 'Hey Kurt buksan ang Notes'
        with patch.object(speech,'cached_local_model',return_value=True),patch.object(voice,'record_until_silence',return_value=str(self.wav)), \
             patch.object(voice,'transcribe_audio_fast',side_effect=local),patch.object(voice,'transcribe_utterance') as remote,patch.object(voice,'_cleanup'):
            listener._listen_loop()
        remote.assert_not_called()

    def test_cached_model_loader_refuses_network_downloads(self):
        factory=Mock(return_value=Mock())
        with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=factory)}),patch.object(voice,'_whisper_model',None):
            voice._get_whisper_model()
        self.assertTrue(factory.call_args.kwargs['local_files_only'])

    def test_hotkey_mode_does_not_capture_background_audio_with_cached_model(self):
        listener=voice.WakeWordListener(use_hotkey=False,hotkey_only=True);listener._running=True
        def stop(_):listener._running=False
        with patch.object(speech,'cached_local_model',return_value=True),patch.object(voice.time,'sleep',side_effect=stop), \
             patch.object(voice,'record_until_silence') as record:
            listener._listen_loop()
        record.assert_not_called()

    def test_windows_playback_uses_isolated_worker_without_provider_keys(self):
        class Edge:
            def __init__(self,*args,**kwargs):pass
            async def save(self,path):Path(path).write_bytes(b'fixture')
        with patch.dict(sys.modules,{'edge_tts':SimpleNamespace(Communicate=Edge)}), \
             patch.object(voice,'OS','Windows'),patch.dict(os.environ,{'GROQ_API_KEY':'fixture-parent-only'}), \
             patch('kurt.utils.process.run_bounded',return_value={'status':'completed'}) as run:
            voice._speak_sync('Kumusta',{'edge_voice':'fil-PH-AngeloNeural'})
        self.assertIn('kurt.core.audio_playback',run.call_args.args[0])
        self.assertNotIn('GROQ_API_KEY',run.call_args.kwargs['env'])
        self.assertFalse(Path(run.call_args.args[0][-1]).exists())

    def test_wake_word_is_not_a_substring_of_an_unrelated_word(self):
        self.assertIsNone(voice._find_wake_word('Kurtosis is a statistic',['kurt']))
        self.assertEqual(voice._find_wake_word('Hey Kurt, buksan ang Notes',['hey kurt']),'hey kurt')
