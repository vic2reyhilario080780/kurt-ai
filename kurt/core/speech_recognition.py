"""Tagalog/Taglish recognition with explicit routing and quality metadata."""
from dataclasses import dataclass
import asyncio
import json
import math
import os
from pathlib import Path
import re
import wave
import io
import importlib.util

from kurt.core import persona
from kurt.utils.security import redact

MODELS = ('whisper-large-v3','whisper-large-v3-turbo')
BUILTIN_WORDS = ('Kurt','Bhe','Daddy Tito','Vibe','DeepSeek','Copilot','GitHub','iMac',
                 'buksan','ikonekta','i-save','i-push','diga')


def groq_key():
    from kurt.utils.env_loader import ENV_PATH
    from dotenv import dotenv_values
    saved = dotenv_values(ENV_PATH,interpolate=False) if ENV_PATH.is_file() else {}
    value = (saved.get('GROQ_API_KEY',os.environ.get('GROQ_API_KEY','')) or '').strip()
    return value if not value.startswith(('your-','gsk_your','placeholder')) else ''


def options():
    saved = persona.load_persona()
    from kurt.billing.client import active
    provider = saved.get('speech_provider','auto')
    if provider == 'auto': provider = 'groq' if active() or groq_key() else 'local'
    language = saved.get('speech_language','auto' if saved.get('language') == 'taglish' else 'tl')
    model = saved.get('speech_model','whisper-large-v3')
    if provider not in ('groq','local') or language not in ('tl','auto','en') or model not in MODELS:
        raise ValueError('Invalid speech settings; use kurt speech configure.')
    return {'provider':provider,'language':language,'model':model}


def vocabulary_prompt():
    saved = persona.load_persona()
    words = [saved.get('kurt_name','Kurt'),saved.get('user_name',''),
             *saved.get('speech_vocabulary',[]),*BUILTIN_WORDS]
    prompt = 'Usapang Tagalog at English. Mga pangalan at salita: '
    seen = set()
    for value in words:
        if not isinstance(value,str): continue
        word = redact(value).strip()
        if not word or len(word)>48 or '\n' in word or '[REDACTED]' in word or word.casefold() in seen: continue
        candidate = prompt + (', ' if seen else '') + word
        # A byte budget also bounds Whisper BPE token count below its 224 limit.
        if len(candidate.encode())>208: continue
        prompt=candidate; seen.add(word.casefold())
    return prompt


def cached_local_model():
    cache = Path(os.environ.get('HF_HUB_CACHE',str(Path(os.environ.get('HF_HOME',str(Path.home()/'.cache/huggingface')))/'hub')))
    def installed(name):
        try:return importlib.util.find_spec(name) is not None
        except (ImportError,ValueError,AttributeError):return False
    return (installed('faster_whisper') and any(cache.glob('models--Systran--faster-whisper-small/snapshots/*/model.bin'))) or (installed('whisper') and (Path.home()/'.cache/whisper/base.pt').is_file())


@dataclass(frozen=True)
class Transcript:
    text: str
    provider: str
    language: str | None = None
    review_reasons: tuple[str,...] = ()
    confidence: float | None = None  # No fabricated accuracy percentage.


def checked_transcript(data,provider):
    text = data.get('text','')
    if not isinstance(text,str): raise ValueError('Transcription provider returned invalid text.')
    text=text.strip()
    reasons=[]
    if not text: reasons.append('empty transcription')
    segments=data.get('segments') or []
    if not isinstance(segments,(list,tuple)): raise ValueError('Invalid speech quality metadata.')
    if text and not segments: reasons.append('quality metadata unavailable')
    measured=False
    for segment in segments:
        for name,limit,above in [('no_speech_prob',.6,True),('avg_logprob',-1.0,False),('compression_ratio',2.4,True)]:
            value=segment.get(name) if isinstance(segment,dict) else getattr(segment,name,None)
            if isinstance(value,(int,float)):
                measured=True
                if not math.isfinite(value) or (value>limit if above else value<limit):
                    reasons.append(name+' outside quality threshold')
    if text and segments and not measured: reasons.append('quality metadata unavailable')
    words=re.findall(r'\w+',text.casefold())
    if len(words)>=8 and len(set(words))/len(words)<.25: reasons.append('repetitive transcript')
    return Transcript(redact(text),provider,data.get('language'),tuple(dict.fromkeys(reasons)))


def _audio(path):
    source=Path(path)
    with source.open('rb') as stream: raw=stream.read(8*1024*1024+1)
    if len(raw)>8*1024*1024: raise ValueError('Voice recording exceeds the upload limit.')
    with wave.open(io.BytesIO(raw),'rb') as stream:
        if stream.getnchannels()!=1 or stream.getframerate()!=16000 or stream.getsampwidth()!=2 or stream.getnframes()<=0:
            raise ValueError('Voice transcription requires nonempty 16 kHz mono PCM16 WAV.')
    return raw


async def transcribe_online(path):
    config=options()
    from kurt.core.router import ModelRouter
    from kurt.billing.client import active
    key=groq_key()
    if not active() and not key: raise ValueError('Configure GROQ_API_KEY in Kurt /setup for online speech.')
    data={'model':config['model'],'response_format':'verbose_json','temperature':'0',
          'prompt':vocabulary_prompt()}
    if config['language']!='auto': data['language']=config['language']
    # One request, no paid fallback/replay; wallet transport remains authoritative.
    async with ModelRouter()._http_client(timeout=45,follow_redirects=False,trust_env=False) as client:
        response=await client.post('https://api.groq.com/openai/v1/audio/transcriptions',
            headers={'Authorization':'Bearer '+key},data=data,files={'file':('voice.wav',_audio(path),'audio/wav')})
        response.raise_for_status()
        result=response.json()
        if not isinstance(result,dict): raise ValueError('Invalid transcription response.')
        return checked_transcript(result,'groq')


def transcribe(path):
    if options()['provider']=='groq': return asyncio.run(transcribe_online(path))
    from kurt.core.wake_word import transcribe_local
    return transcribe_local(path)


def status():
    config=options()
    from kurt.billing.client import active
    return {**config,'credential_configured':bool(active() or groq_key()) if config['provider']=='groq' else None,
            'cached_local_model':cached_local_model(),'vocabulary_prompt':vocabulary_prompt(),
            'audio_upload':config['provider']=='groq','wake_word':'cached local model only; F5/hotkey otherwise',
            'note':'Recognition/recording/playback still need an explicit test. No model request submitted.'}


def register_commands(app):
    import typer
    group=typer.Typer(help='Configure Tagalog/Taglish speech and personal vocabulary')
    app.add_typer(group,name='speech')
    @group.command('status')
    def show(): typer.echo(json.dumps(status(),ensure_ascii=False,indent=2))
    @group.command('configure')
    def configure(provider:str=typer.Option('groq'),language:str=typer.Option('tl'),model:str=typer.Option('whisper-large-v3'),pause:float=typer.Option(2.,min=.6,max=4.)):
        try: typer.echo(save_options(provider,language,model,pause))
        except ValueError as exc: raise typer.BadParameter(str(exc)) from exc
    @group.command('word-add')
    def add(word:str):
        try: typer.echo(add_word(word))
        except ValueError as exc: raise typer.BadParameter(str(exc)) from exc

    @group.command('test')
    def test(path:str):
        """Transcribe one 16 kHz mono WAV without executing any command. Groq uploads audio and may use credits."""
        from dataclasses import asdict
        try: result=transcribe(path)
        except Exception as exc: raise typer.BadParameter(redact(str(exc))) from exc
        typer.echo(json.dumps(asdict(result),ensure_ascii=False,indent=2))


def save_options(provider,language,model,pause):
    if provider not in ('auto','groq','local') or language not in ('tl','auto','en') or model not in MODELS or not .6<=pause<=4:
        raise ValueError('Provider auto/groq/local; language tl/auto/en; supported Whisper model and pause 0.6–4 seconds required.')
    saved=persona.load_persona();saved.update(speech_provider=provider,speech_language=language,speech_model=model,speech_pause_seconds=pause)
    persona.save_persona(saved)
    return 'Speech settings saved. Groq uploads activated audio and may use credits; local mode uses cached models only. Restart chat after changing provider.'


def add_word(word):
    if not word.strip() or len(word)>48 or '\n' in word or '\0' in word: raise ValueError('Use one short word or name, at most 48 characters.')
    word=redact(word.strip())
    if '[REDACTED]' in word: raise ValueError('Credentials cannot be used as speech vocabulary.')
    saved=persona.load_persona();words=list(saved.get('speech_vocabulary',[]))
    if word.casefold() in {w.casefold() for w in words}: return 'Word is already in the speech vocabulary.'
    if len(words)>=80: raise ValueError('Vocabulary is limited to 80 entries; keep the relevant names only.')
    words.insert(0,word);saved['speech_vocabulary']=words;persona.save_persona(saved)
    return 'Vocabulary saved; newest words have priority within the recognizer prompt limit. Check /speech status to see the active prompt.'


def slash(args):
    import shlex
    parts=shlex.split(args)
    if not parts or parts==['status']: return json.dumps(status(),ensure_ascii=False,indent=2)
    if parts[0]=='word-add' and len(parts)>1: return add_word(' '.join(parts[1:]))
    saved=persona.load_persona()
    if len(parts)==2 and parts[0] in ('language','provider','pause'):
        provider=parts[1] if parts[0]=='provider' else saved.get('speech_provider','auto')
        language=parts[1] if parts[0]=='language' else saved.get('speech_language','auto')
        pause=float(parts[1]) if parts[0]=='pause' else saved.get('speech_pause_seconds',2.)
        return save_options(provider,language,saved.get('speech_model','whisper-large-v3'),pause)
    return 'Usage: /speech status | language tl|auto|en | provider auto|groq|local | pause 2 | word-add <name>'
