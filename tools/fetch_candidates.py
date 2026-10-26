"""Wikimedia Commons에서 단어별 후보 사진을 받아 카테고리별 비교 시트를 만든다.

사용법: python tools/fetch_candidates.py [word_id ...]
결과: tools/cache/cand/<id>/<n>.jpg, tools/cache/cand/<id>/meta.json, tools/cache/sheet_<cat>.jpg
"""
import json
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from words import CATEGORIES, WORDS

ROOT = Path(__file__).parent
CACHE = ROOT / "cache" / "cand"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "ForMyBaby-WordCards/1.0 (personal educational project)"}
N = 8

session = requests.Session()
session.headers.update(UA)


def get(url, **kw):
    for attempt in range(8):
        time.sleep(0.4)
        r = session.get(url, timeout=30, **kw)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 0)) or 5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()


def search(query, limit=N * 2):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": 6, "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 330,
        "iiextmetadatafilter": "LicenseShortName|Artist|LicenseUrl|UsageTerms",
    }
    pages = get(API, params=params).json().get("query", {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        ii = p.get("imageinfo", [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        if min(ii.get("width", 0), ii.get("height", 0)) < 400:
            continue
        meta = ii.get("extmetadata", {})
        out.append({
            "title": p["title"],
            "page": ii.get("descriptionurl"),
            "thumb": ii.get("thumburl"),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "artist": meta.get("Artist", {}).get("value", ""),
        })
        if len(out) >= N:
            break
    return out


def fetch_word(w, force=False):
    wid, _cat, _ko, en, query = w
    d = CACHE / wid
    d.mkdir(parents=True, exist_ok=True)
    if (d / "meta.json").exists() and not force:
        return wid, len(list(d.glob("*.jpg")))
    # query는 "|"로 여러 검색어를 이어 쓸 수 있고, 모자라면 영어 단어만으로 보충
    queries = query.split("|")
    cap = N if len(queries) == 1 else N // 2  # 검색어가 여러 개면 골고루 섞는다
    cands, seen = [], set()
    for q in [*queries, en]:
        taken = 0
        for c in search(q.strip()):
            if c["title"] not in seen and len(cands) < N and (taken < cap or q == en):
                seen.add(c["title"])
                cands.append(c)
                taken += 1
        if len(cands) >= N:
            break
    for old in d.glob("*.jpg"):  # 새 검색 결과와 번호가 어긋나지 않게
        old.unlink()
    for i, c in enumerate(cands):
        (d / f"{i}.jpg").write_bytes(get(c["thumb"]).content)
    (d / "meta.json").write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")
    return wid, len(cands)


def make_sheet(cat):
    cell = 200
    rows = [w for w in WORDS if w[1] == cat]
    sheet = Image.new("RGB", (120 + cell * N, cell * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for r, w in enumerate(rows):
        draw.text((6, r * cell + cell // 2 - 10), w[0], fill="black", font=font)
        for i in range(N):
            f = CACHE / w[0] / f"{i}.jpg"
            if not f.exists():
                continue
            im = Image.open(f).convert("RGB")
            im.thumbnail((cell - 8, cell - 8))
            x, y = 120 + i * cell, r * cell
            sheet.paste(im, (x + 4, y + 4))
            draw.text((x + 6, y + 4), str(i), fill="red", font=font)
        draw.line((0, (r + 1) * cell - 1, sheet.width, (r + 1) * cell - 1), fill="#ccc")
    out = ROOT / "cache" / f"sheet_{cat}.jpg"
    sheet.save(out, quality=80)
    return out


if __name__ == "__main__":
    only = set(sys.argv[1:])
    todo = [w for w in WORDS if not only or w[0] in only]
    for w in todo:
        print(*fetch_word(w, force=bool(only)), flush=True)
    for cat in {w[1] for w in todo}:
        print(make_sheet(cat))
