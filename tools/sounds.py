"""동물 울음소리·탈것 소리를 Wikimedia Commons에서 찾아 짧은 mp3로 만든다.

사용법:
  python tools/sounds.py search [id ...]   후보 목록 -> tools/cache/snd/<id>.json 와 화면 출력
  python tools/sounds.py build  [id ...]   tools/sound_picks.json 의 후보 번호로 snd/<id>.mp3 생성
sound_picks.json: {"dog": 0, "lion": {"i": 2, "start": 1.5, "len": 3}}  (start/len 생략 시 가장 큰 구간 자동 선택)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from fetch_candidates import API, get

ROOT = Path(__file__).parent
APP = ROOT.parent
CACHE = ROOT / "cache" / "snd"
OUT = APP / "snd"
RATE = 22050

# id: (의성어, Commons 검색어). 검색어가 None이면 소리 파일 없이 의성어만 읽어준다.
SOUNDS = {
    "dog": ("멍멍", "dog barking"),
    "cat": ("야옹", "cat meow"),
    "rabbit": ("깡충깡충", None),
    "lion": ("어흥", "Panthera leo|lion roaring|lion"),
    "elephant": ("뿌우", "elephant trumpet"),
    "giraffe": (None, None),
    "bear": ("으르렁", "bear growl"),
    "monkey": ("끼끼끼", "monkey call"),
    "tiger": ("어흥", "Panthera tigris|tiger growl|tiger"),
    "penguin": ("꽥꽥", "Spheniscus|penguin|Aptenodytes"),
    "duck": ("꽥꽥", "mallard Anas platyrhynchos|duck quacking|domestic duck"),
    "horse": ("히히힝", "horse neigh"),
    "cow": ("음매", "cow moo"),
    "pig": ("꿀꿀", "pig oink|pig grunt|pigs farm sound"),
    "car": ("빵빵", "car horn"),
    "bus": ("부릉부릉", "bus engine"),
    "train": ("칙칙폭폭", "train horn"),
    "airplane": ("슈웅", "airplane flyover|aircraft takeoff|jet airliner landing"),
    "ship": ("뿌우웅", "ship horn"),
    "bicycle": ("따르릉", "bicycle bell"),
    "motorcycle": ("부릉부릉", "motorcycle engine"),
    "helicopter": ("두두두두", "helicopter"),
    "truck": ("빵빵", "truck air horn|lorry horn|truck engine"),
    "firetruck": ("애앵애앵", "fire engine siren"),
    "policecar": ("위용위용", "police siren"),
    "ambulance": ("삐뽀삐뽀", "ambulance siren"),
    "excavator": ("덜덜덜", "excavator"),
}


def search(query, limit=12):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": 6, "gsrsearch": f"{query} filetype:audio", "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|Artist",
    }
    pages = get(API, params=params).json().get("query", {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        ii = p.get("imageinfo", [{}])[0]
        meta = ii.get("extmetadata", {})
        out.append({
            "title": p["title"], "page": ii.get("descriptionurl"), "url": ii.get("url"),
            "duration": round(ii.get("duration", 0), 1), "size": ii.get("size", 0),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "artist": meta.get("Artist", {}).get("value", ""),
        })
    return out


def cmd_search(ids):
    CACHE.mkdir(parents=True, exist_ok=True)
    for wid in ids:
        _, q = SOUNDS[wid]
        if not q:
            continue
        cands, seen = [], set()
        for sub in q.split("|"):  # 여러 검색어 결과를 합친다
            for c in search(sub, limit=8):
                if c["title"] not in seen:
                    seen.add(c["title"])
                    cands.append(c)
        (CACHE / f"{wid}.json").write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"== {wid} ({q})")
        for i, c in enumerate(cands):
            print(f"  {i}: {c['title'][5:70]}  {c['duration']}s  {c['size'] // 1024}KB  {c['license']}")


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def loudest(x, seconds):
    """에너지가 가장 큰 구간의 시작 시각(초)."""
    n = int(seconds * RATE)
    if len(x) <= n:
        return 0.0
    e = np.concatenate([[0], np.cumsum(x.astype(np.float64) ** 2)])
    win = e[n:] - e[:-n]
    return float(np.argmax(win[::RATE // 20]) * (RATE // 20) / RATE)


def cmd_build(ids):
    picks = json.loads((ROOT / "sound_picks.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    for wid in ids:
        if wid not in picks:
            continue
        p = picks[wid] if isinstance(picks[wid], dict) else {"i": picks[wid]}
        base = p.get("from", wid)  # 다른 단어의 후보 목록에서 가져올 수도 있다
        c = json.loads((CACHE / f"{base}.json").read_text(encoding="utf-8"))[p["i"]]
        src = CACHE / f"{base}_{p['i']}{Path(c['url']).suffix}"
        if not src.exists():
            src.write_bytes(get(c["url"]).content)
        # repeat: 아주 짧은 소리(돼지 꿀꿀 등)를 n번 이어 붙인다
        repeat = p.get("repeat", 1)
        length = min(p.get("len", 3.0), c["duration"] or 3.0) * repeat
        start = p.get("start", 0.0 if repeat > 1 else loudest(decode(src), length))
        fade = min(0.4, length / 4)
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-stream_loop", str(repeat - 1),
            "-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", str(src),
            "-af", f"afade=t=in:d=0.05,afade=t=out:st={length - fade:.2f}:d={fade},loudnorm=I=-16:TP=-1.5",
            "-ac", "1", "-ar", "44100", "-b:a", "80k", str(OUT / f"{wid}.mp3"),
        ], check=True)
        print("built", wid, f"start={start:.2f}s", flush=True)


if __name__ == "__main__":
    mode, *ids = sys.argv[1:]
    ids = ids or list(SOUNDS)
    {"search": cmd_search, "build": cmd_build}[mode](ids)
