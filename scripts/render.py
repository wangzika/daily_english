import os
import math
import json
import wave
import subprocess
from typing import List, Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from piper.phonemize_espeak import EspeakPhonemizer

# Initialize phonemizer once
_phonemizer = None

def get_phonemizer() -> EspeakPhonemizer:
    global _phonemizer
    if _phonemizer is None:
        _phonemizer = EspeakPhonemizer()
    return _phonemizer

def extract_word_phonetics(sentence: str) -> List[Tuple[str, str]]:
    """Extracts American English IPA for each word in the sentence."""
    ph = get_phonemizer()
    # Clean text to get word tokens
    clean_text = sentence.replace(",", " ").replace(".", " ").replace("?", " ").replace("!", " ").replace(";", " ")
    words = [w.strip() for w in clean_text.split() if w.strip()]
    results = []
    for w in words:
        # Strip outer quotes or punctuation while keeping apostrophe in words like haven't
        w_clean = w.strip("'\"")
        if not w_clean:
            continue
        try:
            phones = ph.phonemize("en-us", w_clean)[0]
            ipa = "".join(phones).strip(".")
            results.append((w_clean, f"/{ipa}/"))
        except Exception:
            results.append((w_clean, ""))
    return results

def create_gradient_bg(width: int, height: int, center_color=(18, 48, 36), edge_color=(7, 18, 13)) -> Image.Image:
    """Creates a mathematically smooth, band-free radial dark green gradient background using NumPy."""
    cx, cy = width * 0.48, height * 0.42
    max_radius = math.hypot(width, height) * 0.65
    
    y, x = np.ogrid[:height, :width]
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_radius
    factor = np.clip(dist ** 1.45, 0.0, 1.0)[:, :, None]
    
    c_center = np.array(center_color, dtype=np.float32)
    c_edge = np.array(edge_color, dtype=np.float32)
    
    arr = (c_center * (1.0 - factor) + c_edge * factor).astype(np.uint8)
    return Image.fromarray(arr, "RGB")

def wrap_english_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps English text intelligently to balanced 2 lines."""
    if "\n" in text:
        return text.split("\n")
        
    words = text.split()
    if not words:
        return [""]
    
    bbox = draw.textbbox((0, 0), text, font=font)
    if (bbox[2] - bbox[0]) <= max_width and len(words) <= 4:
        return [text]
        
    mid = len(words) // 2
    line1 = " ".join(words[:mid+1])
    line2 = " ".join(words[mid+1:])
    
    b1 = draw.textbbox((0, 0), line1, font=font)
    b2 = draw.textbbox((0, 0), line2, font=font)
    if (b1[2] - b1[0]) <= max_width and (b2[2] - b2[0]) <= max_width and line2:
        return [line1, line2]
        
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines

def render_scene_card(
    config: Dict[str, Any],
    english_text: str,
    chinese_text: str,
    phonetics: List[Tuple[str, str]],
    show_phonetics: bool,
    show_chinese: bool,
    stage_name: str,
    countdown_sec: int = None,
    total_countdown: int = 4,
    sentence_idx: int = 1,
    total_sentences: int = 20,
    output_path: str = ""
):
    """
    Renders an individual frame card matching the podcast shadowing style with phonetic table.
    """
    width = config.get("width", 1920)
    height = config.get("height", 1080)
    
    # Fonts
    font_en_path = config.get("font_english", "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf")
    font_ipa_path = config.get("font_ipa", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    font_zh_path = config.get("font_chinese", "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc")
    
    font_en = ImageFont.truetype(font_en_path, 90)
    font_zh = ImageFont.truetype(font_zh_path, 72)
    font_badge_en = ImageFont.truetype(font_en_path, 36)
    font_badge_bold = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 36)
    font_sub = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 26)
    font_cc = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", 26)
    
    font_card_w = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 26)
    font_card_ipa = ImageFont.truetype(font_ipa_path, 28)

    bg = create_gradient_bg(width, height)
    base = bg.convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Top Header Pill: "VibeEnglish  PODCAST"
    pill_w, pill_h = 440, 72
    pill_x0 = (width - pill_w) // 2
    pill_y0 = 55
    pill_x1 = pill_x0 + pill_w
    pill_y1 = pill_y0 + pill_h
    
    draw.rounded_rectangle(
        [pill_x0, pill_y0, pill_x1, pill_y1],
        radius=36,
        fill=(18, 34, 26, 215),
        outline=(55, 82, 68, 220),
        width=2
    )
    
    t1 = config.get("header_title", "VibeEnglish")
    t2 = config.get("header_badge", "PODCAST")
    bbox1 = draw.textbbox((0, 0), t1, font=font_badge_en)
    bbox2 = draw.textbbox((0, 0), t2, font=font_badge_bold)
    w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
    w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
    
    gap = 22
    total_inner_w = w1 + gap + w2
    start_x = pill_x0 + (pill_w - total_inner_w) // 2
    y_text = pill_y0 + (pill_h - max(h1, h2)) // 2 - 2
    
    draw.text((start_x, y_text), t1, font=font_badge_en, fill=(248, 222, 68, 255))
    draw.text((start_x + w1 + gap, y_text), t2, font=font_badge_bold, fill=(255, 255, 255, 255))

    # 2. Status Badge / Progress
    status_str = f"Sentence {sentence_idx:02d}/{total_sentences:02d}  •  {stage_name}"
    sb_bbox = draw.textbbox((0, 0), status_str, font=font_sub)
    sb_w = sb_bbox[2] - sb_bbox[0]
    draw.text(((width - sb_w) // 2, pill_y1 + 16), status_str, font=font_sub, fill=(150, 190, 170, 220))

    # 3. English Text with Outer Blue Glow
    max_text_width = width - 360
    lines_en = wrap_english_text(english_text, font_en, max_text_width, draw)
    line_metrics = []
    total_en_h = 0
    line_spacing = 20
    
    for line in lines_en:
        bbox = draw.textbbox((0, 0), line, font=font_en)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        line_metrics.append((line, lw, lh))
        total_en_h += lh
    total_en_h += line_spacing * (len(lines_en) - 1)
    
    # Calculate vertical position
    # If showing phonetics and chinese, adjust start_en_y slightly higher
    if show_phonetics and show_chinese:
        start_en_y = 260
    elif show_phonetics:
        start_en_y = 300
    else:
        start_en_y = 380
    
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    curr_y = start_en_y
    for line, lw, lh in line_metrics:
        lx = (width - lw) // 2
        glow_draw.text((lx, curr_y), line, font=font_en, fill=(45, 120, 255, 255))
        curr_y += lh + line_spacing
        
    glow1 = glow_layer.filter(ImageFilter.GaussianBlur(radius=18))
    glow2 = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
    base = Image.alpha_composite(base, glow1)
    base = Image.alpha_composite(base, glow2)

    # Render sharp white English text
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    curr_y = start_en_y
    for line, lw, lh in line_metrics:
        lx = (width - lw) // 2
        text_draw.text((lx, curr_y), line, font=font_en, fill=(255, 255, 255, 255))
        curr_y += lh + line_spacing

    # 4. Phonetic Pronunciation Table (Cards)
    if show_phonetics and phonetics:
        badge_gap = 16
        card_h = 96
        max_row_w = width - 200
        
        # Measure badges
        badge_data = []
        for w, ipa in phonetics:
            b1 = text_draw.textbbox((0, 0), w, font=font_card_w)
            b2 = text_draw.textbbox((0, 0), ipa, font=font_card_ipa)
            bw = max(b1[2] - b1[0], b2[2] - b2[0]) + 30
            badge_data.append((w, ipa, bw, b1, b2))
            
        # Group into rows
        rows = []
        cur_row = []
        cur_w = 0
        for b in badge_data:
            bw = b[2]
            if cur_row and (cur_w + badge_gap + bw) > max_row_w:
                rows.append((cur_row, cur_w))
                cur_row = [b]
                cur_w = bw
            else:
                cur_w += (badge_gap + bw) if cur_row else bw
                cur_row.append(b)
        if cur_row:
            rows.append((cur_row, cur_w))
            
        by = curr_y + 30
        for r_badges, r_w in rows:
            bx = (width - r_w) // 2
            for w, ipa, bw, b1, b2 in r_badges:
                # Rounded badge card
                text_draw.rounded_rectangle(
                    [bx, by, bx + bw, by + card_h],
                    radius=12,
                    fill=(14, 32, 25, 225),
                    outline=(55, 105, 82, 230),
                    width=2
                )
                # Word
                w_w = b1[2] - b1[0]
                text_draw.text((bx + (bw - w_w) // 2, by + 14), w, font=font_card_w, fill=(240, 248, 255, 255))
                # IPA
                ipa_w = b2[2] - b2[0]
                text_draw.text((bx + (bw - ipa_w) // 2, by + 52), ipa, font=font_card_ipa, fill=(105, 220, 255, 255))
                bx += bw + badge_gap
            by += card_h + 12
        curr_y = by

    # 5. Chinese Translation (Visible when show_chinese is True)
    if show_chinese and chinese_text:
        zh_bbox = text_draw.textbbox((0, 0), chinese_text, font=font_zh)
        zh_w, zh_h = zh_bbox[2] - zh_bbox[0], zh_bbox[3] - zh_bbox[1]
        zh_x = (width - zh_w) // 2
        zh_y = curr_y + (24 if show_phonetics else 40)
        
        text_draw.text(
            (zh_x, zh_y),
            chinese_text,
            font=font_zh,
            fill=(255, 222, 0, 255),
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255)
        )
        curr_y = zh_y + zh_h

    # 6. Countdown Pill (in Your Turn phase)
    if countdown_sec is not None:
        cd_str = f"Your turn: {countdown_sec}s"
        cd_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 32)
        cd_bbox = text_draw.textbbox((0, 0), cd_str, font=cd_font)
        cd_tw, cd_th = cd_bbox[2] - cd_bbox[0], cd_bbox[3] - cd_bbox[1]
        
        cd_pw, cd_ph = cd_tw + 60, cd_th + 24
        cd_px0 = (width - cd_pw) // 2
        cd_py0 = curr_y + 30
        text_draw.rounded_rectangle(
            [cd_px0, cd_py0, cd_px0 + cd_pw, cd_py0 + cd_ph],
            radius=cd_ph // 2,
            fill=(210, 50, 50, 220) if countdown_sec <= 1 else (35, 140, 90, 220),
            outline=(255, 255, 255, 200),
            width=2
        )
        text_draw.text(
            (cd_px0 + 30, cd_py0 + 10),
            cd_str,
            font=cd_font,
            fill=(255, 255, 255, 255)
        )

    # 7. Bottom CC Subtitle bar (optional, disabled by default)
    if config.get("show_bottom_subtitles", False):
        cc_text = english_text.replace("\n", " ")
        cc_bbox = text_draw.textbbox((0, 0), cc_text, font=font_cc)
        cc_w, cc_h = cc_bbox[2] - cc_bbox[0], cc_bbox[3] - cc_bbox[1]
        cc_pad_x, cc_pad_y = 18, 8
        cc_box_x = (width - cc_w) // 2 - cc_pad_x
        cc_box_y = height - 90
        text_draw.rectangle(
            [cc_box_x, cc_box_y, cc_box_x + cc_w + cc_pad_x * 2, cc_box_y + cc_h + cc_pad_y * 2],
            fill=(0, 0, 0, 180)
        )
        text_draw.text(
            (cc_box_x + cc_pad_x, cc_box_y + cc_pad_y - 2),
            cc_text,
            font=font_cc,
            fill=(255, 255, 255, 240)
        )

    base = Image.alpha_composite(base, overlay)
    base = Image.alpha_composite(base, text_layer)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    base.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path

def generate_silence_wav(output_path: str, duration: float, sample_rate: int = 48000):
    """Generates an exact silent mono 16-bit PCM WAV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    num_samples = int(duration * sample_rate)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)

def convert_to_standard_pcm(input_path: str, output_path: str, sample_rate: int = 48000):
    """Converts any WAV to standard 48kHz mono 16-bit PCM with de-essing, lowpass filtering, and sinc resampling."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", "deesser=i=0.5:m=0.5:f=0.5:s=o,lowpass=f=10000,aresample=resampler=soxr:precision=28,volume=0.95",
        "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def render_timeline_and_video(
    items: List[Dict[str, Any]],
    config: Dict[str, Any],
    work_dir: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Constructs timeline, concatenates audio, generates stage frame cards, and encodes MP4.
    """
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    transition_sec = float(config.get("transition_seconds", 1.0))
    next_sec = float(config.get("next_seconds", 0.3))
    sample_rate = int(config.get("audio_sample_rate", 48000))

    silence_trans_wav = os.path.join(work_dir, f"silence_trans_{transition_sec:.2f}s.wav")
    generate_silence_wav(silence_trans_wav, transition_sec, sample_rate)

    silence_next_wav = os.path.join(work_dir, f"silence_next_{next_sec:.2f}s.wav")
    generate_silence_wav(silence_next_wav, next_sec, sample_rate)

    audio_files_to_concat = []
    video_concat_lines = []
    timeline = []
    
    total_sentences = len(items)
    cursor = 0.0

    print(f"Building timeline, IPA phonetics, and image cards for {total_sentences} sentences...")

    for idx, item in enumerate(items, start=1):
        sid = item["id"]
        prefix = f"{int(sid):03d}" if sid.isdigit() else str(sid)
        pause_sec = float(item["pause_seconds"])

        # Extract IPA phonetics for sentence
        phonetics = extract_word_phonetics(item["english"])

        # 1. Prepare PCM audios
        normal_pcm = os.path.join(work_dir, f"{prefix}_norm_48k.wav")
        slow_pcm = os.path.join(work_dir, f"{prefix}_slow_48k.wav")
        convert_to_standard_pcm(item["normal_wav"], normal_pcm, sample_rate)
        convert_to_standard_pcm(item["slow_wav"], slow_pcm, sample_rate)

        pause_silence_wav = os.path.join(work_dir, f"{prefix}_silence_pause_{pause_sec:.2f}s.wav")
        generate_silence_wav(pause_silence_wav, pause_sec, sample_rate)

        audio_files_to_concat.extend([
            normal_pcm,
            silence_trans_wav,
            slow_pcm,
            pause_silence_wav,
            silence_next_wav
        ])

        dur_norm = item["normal_duration"]
        dur_slow = item["slow_duration"]

        s_record = {
            "id": sid,
            "english": item["english"],
            "chinese": item["chinese"],
            "phonetics": phonetics,
            "stages": {}
        }

        # Stage 1: Listen (Normal speed, English sentence only)
        s1_card = os.path.join(work_dir, f"{prefix}_stage1_listen.png")
        render_scene_card(
            config, item["english"], item["chinese"],
            phonetics=phonetics, show_phonetics=False, show_chinese=False,
            stage_name="Listen",
            sentence_idx=idx, total_sentences=total_sentences, output_path=s1_card
        )
        s_record["stages"]["listen"] = {"start": round(cursor, 3), "duration": round(dur_norm, 3)}
        video_concat_lines.append(f"file '{os.path.abspath(s1_card)}'\nduration {dur_norm:.4f}")
        cursor += dur_norm

        # Stage 2: Transition (1.0s silence, preparing slow listen)
        s2_card = os.path.join(work_dir, f"{prefix}_stage2_trans.png")
        render_scene_card(
            config, item["english"], item["chinese"],
            phonetics=phonetics, show_phonetics=False, show_chinese=False,
            stage_name="Listen slowly",
            sentence_idx=idx, total_sentences=total_sentences, output_path=s2_card
        )
        s_record["stages"]["transition"] = {"start": round(cursor, 3), "duration": round(transition_sec, 3)}
        video_concat_lines.append(f"file '{os.path.abspath(s2_card)}'\nduration {transition_sec:.4f}")
        cursor += transition_sec

        # Stage 3: Listen slowly (Word by Word) -> PHONETIC TABLE APPEARS!
        s3_card = os.path.join(work_dir, f"{prefix}_stage3_slow.png")
        render_scene_card(
            config, item["english"], item["chinese"],
            phonetics=phonetics, show_phonetics=True, show_chinese=False,
            stage_name="Listen slowly (Word by Word)",
            sentence_idx=idx, total_sentences=total_sentences, output_path=s3_card
        )
        s_record["stages"]["slow"] = {"start": round(cursor, 3), "duration": round(dur_slow, 3)}
        video_concat_lines.append(f"file '{os.path.abspath(s3_card)}'\nduration {dur_slow:.4f}")
        cursor += dur_slow

        # Stage 4: Your turn with countdown (English + Phonetics + Chinese + Countdown)
        s_record["stages"]["your_turn"] = {"start": round(cursor, 3), "duration": round(pause_sec, 3)}
        
        full_seconds = int(pause_sec)
        rem_frac = pause_sec - full_seconds
        
        for sec in range(full_seconds, 0, -1):
            s4_tick = os.path.join(work_dir, f"{prefix}_stage4_cd_{sec}.png")
            render_scene_card(
                config, item["english"], item["chinese"],
                phonetics=phonetics, show_phonetics=True, show_chinese=True,
                stage_name="Your turn",
                countdown_sec=sec, total_countdown=int(pause_sec),
                sentence_idx=idx, total_sentences=total_sentences, output_path=s4_tick
            )
            tick_dur = 1.0 + (rem_frac if sec == full_seconds else 0.0)
            video_concat_lines.append(f"file '{os.path.abspath(s4_tick)}'\nduration {tick_dur:.4f}")
            cursor += tick_dur

        # Stage 5: Next (0.3s silence, brief hold)
        s5_card = os.path.join(work_dir, f"{prefix}_stage5_next.png")
        render_scene_card(
            config, item["english"], item["chinese"],
            phonetics=phonetics, show_phonetics=True, show_chinese=True,
            stage_name="Next",
            sentence_idx=idx, total_sentences=total_sentences, output_path=s5_card
        )
        s_record["stages"]["next"] = {"start": round(cursor, 3), "duration": round(next_sec, 3)}
        video_concat_lines.append(f"file '{os.path.abspath(s5_card)}'\nduration {next_sec:.4f}")
        cursor += next_sec

        timeline.append(s_record)

    if video_concat_lines:
        last_file_line = video_concat_lines[-1].split("\n")[0]
        video_concat_lines.append(last_file_line)

    timeline_path = os.path.join(output_dir, "timeline.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump({"total_duration": round(cursor, 3), "sentences": timeline}, f, indent=2, ensure_ascii=False)
    print(f"Timeline saved to: {timeline_path} (Total duration: {cursor:.2f}s)")

    # 1. Concat Audio
    audio_list_file = os.path.join(work_dir, "audio_concat.txt")
    with open(audio_list_file, "w", encoding="utf-8") as f:
        for a_file in audio_files_to_concat:
            f.write(f"file '{os.path.abspath(a_file)}'\n")

    full_audio_wav = os.path.join(work_dir, "full_audio.wav")
    print("Concatenating master audio track with FFmpeg...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", audio_list_file,
        "-c", "copy",
        full_audio_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 2. Concat Video Cards
    video_list_file = os.path.join(work_dir, "video_concat.txt")
    with open(video_list_file, "w", encoding="utf-8") as f:
        f.write("\n".join(video_concat_lines) + "\n")

    # 3. Final MP4 Encoding
    output_mp4 = os.path.join(output_dir, "video.mp4")
    fps = config.get("fps", 30)
    print(f"Encoding final 1080p MP4 ({fps} fps) to: {output_mp4}...")
    
    cmd_encode = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", video_list_file,
        "-i", full_audio_wav,
        "-vf", f"fps={fps},format=yuv420p",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_mp4
    ]
    subprocess.run(cmd_encode, check=True)

    print(f"Video rendering complete: {output_mp4}")
    return {
        "video_path": output_mp4,
        "timeline_path": timeline_path,
        "total_duration": cursor
    }
