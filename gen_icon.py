#!/usr/bin/env python3
"""Generate a simple Pomodoro (tomato) icon for the app bundle."""

import struct
import zlib
import sys
import os

def create_png(width, height, pixel_func):
    """Create a PNG image and return raw bytes."""

    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + chunk + crc

    # IHDR
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)

    # IDAT
    raw_rows = b''
    for y in range(height):
        raw_rows += b'\x00'  # filter byte
        for x in range(width):
            r, g, b, a = pixel_func(x, y)
            raw_rows += struct.pack('BBBB', r, g, b, a)

    compressed = zlib.compress(raw_rows)

    png = b'\x89PNG\r\n\x1a\n'
    png += make_chunk(b'IHDR', ihdr)
    png += make_chunk(b'IDAT', compressed)
    png += make_chunk(b'IEND', b'')
    return png


def draw_icon(size):
    """Draw a tomato-like circle with a highlight."""
    cx = size / 2
    cy = size / 2
    radius = size / 2.3
    leaf_color = (100, 180, 80, 255)
    body_color = (224, 77, 77, 255)
    highlight_color = (255, 160, 140, 255)

    def pixel(x, y):
        dx = x - cx
        dy = y - cy - size * 0.04
        dist = (dx * dx + dy * dy) ** 0.5

        if dist > radius:
            # Transparent background
            return (0, 0, 0, 0)

        # Leaf / stem at top
        if dy < -radius * 0.5 and abs(dx) < radius * 0.25:
            # Small green leaf
            leaf_dist = ((dx / (radius * 0.25)) ** 2 + ((dy + radius * 0.5) / (radius * 0.4)) ** 2) ** 0.5
            if leaf_dist < 1.0:
                return leaf_color

        # Body gradient - lighter at top-left
        t = dist / radius
        r = int(224 + (255 - 224) * (1 - t) * 0.3)
        g = int(77 + (160 - 77) * (1 - t) * 0.2)
        b = int(77 + (140 - 77) * (1 - t) * 0.2)

        # Highlight spot
        if 0.15 < dx / radius < 0.55 and -0.55 < dy / radius < -0.15 and dist < radius * 0.85:
            r = min(255, r + 60)
            g = min(255, g + 50)
            b = min(255, b + 50)

        return (r, g, b, 255)

    return create_png(size, size, pixel)


def main():
    iconset_dir = sys.argv[1] if len(sys.argv) > 1 else '.'

    sizes = {
        'icon_16x16.png': 16,
        'icon_16x16@2x.png': 32,
        'icon_32x32.png': 32,
        'icon_32x32@2x.png': 64,
        'icon_128x128.png': 128,
        'icon_128x128@2x.png': 256,
        'icon_256x256.png': 256,
        'icon_256x256@2x.png': 512,
        'icon_512x512.png': 512,
        'icon_512x512@2x.png': 1024,
    }

    for filename, size in sizes.items():
        png_data = draw_icon(size)
        path = os.path.join(iconset_dir, filename)
        with open(path, 'wb') as f:
            f.write(png_data)
        print(f"  ✓ {filename} ({size}x{size})")


if __name__ == '__main__':
    main()
