"""Bounded audio-worker entrypoint; keep native audio drivers out of chat."""
import sys


def play(path):
    import soundfile as sf
    import sounddevice as sd
    info=sf.info(path)
    if not 0<info.duration<=240 or not 0<info.channels<=2 or not 8000<=info.samplerate<=192000:
        raise ValueError('Audio playback exceeds supported duration/format limits.')
    audio,rate=sf.read(path,dtype='float32',always_2d=True)
    try: sd.play(audio,rate,blocking=True)
    finally: sd.stop()


if __name__=='__main__':
    try:
        if len(sys.argv)!=2: raise ValueError('One local audio path is required.')
        play(sys.argv[1])
    except Exception:
        print('Audio playback failed; check the output device and voice dependencies.',file=sys.stderr)
        raise SystemExit(1)
