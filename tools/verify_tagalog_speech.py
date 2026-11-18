"""Explicit synthetic Tagalog speech benchmark; no microphone or tool actions.

Uses Edge TTS and one Groq request per sentence, so may consume API credits.
"""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import tempfile
from unittest.mock import patch

from kurt.core import speech_recognition as speech
from kurt.utils.security import redact

SENTENCES = ['Kurt, buksan ang Notes at sabihin mong mahal kita.',
             'Bhe, gamitin natin ang Vibe at DeepSeek para sa project.']


def word_error(reference,hypothesis):
    a=re.findall(r'\w+',reference.casefold());b=re.findall(r'\w+',hypothesis.casefold())
    previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        current=[i]
        for j,right in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=current
    return previous[-1]/max(1,len(a))


async def verify():
    import aiohttp
    import certifi
    import edge_tts
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('ffmpeg is required only for this benchmark conversion.')
    results=[]
    with tempfile.TemporaryDirectory(prefix='kurt-synthetic-speech-') as folder:
        for index,text in enumerate(SENTENCES):
            mp3=Path(folder)/f'{index}.mp3';wav=Path(folder)/f'{index}.wav'
            async with aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where())) as connector:
                await edge_tts.Communicate(text,'fil-PH-AngeloNeural',connector=connector).save(str(mp3))
            subprocess.run([ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-i',str(mp3),
                            '-ac','1','-ar','16000',str(wav)],check=True,timeout=20)
            with patch.object(speech,'options',return_value={'provider':'groq','language':'tl','model':'whisper-large-v3'}):
                result=await speech.transcribe_online(wav)
            results.append({'reference':text,**asdict(result),'word_error_rate':word_error(text,result.text)})
    return {'synthetic_audio_only':True,'microphone_recorded':False,'actions_executed':False,
            'paid_requests':len(results),'results':results,'note':'Synthetic Filipino TTS does not measure the user\'s accent or room/microphone quality.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    try: report=asyncio.run(verify())
    except Exception as exc:
        report={'completed':False,'error':redact(str(exc)),'note':'Stopped without paid fallback or replay.'}
        Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(1)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
