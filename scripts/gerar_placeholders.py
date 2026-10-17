"""Gera os PNGs provisórios da identidade visual que ainda não existem.

Uso:  python scripts/gerar_placeholders.py [--force]
Requer Pillow (pip install pillow). Os arquivos gerados carregam uma marca interna
"simetal-placeholder" que o painel /admin/identidade usa para avisar que ainda são provisórios.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin  # noqa: E402

from app.brand import BRAND_DIR, SLOTS  # noqa: E402


def make(slot, force: bool) -> bool:
    if slot.path.exists() and not force:
        return False
    dark = slot.key in {"logo", "logo_dark"}
    bg = (0, 0, 0, 0) if slot.key in {"logo", "logo_mark", "mascot", "institution_logo", "empty_state"} else (232, 238, 240, 255)
    fg = (255, 255, 255, 255) if dark else (27, 107, 122, 255)
    img = Image.new("RGBA", (slot.width, slot.height), bg)
    d = ImageDraw.Draw(img)
    pad = max(2, min(slot.width, slot.height) // 40)
    # moldura tracejada
    step = 24
    for x in range(pad, slot.width - pad, step * 2):
        d.line([(x, pad), (min(x + step, slot.width - pad), pad)], fill=fg, width=3)
        d.line([(x, slot.height - pad), (min(x + step, slot.width - pad), slot.height - pad)], fill=fg, width=3)
    for y in range(pad, slot.height - pad, step * 2):
        d.line([(pad, y), (pad, min(y + step, slot.height - pad))], fill=fg, width=3)
        d.line([(slot.width - pad, y), (slot.width - pad, min(y + step, slot.height - pad))], fill=fg, width=3)
    font = ImageFont.load_default(size=max(12, min(slot.width // 14, slot.height // 4, 56)))
    text = f"{slot.file}\n{slot.width}x{slot.height}"
    box = d.multiline_textbbox((0, 0), text, font=font, align="center")
    d.multiline_text(((slot.width - (box[2] - box[0])) / 2, (slot.height - (box[3] - box[1])) / 2), text, fill=fg, font=font, align="center")
    info = PngImagePlugin.PngInfo()
    info.add_text("simetal-placeholder", "1")
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    img.save(slot.path, pnginfo=info)
    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    created = [s.file for s in SLOTS if make(s, force)]
    print("Criados:", ", ".join(created) if created else "nenhum (todos já existem)")
