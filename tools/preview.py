"""누끼 결과를 색 배경 위에 모아 확인용 시트로 만든다. 사용법: python tools/preview.py [cat]"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from words import WORDS

ROOT = Path(__file__).parent
IMG = ROOT.parent / "img"

cat = sys.argv[1] if len(sys.argv) > 1 else None
items = [w for w in WORDS if (not cat or w[1] == cat) and (IMG / f"{w[0]}.webp").exists()]
cell, cols = 220, 6
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGB", (cell * cols, cell * rows), "#ffd6e0")
draw = ImageDraw.Draw(sheet)
font = ImageFont.load_default(size=16)
for n, w in enumerate(items):
    im = Image.open(IMG / f"{w[0]}.webp")
    im.thumbnail((cell - 20, cell - 30))
    x, y = (n % cols) * cell, (n // cols) * cell
    sheet.paste(im, (x + (cell - im.width) // 2, y + 22 + (cell - 30 - im.height) // 2), im)
    draw.text((x + 6, y + 4), w[0], fill="black", font=font)
out = ROOT / "cache" / f"preview_{cat or 'all'}.jpg"
sheet.save(out, quality=82)
print(out)
