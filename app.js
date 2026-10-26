(() => {
  const { categories, words } = window.CARD_DATA;

  // 카테고리별 색 (배경 tint, 강조 accent)
  const THEMES = {
    all:       { tint: "#ffe9d6", accent: "#ff8a3d" },
    fruit:     { tint: "#ffe2e0", accent: "#f2545b" },
    animal:    { tint: "#fff0cc", accent: "#e8a100" },
    vehicle:   { tint: "#dcebff", accent: "#3d7ef0" },
    appliance: { tint: "#d9f4ea", accent: "#16a57a" },
    object:    { tint: "#ece4ff", accent: "#7c5ce8" },
    body:      { tint: "#ffe3f1", accent: "#e0498f" },
  };

  const $ = (id) => document.getElementById(id);
  const home = $("home"), deck = $("deck"), card = $("card");
  const img = $("card-img"), ko = $("card-ko"), en = $("card-en");
  const dots = $("dots"), counter = $("counter"), soundBtn = $("sound");
  const soundBubble = $("card-sound"), soundText = $("card-sound-text");

  let list = [], index = 0, busy = false, fromHome = false;
  let soundOn = load("soundOn", true);

  function load(key, fallback) {
    try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); }
    catch { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
  }

  function applyTheme(catId) {
    const t = THEMES[catId] || THEMES.all;
    document.documentElement.style.setProperty("--tint", t.tint);
    document.documentElement.style.setProperty("--accent", t.accent);
  }

  // ---------- 홈 ----------
  function renderHome() {
    const grid = $("categories");
    const tiles = categories
      .map((c) => [c, words.find((w) => w.id === c.cover) || words.find((w) => w.cat === c.id)])
      .filter(([, cover]) => cover)
      .map(([c, cover]) => tile(c.id, c.ko, c.en, cover.img));
    const any = words[Math.floor(Math.random() * words.length)];
    tiles.push(tile("all", "모두 섞기", "Mix all", any.img, "all"));
    grid.replaceChildren(...tiles);
  }

  function tile(id, k, e, src, extra = "") {
    const t = THEMES[id] || THEMES.all;
    const b = document.createElement("button");
    b.className = `cat ${extra}`;
    b.style.setProperty("--tint", t.tint);
    b.style.setProperty("--accent", t.accent);
    b.innerHTML = `<img alt="" src="${src}"><span class="ko">${k}</span><span class="en">${e}</span>`;
    b.addEventListener("click", () => { fromHome = true; location.hash = `cat=${id}`; });
    return b;
  }

  // ---------- 덱 ----------
  function openDeck(catId) {
    if (catId === "all") {
      list = shuffle(words.slice());
    } else {
      list = words.filter((w) => w.cat === catId);
    }
    if (!list.length) return showHome();
    const c = categories.find((x) => x.id === catId);
    $("deck-title").textContent = c ? c.ko : "모두 섞기";
    applyTheme(catId);
    index = 0;
    dots.replaceChildren(...list.map(() => document.createElement("i")));
    home.hidden = true;
    deck.hidden = false;
    card.style.transition = "none";
    card.style.transform = "";
    render();
  }

  function showHome() {
    stopAll();
    fromHome = false;
    applyTheme("all");
    deck.hidden = true;
    home.hidden = false;
  }

  function render() {
    const w = list[index];
    img.src = w.img;
    img.alt = w.ko;
    ko.textContent = w.ko;
    en.textContent = w.en;
    counter.textContent = `${index + 1} / ${list.length}`;
    [...dots.children].forEach((d, i) => d.classList.toggle("on", i === index));
    soundBubble.hidden = !(w.sound || w.snd);
    soundText.textContent = w.sound || "";
    // 양 옆 카드 이미지·소리 미리 받아두기
    for (const d of [1, -1]) {
      const n = list[(index + d + list.length) % list.length];
      new Image().src = n.img;
      if (n.snd) loadBuffer(n.snd).catch(() => {});
    }
  }

  function go(dir) {
    if (busy || list.length < 2) return;
    busy = true;
    const W = window.innerWidth;
    card.style.transition = "transform .28s ease-in";
    card.style.transform = `translateX(${-dir * W}px) rotate(${-dir * 18}deg)`;
    setTimeout(() => {
      index = (index + dir + list.length) % list.length;
      render();
      card.style.transition = "none";
      card.style.transform = `translateX(${dir * W}px) rotate(${dir * 18}deg)`;
      card.offsetWidth; // 리플로우로 시작 위치 고정
      card.style.transition = "transform .35s cubic-bezier(.2,.9,.3,1.15)";
      card.style.transform = "";
      setTimeout(() => { busy = false; }, 340);
      if (soundOn) speak(list[index], true);
      else stopAll();
    }, 280);
  }

  function tapCard() {
    card.classList.remove("pop");
    card.offsetWidth;
    card.classList.add("pop");
    speak(list[index], true);
  }

  // ---------- 스와이프 ----------
  let drag = null;

  card.addEventListener("pointerdown", (e) => {
    unlockAudio();
    if (busy || e.target.closest(".sound-btn")) return;
    drag = { x: e.clientX, y: e.clientY, t: performance.now(), dx: 0 };
    card.setPointerCapture(e.pointerId);
    card.style.transition = "none";
  });

  card.addEventListener("pointermove", (e) => {
    if (!drag) return;
    drag.dx = e.clientX - drag.x;
    card.style.transform = `translateX(${drag.dx}px) rotate(${drag.dx * 0.05}deg)`;
  });

  const endDrag = (e) => {
    if (!drag) return;
    const { dx, t } = drag;
    const dt = performance.now() - t;
    const dy = e.clientY - drag.y;
    drag = null;
    const fast = Math.abs(dx) > 30 && Math.abs(dx) / dt > 0.5;
    if (Math.abs(dx) > Math.min(110, card.offsetWidth * 0.25) || fast) {
      go(dx < 0 ? 1 : -1);
      return;
    }
    card.style.transition = "transform .3s cubic-bezier(.2,.9,.3,1.3)";
    card.style.transform = "";
    if (e.type === "pointerup" && Math.abs(dx) < 10 && Math.abs(dy) < 10 && dt < 500) tapCard();
  };
  card.addEventListener("pointerup", endDrag);
  card.addEventListener("pointercancel", endDrag);
  // 블로그 iframe 안에서 마우스를 끌다가 밖에서 놓으면 pointerup이 오지 않으므로,
  // 포인터가 문서를 벗어나거나 캡처가 풀리면 그 자리에서 끝낸다
  card.addEventListener("lostpointercapture", endDrag);
  document.documentElement.addEventListener("pointerleave", endDrag);
  window.addEventListener("blur", () => endDrag({ type: "blur", clientY: drag?.y ?? 0 }));

  $("prev").addEventListener("click", () => go(-1));
  $("next").addEventListener("click", () => go(1));
  // 홈에서 들어왔으면 history.back()으로 돌아가야 안드로이드 뒤로가기와 어긋나지 않는다
  $("back").addEventListener("click", () => { fromHome ? history.back() : (location.hash = ""); });

  document.addEventListener("keydown", (e) => {
    if (deck.hidden) return;
    if (e.key === "ArrowRight") go(1);
    else if (e.key === "ArrowLeft") go(-1);
    else if (e.key === " " || e.key === "Enter") { e.preventDefault(); tapCard(); }
    else if (e.key === "Escape") $("back").click();
  });

  // ---------- 소리 ----------
  let voices = [];
  const loadVoices = () => { voices = window.speechSynthesis ? speechSynthesis.getVoices() : []; };
  if (window.speechSynthesis) {
    loadVoices();
    speechSynthesis.addEventListener?.("voiceschanged", loadVoices);
  }
  const pickVoice = (lang) =>
    voices.find((v) => v.lang.replace("_", "-").startsWith(lang) && /Google|Natural|Yuna|Heami|SunHi/i.test(v.name)) ||
    voices.find((v) => v.lang.replace("_", "-").startsWith(lang));

  // 카드가 바뀌면 token이 바뀌어, 이전 카드의 늦은 콜백이 소리를 내지 않는다
  let token = 0;

  function say(text, lang, onend) {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = 0.8;
    u.pitch = 1.1;
    const v = pickVoice(lang);
    if (v) u.voice = v;
    if (onend) u.onend = onend;
    speechSynthesis.speak(u);
  }

  // 단어를 한국어·영어로 읽고, withSound면 이어서 울음소리/탈것 소리를 낸다
  function speak(w, withSound = false) {
    stopAll();
    const t = token;
    const next = withSound && (w.snd || w.sound) ? () => { if (t === token) playSound(w); } : null;
    if (!window.speechSynthesis) return next?.();
    say(w.ko, "ko-KR");
    say(w.en, "en-US", next);
  }

  // 실제 녹음은 Web Audio로 재생한다 (iOS에서 첫 터치 이후 언제든 재생 가능)
  let actx = null;
  const buffers = new Map();
  let source = null;

  function audioCtx() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (AC) actx ??= new AC();
    return actx;
  }

  // 터치 이벤트 안에서 불러야 모바일 브라우저가 소리를 허용한다
  function unlockAudio() {
    if (audioCtx()?.state === "suspended") actx.resume();
  }

  function loadBuffer(url) {
    if (!audioCtx()) return Promise.reject(new Error("no Web Audio"));
    if (!buffers.has(url)) {
      const p = fetch(url)
        .then((r) => r.arrayBuffer())
        .then((b) => new Promise((ok, fail) => actx.decodeAudioData(b, ok, fail)));
      p.catch(() => buffers.delete(url));
      buffers.set(url, p);
    }
    return buffers.get(url);
  }

  async function playSound(w) {
    const t = token;
    soundBubble.classList.add("playing");
    const done = () => { if (t === token) soundBubble.classList.remove("playing"); };
    if (!w.snd) {
      // 녹음이 없으면 의성어를 읽어준다 (예: 토끼 "깡충깡충")
      if (window.speechSynthesis) say(w.sound, "ko-KR", done);
      else done();
      return;
    }
    try {
      const buf = await loadBuffer(w.snd);
      if (t !== token) return done();
      source = actx.createBufferSource();
      source.buffer = buf;
      source.connect(actx.destination);
      source.onended = done;
      source.start();
    } catch {
      done();
    }
  }

  function stopAll() {
    token++;
    window.speechSynthesis?.cancel();
    try { source?.stop(); } catch {}
    source = null;
    soundBubble.classList.remove("playing");
  }

  soundBubble.addEventListener("click", (e) => {
    e.stopPropagation();
    unlockAudio();
    stopAll();
    playSound(list[index]);
  });

  function setSound(on) {
    soundOn = on;
    soundBtn.setAttribute("aria-pressed", String(on));
    save("soundOn", on);
    if (!on) stopAll();
  }
  soundBtn.addEventListener("click", () => setSound(!soundOn));
  setSound(soundOn);

  // ---------- 라우팅 (뒤로가기 지원) ----------
  function route() {
    const m = location.hash.match(/cat=(\w+)/);
    m ? openDeck(m[1]) : showHome();
  }

  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  renderHome();
  window.addEventListener("hashchange", route);
  route();

  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
})();
