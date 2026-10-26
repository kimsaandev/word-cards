"""링크 공유용 대표 이미지(og.png, 1200x630)를 만든다. 사용법: python tools/og_image.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

APP = Path(__file__).parent.parent
FONT = "C:/Windows/Fonts/malgunbd.ttf"
W, H = 1200, 630

img = Image.new("RGB", (W, H), "#fff8ef")
d = ImageDraw.Draw(img)

# 왼쪽: 제목
d.text((70, 140), "아기 낱말 카드", font=ImageFont.truetype(FONT, 74), fill="#3b2f2a")
d.text((74, 252), "실사 사진 · 동물 울음소리 · 탈것 소리", font=ImageFont.truetype(FONT, 27), fill="#ff8a3d")
d.text((74, 302), "과일 · 동물 · 탈것 · 가전 · 사물 · 신체", font=ImageFont.truetype(FONT, 25), fill="#8a7b72")
d.text((74, 340), "카드 75장 · 한국어 + 영어", font=ImageFont.truetype(FONT, 25), fill="#8a7b72")
d.rounded_rectangle((70, 410, 430, 482), radius=36, fill="#ff8a3d")
d.text((250, 446), "무료 · 설치 없이 바로", font=ImageFont.truetype(FONT, 29), fill="white", anchor="mm")

# 오른쪽: 카테고리 색 타일 위에 누끼 사진
tiles = [("apple", "#ffe2e0"), ("dog", "#fff0cc"), ("firetruck", "#dcebff"),
         ("lion", "#fff0cc"), ("banana", "#ffe2e0"), ("ball", "#ece4ff")]
size, gap = 150, 18
x0, y0 = W - 60 - (3 * size + 2 * gap), (H - (2 * size + gap)) // 2
for n, (wid, color) in enumerate(tiles):
    x, y = x0 + (n % 3) * (size + gap), y0 + (n // 3) * (size + gap)
    d.rounded_rectangle((x, y, x + size, y + size), radius=32, fill=color)
    im = Image.open(APP / "img" / f"{wid}.webp")
    im.thumbnail((size - 28, size - 28), Image.LANCZOS)
    img.paste(im, (x + (size - im.width) // 2, y + (size - im.height) // 2), im)

img.save(APP / "og.png", optimize=True)
print(APP / "og.png")
