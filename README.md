# 낱말 카드

아이들을 위한 실사 사진 낱말 카드 웹앱입니다. 좌우로 밀어 넘기고, 카드를 누르면 단어를 한국어·영어로 읽어줍니다.
동물·탈것 카드는 실제 울음소리/탈것 소리도 들을 수 있어요.

- 카테고리: 과일, 동물, 탈것, 가전, 사물, 신체 (75장)
- 사진·소리: Wikimedia Commons 자유 라이선스 자료 — [출처](credits.html)

## 다시 만들기

`tools/`의 스크립트로 사진 후보 수집(`fetch_candidates.py`), 누끼(`process.py`), 소리(`sounds.py`)를 만듭니다.
고른 후보 번호는 `tools/picks.json`, `tools/sound_picks.json`에 있습니다.
