import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_gradient_bg(width, height, center_color=(16, 42, 32), edge_color=(6, 17, 12)):
    """Creates a smooth radial dark green gradient background."""
    # Create smaller canvas and upscale with bicubic for speed and ultra-smooth gradient
    sw, sh = width // 4, height // 4
    img = Image.new("RGB", (sw, sh), edge_color)
    draw = ImageDraw.Draw(img)
    
    cx, cy = sw * 0.45, sh * 0.4
    max_radius = math.hypot(sw, sh) * 0.65
    
    for r in range(int(max_radius), 0, -2):
        factor = 1.0 - (r / max_radius)
        # quadratic easing for cinematic glow in center
        factor = factor ** 1.6
        c = (
            int(edge_color[0] + (center_color[0] - edge_color[0]) * factor),
            int(edge_color[1] + (center_color[1] - edge_color[1]) * factor),
            int(edge_color[2] + (center_color[2] - edge_color[2]) * factor),
        )
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
        
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    return img.resize((width, height), Image.Resampling.BICUBIC)

def render_frame(
    english_text="You haven't changed\nat all.",
    chinese_text="你一點都沒變。",
    stage="Listen slowly",
    countdown=None,
    sentence_idx=1,
    total_sentences=20,
    output_path="work/sample_frame.png"
):
    width, height = 1920, 1080
    bg = create_gradient_bg(width, height)
    
    # Fonts
    font_en_path = "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf"
    font_zh_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
    
    font_en = ImageFont.truetype(font_en_path, 88)
    font_zh = ImageFont.truetype(font_zh_path, 68)
    font_badge_en = ImageFont.truetype(font_en_path, 34)
    font_badge_bold = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 34)
    font_sub = ImageFont.truetype("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", 26)

    # Convert to RGBA for alpha compositing
    base = bg.convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Top Header Pill: "VibeEnglish  PODCAST"
    pill_w, pill_h = 420, 70
    pill_x0 = (width - pill_w) // 2
    pill_y0 = 60
    pill_x1 = pill_x0 + pill_w
    pill_y1 = pill_y0 + pill_h
    
    # Pill background with rounded corners and border
    draw.rounded_rectangle(
        [pill_x0, pill_y0, pill_x1, pill_y1],
        radius=35,
        fill=(18, 32, 26, 210),
        outline=(55, 80, 68, 220),
        width=2
    )
    
    # Inside pill: "VibeEnglish" (Yellow) + "PODCAST" (White in badge or bold text)
    t1 = "VibeEnglish"
    t2 = "PODCAST"
    bbox1 = draw.textbbox((0, 0), t1, font=font_badge_en)
    bbox2 = draw.textbbox((0, 0), t2, font=font_badge_bold)
    w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
    w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
    
    gap = 20
    total_inner_w = w1 + gap + w2
    start_x = pill_x0 + (pill_w - total_inner_w) // 2
    y_text = pill_y0 + (pill_h - max(h1, h2)) // 2 - 2
    
    draw.text((start_x, y_text), t1, font=font_badge_en, fill=(245, 220, 70, 255))
    
    # PODCAST label with clean bright white text
    draw.text((start_x + w1 + gap, y_text), t2, font=font_badge_bold, fill=(255, 255, 255, 255))

    # 2. Status / Progress indicator below pill or top corner
    status_text = f"Sentence {sentence_idx:02d}/{total_sentences:02d}  •  {stage}"
    if countdown is not None:
        status_text += f" ({countdown}s)"
    sb_bbox = draw.textbbox((0, 0), status_text, font=font_sub)
    sb_w = sb_bbox[2] - sb_bbox[0]
    draw.text(((width - sb_w) // 2, pill_y1 + 18), status_text, font=font_sub, fill=(140, 180, 160, 200))

    # 3. English Text with Outer Blue/Cyan Glow
    # Measure multi-line English text
    lines_en = english_text.split("\n")
    line_metrics = []
    total_en_h = 0
    line_spacing = 24
    
    for line in lines_en:
        bbox = draw.textbbox((0, 0), line, font=font_en)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        line_metrics.append((line, lw, lh))
        total_en_h += lh
    total_en_h += line_spacing * (len(lines_en) - 1)
    
    # Vertical positioning
    center_y = 510
    start_en_y = center_y - total_en_h // 2 - 40
    
    # Glow layer for English text
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    
    curr_y = start_en_y
    for line, lw, lh in line_metrics:
        lx = (width - lw) // 2
        glow_draw.text((lx, curr_y), line, font=font_en, fill=(45, 125, 255, 255))
        curr_y += lh + line_spacing
        
    # Apply Gaussian blur to create soft neon blue glow
    glow_layer1 = glow_layer.filter(ImageFilter.GaussianBlur(radius=16))
    glow_layer2 = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
    
    # Merge glows onto base
    base = Image.alpha_composite(base, glow_layer1)
    base = Image.alpha_composite(base, glow_layer2)
    
    # 4. Draw sharp white English text on top
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    curr_y = start_en_y
    for line, lw, lh in line_metrics:
        lx = (width - lw) // 2
        text_draw.text((lx, curr_y), line, font=font_en, fill=(255, 255, 255, 255))
        curr_y += lh + line_spacing

    # 5. Chinese Translation with Bright Yellow Fill + Black Stroke
    if chinese_text:
        zh_bbox = text_draw.textbbox((0, 0), chinese_text, font=font_zh)
        zh_w, zh_h = zh_bbox[2] - zh_bbox[0], zh_bbox[3] - zh_bbox[1]
        zh_x = (width - zh_w) // 2
        zh_y = curr_y + 40
        
        # Draw with stroke
        text_draw.text(
            (zh_x, zh_y),
            chinese_text,
            font=font_zh,
            fill=(255, 222, 0, 255),
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255)
        )

    # 6. Bottom subtitle simulation box (optional touch like YouTube CC)
    # Shown in bottom right or subtle bottom
    cc_text = "You haven't changed at all."
    cc_bbox = text_draw.textbbox((0, 0), cc_text, font=font_sub)
    cc_w, cc_h = cc_bbox[2] - cc_bbox[0], cc_bbox[3] - cc_bbox[1]
    cc_pad_x, cc_pad_y = 16, 8
    cc_box_x = (width - cc_w) // 2 - cc_pad_x
    cc_box_y = height - 120
    text_draw.rectangle(
        [cc_box_x, cc_box_y, cc_box_x + cc_w + cc_pad_x * 2, cc_box_y + cc_h + cc_pad_y * 2],
        fill=(0, 0, 0, 190)
    )
    text_draw.text(
        (cc_box_x + cc_pad_x, cc_box_y + cc_pad_y - 2),
        cc_text,
        font=font_sub,
        fill=(255, 255, 255, 240)
    )

    base = Image.alpha_composite(base, overlay)
    base = Image.alpha_composite(base, text_layer)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    base.convert("RGB").save(output_path, "PNG", quality=95)
    print(f"Sample frame rendered to: {output_path}")

if __name__ == "__main__":
    render_frame()
