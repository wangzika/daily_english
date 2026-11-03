import os
import io
import wave
import json
import hashlib
from typing import List, Dict, Any
import numpy as np
from piper import PiperVoice, SynthesisConfig

def get_wav_duration(wav_path: str) -> float:
    with wave.open(wav_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)

def synthesize_word_by_word_audio(
    words: List[str],
    voice: PiperVoice,
    syn_config: SynthesisConfig,
    word_pause_seconds: float = 0.28,
    sample_rate: int = 22050
) -> np.ndarray:
    """
    Synthesizes each word independently in full citation form with steady duration,
    and stitches them with a consistent silence pause.
    This guarantees every word has a uniform, deliberate slow teaching tempo
    and avoids unstressed word compression from continuous sentence prosody.
    """
    pause_samples = int(sample_rate * word_pause_seconds)
    silence = np.zeros(pause_samples, dtype=np.int16)
    pad_samples = int(sample_rate * 0.02)
    fade_samples = int(sample_rate * 0.005)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)

    chunks = []
    for w in words:
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            voice.synthesize_wav(w + ".", wf, syn_config=syn_config)
        bio.seek(0)
        with wave.open(bio, "rb") as wf:
            audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        non_silent = np.where(np.abs(audio) > 300)[0]
        if len(non_silent) > 0:
            start = max(0, non_silent[0] - pad_samples)
            end = min(len(audio), non_silent[-1] + pad_samples)
            audio = audio[start:end].copy()

        if len(audio) > fade_samples * 2:
            audio[:fade_samples] = (audio[:fade_samples] * fade_in).astype(np.int16)
            audio[-fade_samples:] = (audio[-fade_samples] * fade_out).astype(np.int16)

        chunks.append(audio)
        chunks.append(silence)

    if not chunks:
        return np.zeros(0, dtype=np.int16)

    return np.concatenate(chunks[:-1])

def synthesize_sentences(
    rows: List[Dict[str, Any]],
    config: Dict[str, Any],
    work_dir: str,
    force: bool = False
) -> List[Dict[str, Any]]:
    """
    Synthesizes normal and slow speed WAV files for each sentence using Piper.
    Loads PiperVoice only once for optimal performance.
    Automatically invalidates cache if sentence text or voice settings change.
    """
    os.makedirs(work_dir, exist_ok=True)
    voice_path = config["voice_model"]

    manifest_path = os.path.join(work_dir, "audio_cache_manifest.json")
    manifest = {}
    if os.path.exists(manifest_path) and not force:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}

    normal_scale = float(config.get("normal_length_scale", 1.0))
    slow_scale = float(config.get("slow_length_scale", 1.25))
    noise_scale = float(config.get("noise_scale", 0.333))
    noise_w_scale = float(config.get("noise_w_scale", 0.6))
    audio_volume = float(config.get("audio_volume", 0.92))
    word_by_word_slow = config.get("word_by_word_slow", True)
    word_pause_seconds = float(config.get("word_pause_seconds", 0.28))

    syn_cfg_normal = SynthesisConfig(
        length_scale=normal_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w_scale,
        volume=audio_volume
    )
    syn_cfg_slow = SynthesisConfig(
        length_scale=slow_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w_scale,
        volume=audio_volume
    )

    voice = None
    results = []

    for item in rows:
        sid = item["id"]
        text = item["english"]
        prefix = f"{int(sid):03d}" if sid.isdigit() else str(sid)

        normal_wav = os.path.join(work_dir, f"{prefix}_normal.wav")
        slow_wav = os.path.join(work_dir, f"{prefix}_slow.wav")

        expected_meta = {
            "text": text,
            "normal_scale": normal_scale,
            "slow_scale": slow_scale,
            "noise_scale": noise_scale,
            "noise_w_scale": noise_w_scale,
            "audio_volume": audio_volume,
            "word_by_word_slow": word_by_word_slow,
            "word_pause_seconds": word_pause_seconds,
            "voice_model": voice_path,
            "method": "discrete_citation_v2"
        }

        cached_meta = manifest.get(sid)
        is_cache_valid = (
            not force
            and cached_meta == expected_meta
            and os.path.exists(normal_wav)
            and os.path.getsize(normal_wav) > 0
            and os.path.exists(slow_wav)
            and os.path.getsize(slow_wav) > 0
        )

        if not is_cache_valid:
            if voice is None:
                print(f"Loading Piper voice model from: {voice_path}...")
                voice = PiperVoice.load(voice_path)

            print(f"[{sid}] Synthesizing normal speed (scale={normal_scale}): {text}")
            with wave.open(normal_wav, "wb") as wf:
                voice.synthesize_wav(text, wf, syn_config=syn_cfg_normal)

            if word_by_word_slow:
                clean_words = [w.strip(",.?!;:\"'") for w in text.split() if w.strip(",.?!;:\"'")]
                if clean_words:
                    print(f"[{sid}] Synthesizing discrete citation words ({len(clean_words)} words, pause={word_pause_seconds}s, scale={slow_scale}): {clean_words}")
                    audio_arr = synthesize_word_by_word_audio(clean_words, voice, syn_cfg_slow, word_pause_seconds)
                    with wave.open(slow_wav, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(22050)
                        wf.writeframes(audio_arr.tobytes())
                else:
                    with wave.open(slow_wav, "wb") as wf:
                        voice.synthesize_wav(text, wf, syn_config=syn_cfg_slow)
            else:
                print(f"[{sid}] Synthesizing continuous slow (scale={slow_scale}): {text}")
                with wave.open(slow_wav, "wb") as wf:
                    voice.synthesize_wav(text, wf, syn_config=syn_cfg_slow)

            manifest[sid] = expected_meta

        dur_normal = get_wav_duration(normal_wav)
        dur_slow = get_wav_duration(slow_wav)

        item_result = dict(item)
        item_result.update({
            "normal_wav": normal_wav,
            "slow_wav": slow_wav,
            "normal_duration": dur_normal,
            "slow_duration": dur_slow,
        })
        results.append(item_result)
        print(f"[{sid}] Durations: Normal={dur_normal:.2f}s, Slow(Word-by-word)={dur_slow:.2f}s")

    # Save updated cache manifest
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return results

if __name__ == "__main__":
    from validate import validate_environment_and_data
    cfg_data = validate_environment_and_data("data/daily_001.csv", "config.json")
    res = synthesize_sentences(cfg_data["rows"][:2], cfg_data["config"], "work/test_audio", force=True)
    print("Synthesize test complete:", res)
