"""고른 사진을 원본 해상도로 받아 배경을 제거(누끼)하고 웹앱 데이터를 만든다.

tools/picks.json 형식: {"apple": 2, "eye": {"i": 0, "mode": "round", "crop": [x0, y0, x1, y1]}}
  - 숫자: 후보 번호 (tools/cache/cand/<id>/<n>.jpg)
  - mode "round": 누끼 대신 둥근 사각형으로 잘라냄 (눈·코처럼 얼굴 일부인 경우)
  - crop: 0~1 비율 좌표로 먼저 잘라낼 영역
  - from: 다른 단어의 후보 사진을 쓸 때 그 단어 id (예: 입과 이를 같은 사진에서 잘라냄)

사용법: python tools/process.py [word_id ...]   (인자 없으면 전체)
결과: img/<id>.webp, data/words.js, credits.html
"""
import html
import json
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from fetch_candidates import API, CACHE, get
from sounds import CACHE as SND_CACHE, SOUNDS
from words import CATEGORIES, WORDS

ROOT = Path(__file__).parent
APP = ROOT.parent
FULL = ROOT / "cache" / "full"
OUT = APP / "img"
MAX_SIDE = 720

COVERS = {"fruit": "apple", "animal": "lion", "vehicle": "firetruck",
          "appliance": "ricecooker", "object": "ball", "body": "hand"}

_session = None


def rembg_session():
    global _session
    if _session is None:
        from rembg import new_session
        _session = new_session("isnet-general-use")
    return _session


def pick_of(picks, wid):
    p = picks.get(wid, 0)
    return p if isinstance(p, dict) else {"i": p}


def full_image(wid, i, cand):
    f = FULL / f"{wid}_{i}.jpg"
    if not f.exists():
        params = {"action": "query", "format": "json", "titles": cand["title"],
                  "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1280}
        page = next(iter(get(API, params=params).json()["query"]["pages"].values()))
        FULL.mkdir(parents=True, exist_ok=True)
        f.write_bytes(get(page["imageinfo"][0]["thumburl"]).content)
    return Image.open(f).convert("RGB")


def cutout(im):
    from rembg import remove
    out = remove(im, session=rembg_session(), post_process_mask=True)
    out = drop_specks(out)
    alpha = out.getchannel("A")
    bbox = alpha.point(lambda a: 255 if a > 16 else 0).getbbox()
    return out.crop(bbox) if bbox else out


def drop_specks(im, keep_ratio=0.03):
    """가장 큰 덩어리의 3%보다 작은 떨어진 조각(배경 잔여물)을 지운다."""
    import numpy as np
    from scipy import ndimage

    a = np.array(im.getchannel("A"))
    labels, n = ndimage.label(a > 16)
    if n <= 1:
        return im
    sizes = ndimage.sum(np.ones_like(a), labels, range(1, n + 1))
    small = np.isin(labels, np.flatnonzero(sizes < sizes.max() * keep_ratio) + 1)
    a[small] = 0
    im.putalpha(Image.fromarray(a))
    return im


def rounded(im):
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    r = min(w, h) // 5
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask.filter(ImageFilter.GaussianBlur(1.5)))
    return out


def candidates(wid, pick):
    base = pick.get("from", wid)
    return base, json.loads((CACHE / base / "meta.json").read_text(encoding="utf-8"))


def process(wid, pick):
    base, cands = candidates(wid, pick)
    cand = cands[pick["i"]]
    im = full_image(base, pick["i"], cand)
    if "crop" in pick:
        x0, y0, x1, y1 = pick["crop"]
        W, H = im.size
        im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    out = rounded(im) if pick.get("mode") == "round" else cutout(im)
    out.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    OUT.mkdir(exist_ok=True)
    out.save(OUT / f"{wid}.webp", quality=86, alpha_quality=90, method=6)
    return cand


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def write_data(picks):
    sound_picks = json.loads((ROOT / "sound_picks.json").read_text(encoding="utf-8"))
    data_words, credits, sound_credits = [], [], []
    for wid, cat, ko, en, _q in WORDS:
        if not (OUT / f"{wid}.webp").exists():
            continue
        word = {"id": wid, "cat": cat, "ko": ko, "en": en, "img": f"img/{wid}.webp"}
        # 의성어(예: 멍멍)와 실제 소리 파일
        if SOUNDS.get(wid, (None,))[0]:
            word["sound"] = SOUNDS[wid][0]
        if (APP / "snd" / f"{wid}.mp3").exists():
            word["snd"] = f"snd/{wid}.mp3"
            sp = sound_picks[wid] if isinstance(sound_picks[wid], dict) else {"i": sound_picks[wid]}
            sc = json.loads((SND_CACHE / f"{sp.get('from', wid)}.json").read_text(encoding="utf-8"))[sp["i"]]
            sound_credits.append((ko, en, sc))
        data_words.append(word)
        pick = pick_of(picks, wid)
        c = candidates(wid, pick)[1][pick["i"]]
        credits.append((ko, en, c))
    data = {
        "categories": [{"id": c, "ko": k, "en": e, "cover": COVERS.get(c)} for c, k, e in CATEGORIES],
        "words": data_words,
    }
    (APP / "data").mkdir(exist_ok=True)
    (APP / "data" / "words.js").write_text(
        "window.CARD_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")

    def rows(items):
        return "\n".join(
            f'<li><b>{html.escape(ko)}</b> ({html.escape(en)}) — '
            f'<a href="{html.escape(c["page"])}">{html.escape(c["title"].removeprefix("File:"))}</a>, '
            f'{html.escape(strip_html(c["artist"]) or "unknown")}, {html.escape(c["license"])}</li>'
            for ko, en, c in items)
    (APP / "credits.html").write_text(f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>사진·소리 출처</title>
<style>
:root {{ --bg:#fff8ef; --ink:#3b2f2a; --link:#c25a12; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#221c19; --ink:#f3e9e1; --link:#ffb072; }} }}
body {{ background:var(--bg); color:var(--ink); font:15px/1.6 system-ui, sans-serif; margin:0 auto; max-width:760px; padding:16px; }}
a {{ color:var(--link); word-break:break-all; }} li {{ margin:6px 0; }}
</style></head><body>
<p><a href="index.html">← 낱말 카드로</a></p>
<h1>사진·소리 출처</h1>
<p>모든 사진과 소리는 Wikimedia Commons의 자유 라이선스 자료입니다.
사진은 배경을 제거하고 크기를 줄였고, 소리는 몇 초만 잘라 음량을 맞췄습니다.</p>
<h2>사진</h2>
<ul>
{rows(credits)}
</ul>
<h2>소리</h2>
<ul>
{rows(sound_credits)}
</ul></body></html>
""", encoding="utf-8")


if __name__ == "__main__":
    picks = json.loads((ROOT / "picks.json").read_text(encoding="utf-8"))
    only = set(sys.argv[1:])
    for wid, *_ in WORDS:
        if only and wid not in only:
            continue
        process(wid, pick_of(picks, wid))
        print("done", wid, flush=True)
    write_data(picks)
    print("data written")
