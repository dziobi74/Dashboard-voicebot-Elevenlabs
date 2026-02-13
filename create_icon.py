"""Generate a professional voicebot dashboard icon (.ico) and desktop shortcut."""

import os
from PIL import Image, ImageDraw


def create_icon_image(size):
    """Create a single icon at given size with anti-aliasing (render at 4x, downscale)."""
    scale = 4
    s = size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = s // 2, s // 2
    r = s // 2 - scale

    # ── Background: solid purple circle #6c5ce7 ──
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(108, 92, 231, 255))

    # Subtle lighter inner ring for depth
    r2 = int(r * 0.92)
    draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(118, 102, 240, 255))

    # ── Microphone (white, centered slightly above middle) ──
    white = (255, 255, 255, 245)
    white_dim = (255, 255, 255, 200)
    mic_cx = cx
    mic_cy = cy - int(s * 0.06)

    # Mic head (capsule shape)
    mic_w = int(s * 0.085)
    mic_h = int(s * 0.17)
    mic_top = mic_cy - int(s * 0.17)
    draw.rounded_rectangle(
        [mic_cx - mic_w, mic_top, mic_cx + mic_w, mic_top + mic_h],
        radius=mic_w,
        fill=white
    )

    # Mic body (rectangle connecting head to arc)
    body_top = mic_top + mic_h - int(s * 0.025)
    body_bottom = mic_cy + int(s * 0.04)
    draw.rectangle(
        [mic_cx - mic_w, body_top, mic_cx + mic_w, body_bottom],
        fill=white
    )

    # Rounded bottom of body
    draw.rounded_rectangle(
        [mic_cx - mic_w, body_bottom - mic_w, mic_cx + mic_w, body_bottom + int(s * 0.01)],
        radius=mic_w,
        fill=white
    )

    # Mic holder arc (U-shape)
    arc_w = int(s * 0.15)
    arc_top_y = mic_cy - int(s * 0.04)
    arc_bot_y = mic_cy + int(s * 0.12)
    lw = max(scale * 2, int(s * 0.022))
    draw.arc(
        [mic_cx - arc_w, arc_top_y, mic_cx + arc_w, arc_bot_y],
        start=0, end=180,
        fill=white_dim, width=lw
    )

    # Stand vertical
    stand_bottom = mic_cy + int(s * 0.20)
    draw.line(
        [mic_cx, arc_bot_y, mic_cx, stand_bottom],
        fill=white_dim, width=lw
    )

    # Stand base
    base_w = int(s * 0.07)
    draw.line(
        [mic_cx - base_w, stand_bottom, mic_cx + base_w, stand_bottom],
        fill=white_dim, width=lw
    )

    # ── Sound waves (3 arcs, right side) ──
    wave_cx = mic_cx + int(s * 0.02)
    wave_cy = mic_cy - int(s * 0.04)
    wave_lw = max(scale * 2, int(s * 0.018))
    for wr_pct, alpha in [(0.19, 230), (0.25, 170), (0.31, 110)]:
        wr = int(s * wr_pct)
        draw.arc(
            [wave_cx - wr, wave_cy - wr, wave_cx + wr, wave_cy + wr],
            start=-50, end=50,
            fill=(255, 255, 255, alpha),
            width=wave_lw
        )

    # ── Bar chart (bottom, green #00b894) ──
    bar_count = 5
    bar_w = int(s * 0.038)
    bar_gap = int(s * 0.055)
    bar_base_y = cy + int(s * 0.37)
    bar_heights = [0.50, 1.0, 0.35, 0.80, 0.55]
    max_bar_h = int(s * 0.15)
    bar_start_x = cx - int((bar_count - 1) * bar_gap / 2)

    for i, bh in enumerate(bar_heights):
        bx = bar_start_x + i * bar_gap
        bh_px = int(max_bar_h * bh)
        draw.rounded_rectangle(
            [bx - bar_w // 2, bar_base_y - bh_px, bx + bar_w // 2, bar_base_y],
            radius=max(1, bar_w // 4),
            fill=(0, 184, 148, 240)
        )

    # ── Downscale with high-quality anti-aliasing ──
    img = img.resize((size, size), Image.LANCZOS)
    return img


def create_ico(filepath):
    """Create multi-resolution .ico file."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [create_icon_image(s) for s in sizes]

    images[-1].save(
        filepath,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    file_size = os.path.getsize(filepath)
    print(f"Icon created: {filepath} ({file_size:,} bytes, {len(sizes)} sizes)")


def create_desktop_shortcut(icon_path):
    """Create a Windows desktop shortcut using VBScript."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Voicebot Dashboard.lnk")
    app_dir = os.path.dirname(os.path.abspath(__file__))
    bat_path = os.path.join(app_dir, "run.bat")

    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{bat_path}"
oLink.WorkingDirectory = "{app_dir}"
oLink.IconLocation = "{icon_path}"
oLink.Description = "Voicebot Dashboard - ElevenLabs Analytics"
oLink.WindowStyle = 1
oLink.Save
'''
    vbs_path = os.path.join(app_dir, "_create_shortcut.vbs")
    with open(vbs_path, 'w') as f:
        f.write(vbs_content)

    os.system(f'cscript //nologo "{vbs_path}"')
    if os.path.exists(vbs_path):
        os.remove(vbs_path)
    print(f"Desktop shortcut created: {shortcut_path}")


def create_preview_png(icon_path):
    """Save a large preview PNG for verification."""
    preview = create_icon_image(512)
    preview_path = icon_path.replace('.ico', '_preview.png')
    preview.save(preview_path, 'PNG')
    print(f"Preview saved: {preview_path}")


if __name__ == "__main__":
    app_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(app_dir, "voicebot.ico")
    create_ico(ico_path)
    create_preview_png(ico_path)
    create_desktop_shortcut(ico_path)
