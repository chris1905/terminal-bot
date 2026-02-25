"""Sixel/iTerm2 image protocol support."""

import os
import sys
import base64
import struct
import zlib


def detect_image_protocol():
    """Detect terminal image protocol support.
    Returns 'iterm2', 'sixel', or None."""
    term_program = os.environ.get("TERM_PROGRAM", "")
    if "iTerm" in term_program:
        return "iterm2"

    # Check SIXEL env hint
    if os.environ.get("SIXEL_SUPPORT") == "1":
        return "sixel"

    # Check terminal responses (simplified - avoid blocking)
    term = os.environ.get("TERM", "")
    if "xterm" in term or "kitty" in term:
        # These may support sixel but we can't reliably detect without DA1 query
        pass

    return None


def _make_minimal_png(pixels, width, height):
    """Create a minimal PNG from pixel data (list of rows, each row is list of (r,g,b) tuples)."""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    ihdr = chunk(b'IHDR', ihdr_data)

    # IDAT - raw image data
    raw_data = b''
    for row in pixels:
        raw_data += b'\x00'  # filter byte (none)
        for r, g, b in row:
            raw_data += struct.pack("BBB", r, g, b)

    compressed = zlib.compress(raw_data)
    idat = chunk(b'IDAT', compressed)

    # IEND
    iend = chunk(b'IEND', b'')

    return sig + ihdr + idat + iend


# ─── Pre-defined pixel art for robot face ────────────────────────────────────

# Simple 16x12 robot face pixel art
ROBOT_PIXELS = None  # Generated on demand


def _generate_robot_face(expression="normal"):
    """Generate a small robot face as pixel array."""
    W = 16
    H = 12
    BG = (30, 30, 50)
    BODY = (100, 200, 255)
    EYE_W = (255, 255, 255)
    PUPIL = (30, 30, 30)
    MOUTH = (255, 100, 120)

    pixels = [[BG] * W for _ in range(H)]

    # Body outline (rows 1-10, cols 2-13)
    for r in range(1, 11):
        for c in range(2, 14):
            if r == 1 or r == 10 or c == 2 or c == 13:
                pixels[r][c] = BODY
            else:
                pixels[r][c] = (40, 50, 70)  # inner body

    # Eyes (row 3-5, left eye cols 4-6, right eye cols 9-11)
    for r in range(3, 6):
        for c in range(4, 7):
            pixels[r][c] = EYE_W
        for c in range(9, 12):
            pixels[r][c] = EYE_W

    # Pupils
    if expression == "normal":
        pixels[4][5] = PUPIL
        pixels[4][10] = PUPIL
    elif expression == "happy":
        pixels[3][5] = PUPIL
        pixels[3][10] = PUPIL
    elif expression == "star":
        pixels[4][5] = (255, 255, 100)
        pixels[4][10] = (255, 255, 100)

    # Mouth (row 7-8, cols 5-10)
    for c in range(5, 11):
        pixels[8][c] = MOUTH
    pixels[7][5] = MOUTH
    pixels[7][10] = MOUTH

    return pixels


def render_iterm2_image(pixels, width, height):
    """Render pixels as iTerm2 inline image."""
    png_data = _make_minimal_png(pixels, width, height)
    b64 = base64.b64encode(png_data).decode("ascii")
    # iTerm2 inline image protocol
    return f"\033]1337;File=inline=1;width=20;height=10;preserveAspectRatio=1:{b64}\007"


def render_sixel(pixels, width, height):
    """Render pixels as sixel escape sequence (simplified)."""
    # Register colors
    colors = {}
    color_idx = 0
    output = "\033Pq"  # DCS q - sixel start

    for row in pixels:
        for r, g, b in row:
            key = (r, g, b)
            if key not in colors and color_idx < 256:
                # Convert to percentage (0-100)
                rp = int(r / 255 * 100)
                gp = int(g / 255 * 100)
                bp = int(b / 255 * 100)
                output += f"#{color_idx};2;{rp};{gp};{bp}"
                colors[key] = color_idx
                color_idx += 1

    # Encode pixels in sixel (groups of 6 rows)
    for band_start in range(0, height, 6):
        for x in range(width):
            # For each column, compute sixel character for this band
            for color_key, cidx in colors.items():
                val = 0
                for bit in range(6):
                    y = band_start + bit
                    if y < height and pixels[y][x] == color_key:
                        val |= (1 << bit)
                if val > 0:
                    output += f"#{cidx}" + chr(63 + val)
        output += "$-"  # CR + LF in sixel

    output += "\033\\"  # ST - string terminator
    return output


def get_bot_image(protocol, expression="normal"):
    """Get bot image string for the given protocol."""
    if protocol == "iterm2":
        pixels = _generate_robot_face(expression)
        return render_iterm2_image(pixels, 16, 12)
    elif protocol == "sixel":
        pixels = _generate_robot_face(expression)
        return render_sixel(pixels, 16, 12)
    return ""
