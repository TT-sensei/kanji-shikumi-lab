"use strict";
/* 漢字のしくみラボ（仮称） プロトタイプ: 1・2・3年生 440字 */
const GRADE_DATA = {1: window.KSL_G1 || [], 2: window.KSL_G2 || [], 3: window.KSL_G3 || []};
const GRADE_TEXT = {1: window.KSL_TEXT || {}, 2: window.KSL_TEXT2 || {}, 3: window.KSL_TEXT3 || {}};
let curGrade = 1;
let DATA = GRADE_DATA[1];
let TEXT = GRADE_TEXT[1];
const LS_KEY = "kanjiShikumiLab.v1";

const POS_JA = {left:"ひだり", right:"みぎ", top:"うえ", bottom:"した", kamae:"かまえ", nyo:"かまえ", nyoc:"かまえ", tare:"かまえ", tarec:"かまえ", kamaec:"かまえ", middle:"まんなか", "":""};
const STRUCT_JA = {horizontal:"左と 右", vertical:"上と 下", enclose:"囲み・かまえ", single:"一つの 形", parts:"組み合わせ"};
const STRUCT_ORDER = ["horizontal","vertical","enclose","single","parts"];
const COMP_COLORS = ["#e2574c","#3b7dd8","#3aa655","#e8912d","#8b5cf6","#0e9594","#d6336c","#5a7247"];
const MODES = {
  bunkai:{name:"分解", ruby:"ぶんかい", icon:"🔍", desc:"パーツに 分けて 見る"},
  kumitate:{name:"組み立て", ruby:"くみたて", icon:"🧩", desc:"パーツを 選んで 漢字を 作る"},
  kozo:{name:"構造", ruby:"こうぞう", icon:"🏗️", desc:"形の タイプを 当てる"},
  bushu:{name:"部首", ruby:"ぶしゅ", icon:"📚", desc:"部首を 見つける・当てる"},
  test:{name:"テスト", ruby:"てすと", icon:"📝", desc:"グループから ランダムに 組み立て"}
};
const MODE_KEY = {bunkai:"b", kumitate:"k", kozo:"s", bushu:"r"};

/* ---------- 保存 ---------- */
function loadStore(){
  try{ const s = JSON.parse(localStorage.getItem(LS_KEY)); if(s && s.status) return s; }catch(e){}
  return {status:{}, mistakes:[], sound:true};
}
let store = loadStore();
function saveStore(){ try{ localStorage.setItem(LS_KEY, JSON.stringify(store)); }catch(e){} }
function st(kanji){ return store.status[kanji] || {}; }
function setSt(kanji, key){
  if(!store.status[kanji]) store.status[kanji] = {};
  store.status[kanji][key] = 1; saveStore();
}
function masteredCount(data){ return (data || DATA).filter(r => st(r.kanji).k).length; }
function modeCount(mode){ const k = MODE_KEY[mode]; return DATA.filter(r => st(r.kanji)[k]).length; }

/* ---------- 音（sounds-recipe-。読み込めなくても学習は続ける） ---------- */
let audioCtx = null, soundMod = null;
import("https://tt-sensei.github.io/sounds-recipe-/sounds.js").then(m => { soundMod = m; }).catch(() => { });
function playSnd(id){
  if(!store.sound) return;
  if(soundMod){
    try{
      if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if(audioCtx.state === "suspended") audioCtx.resume();
      soundMod.playSound(audioCtx, id, 0.5);
      return;
    }catch(e){ }
  }
  if(id === "correct" || id === "clear"){ beep(659,0,0.16); beep(880,0.12,0.26); }
  else if(id === "wrong"){ beep(196,0,0.22,"triangle"); }
  else beep(520,0,0.07);
}
function beep(freq, t0, dur, type){
  if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const o = audioCtx.createOscillator(), g = audioCtx.createGain();
  o.type = type || "sine"; o.frequency.value = freq;
  g.gain.setValueAtTime(0.0001, audioCtx.currentTime + t0);
  g.gain.exponentialRampToValueAtTime(0.22, audioCtx.currentTime + t0 + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + t0 + dur);
  o.connect(g); g.connect(audioCtx.destination);
  o.start(audioCtx.currentTime + t0); o.stop(audioCtx.currentTime + t0 + dur + 0.05);
}
function sndGood(){ playSnd("correct"); }
function sndBad(){ playSnd("wrong"); }
function sndTap(){ playSnd("click"); }

/* ---------- エフェクト ---------- */
function burst(){
  const fx = document.getElementById("fx");
  const cx = window.innerWidth * 0.36, cy = window.innerHeight * 0.45;
  for(let i=0;i<14;i++){
    const s = document.createElement("span");
    s.className = "star"; s.textContent = ["⭐","✨","🎉"][i % 3];
    s.style.left = cx + "px"; s.style.top = cy + "px";
    const a = (Math.PI * 2 * i) / 14, d = 90 + Math.random() * 130;
    s.style.setProperty("--dx", Math.cos(a) * d + "px");
    s.style.setProperty("--dy", Math.sin(a) * d + "px");
    fx.appendChild(s); setTimeout(() => s.remove(), 950);
  }
}

function celebrate(){
  try{ if(window.EduEffects){ EduEffects.confetti(document.body, 60); return; } }catch(e){ }
  burst();
}

/* ---------- ガイド（ナビキャラ6人から開くたびランダム） ---------- */
const NAVI_CHARS = [
  {id:"riku", name:"りく"}, {id:"sora", name:"そら"}, {id:"kai", name:"かい"},
  {id:"saku", name:"さく"}, {id:"tsuki", name:"つき"}, {id:"nami", name:"なみ"}
];
const GUIDE_CHAR = NAVI_CHARS[Math.floor(Math.random() * NAVI_CHARS.length)];
const FACE_BASE = `https://tt-sensei.github.io/navi-character-/assets/web/characters/${GUIDE_CHAR.id}/expressions/`;
const FACE = {
  normal: FACE_BASE + "01-normal-smile.webp",
  happy: FACE_BASE + "02-happy.webp",
  think: FACE_BASE + "03-thinking.webp",
  celeb: FACE_BASE + "08-celebrating.webp"
};
function setGuide(face, line){
  const img = document.getElementById("guideImg");
  if(img){ img.style.visibility = "visible"; img.src = FACE[face] || FACE.normal; }
  const gl = document.getElementById("guideLine");
  if(gl && line != null) gl.textContent = line;
}
const GUIDE_OPEN = {
  bunkai: "パーツを タップして、漢字の しくみを 見てみよう！",
  kumitate: "おぼえうたを たよりに、パーツを 組み立ててみよう！",
  kozo: "この 漢字の つくりは どれかな？ よく 見て 考えよう。",
  bushu: "どの パーツが 部首に なるか、考えてみよう。"
};

/* ---------- SVG ---------- */
function pathsOf(comp){ return comp.d.map(d => `<path d="${d}"/>`).join(""); }
function svgKanji(rec, opts){
  opts = opts || {};
  const order = rec.components.map((c, i) => i).sort((a, b2) => {
    const ba = bboxOf(rec.components[a]), bb = bboxOf(rec.components[b2]);
    return (bb.w * bb.h) - (ba.w * ba.h);
  });
  const groups = order.map(i => { const c = rec.components[i];
    let stroke = "#26304d", cls = "comp", extra = "";
    if(opts.colored) stroke = COMP_COLORS[i % COMP_COLORS.length];
    if(opts.radical && (c.rad || opts.radicalAll)) stroke = "#e2574c";
    else if(opts.radical) stroke = "#b9c2dd";
    if(opts.selected !== undefined){ cls += (i === opts.selected ? " sel" : " dim"); }
    const hit = c.d.map(d => `<path class="hit" d="${d}" stroke="rgba(0,0,0,0)" stroke-width="19" style="pointer-events:stroke"/>`).join("");
    return `<g class="${cls}" data-i="${i}" fill="none" stroke="${stroke}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">${hit}${pathsOf(c)}</g>`;
  }).join("");
  return `<svg class="stage-svg ${opts.small ? "small" : ""}" viewBox="0 0 109 109" xmlns="http://www.w3.org/2000/svg">${groups}</svg>`;
}
function pathBBox(d){
  const tokens = d.match(/[a-zA-Z]|-?\d+\.?\d*/g) || [];
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  let cx = 0, cy = 0, sx = 0, sy = 0, cmd = "", i = 0;
  const add = (x, y) => { if(x < minX) minX = x; if(x > maxX) maxX = x; if(y < minY) minY = y; if(y > maxY) maxY = y; };
  const num = () => parseFloat(tokens[i++]);
  const isCmd = t => /^[a-zA-Z]$/.test(t);
  while(i < tokens.length){
    if(isCmd(tokens[i])){ cmd = tokens[i++]; if(cmd === "Z" || cmd === "z"){ cx = sx; cy = sy; } continue; }
    const rel = cmd === cmd.toLowerCase();
    const C = cmd.toUpperCase();
    const px = v => rel ? cx + v : v, py = v => rel ? cy + v : v;
    if(C === "M"){ const x = num(), y = num(); cx = px(x); cy = py(y); sx = cx; sy = cy; add(cx, cy); cmd = rel ? "l" : "L"; }
    else if(C === "L"){ const x = num(), y = num(); cx = px(x); cy = py(y); add(cx, cy); }
    else if(C === "H"){ const x = num(); cx = px(x); add(cx, cy); }
    else if(C === "V"){ const y = num(); cy = py(y); add(cx, cy); }
    else if(C === "C"){ const x1 = px(num()), y1 = py(num()), x2 = px(num()), y2 = py(num()), x = px(num()), y = py(num()); add(x1, y1); add(x2, y2); cx = x; cy = y; add(cx, cy); }
    else if(C === "S"){ const x2 = px(num()), y2 = py(num()), x = px(num()), y = py(num()); add(x2, y2); cx = x; cy = y; add(cx, cy); }
    else if(C === "Q"){ const x1 = px(num()), y1 = py(num()), x = px(num()), y = py(num()); add(x1, y1); cx = x; cy = y; add(cx, cy); }
    else if(C === "T"){ const x = px(num()), y = py(num()); cx = x; cy = y; add(cx, cy); }
    else if(C === "A"){ num(); num(); num(); num(); num(); const x = px(num()), y = py(num()); cx = x; cy = y; add(cx, cy); }
    else { i++; }
  }
  if(minX > maxX) return {x:0, y:0, w:109, h:109};
  return {x:minX, y:minY, w:maxX - minX, h:maxY - minY};
}
function bboxOf(comp){
  let r = null;
  comp.d.forEach(d => {
    const b = pathBBox(d);
    if(!r) r = {x:b.x, y:b.y, w:b.w, h:b.h};
    else {
      const x2 = Math.max(r.x + r.w, b.x + b.w), y2 = Math.max(r.y + r.h, b.y + b.h);
      r.x = Math.min(r.x, b.x); r.y = Math.min(r.y, b.y); r.w = x2 - r.x; r.h = y2 - r.y;
    }
  });
  return r || {x:0, y:0, w:109, h:109};
}
function posLabelFromCenter(cx, cy){
  if(cy < 42) return "うえ";
  if(cy > 67) return "した";
  if(cx < 42) return "ひだり";
  if(cx > 67) return "みぎ";
  return "";
}
function approxBBox(ds){
  let r = null;
  ds.forEach(d => {
    const b = pathBBox(d);
    if(!r) r = {x:b.x, y:b.y, w:b.w, h:b.h};
    else {
      const x2 = Math.max(r.x + r.w, b.x + b.w), y2 = Math.max(r.y + r.h, b.y + b.h);
      r.x = Math.min(r.x, b.x); r.y = Math.min(r.y, b.y); r.w = x2 - r.x; r.h = y2 - r.y;
    }
  });
  if(!r) r = {x:0, y:0, w:109, h:109};
  const pad = 7;
  return `${r.x - pad} ${r.y - pad} ${r.w + pad * 2} ${r.h + pad * 2}`;
}
function svgPart(comp, color){
  return `<svg viewBox="${approxBBox(comp.d)}" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="${color || "#26304d"}" stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round">${pathsOf(comp)}</g></svg>`;
}

/* ---------- 画面切り替え ---------- */
const VIEWS = ["view-top","view-grade","view-picker","view-play","view-parts","view-sources","view-testgroups"];
function showView(id){
  VIEWS.forEach(v => document.getElementById(v).classList.toggle("hidden", v !== id));
  window.scrollTo(0, 0);
}
function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;"); }
function recOf(kanji){ return DATA.find(r => r.kanji === kanji); }
function readingsHTML(rec){
  const on = rec.on.length ? `<span class="rchip">おん <b>${esc(rec.on.join("・"))}</b></span>` : "";
  const kun = rec.kun.length ? `<span class="rchip">くん <b>${esc(rec.kun.join("・"))}</b></span>` : "";
  return `<div class="reading-chips">${on}${kun}<span class="rchip">${rec.strokes} かく</span></div>`;
}
function exampleOf(rec){ return (rec.examples || []).find(e => e.l === 1) || (rec.examples || [])[0]; }
function labelOf(c){ return c.label || c.el; }
function chantOf(rec){
  const t = TEXT[rec.kanji];
  if(t && t.chant) return t.chant;
  return rec.components.map(c => labelOf(c)).join(" ＋ ");
}
function explOf(rec){
  const t = TEXT[rec.kanji];
  return (t && t.expl) ? t.expl : "";
}
function partLinkTarget(c, selfKanji){
  // 部品そのものが 学習する漢字（1・2年生）なら、その字へのリンクを返す
  for(const cand of [c.el, labelOf(c)]){
    if(!cand || cand === selfKanji) continue;
    for(const gr of [1, 2, 3]){
      if(GRADE_DATA[gr].some(r => r.kanji === cand)) return {kanji: cand, grade: gr};
    }
  }
  return null;
}
function gotoKanji(target){
  if(target.grade !== curGrade){
    curGrade = target.grade;
    DATA = GRADE_DATA[curGrade];
    TEXT = GRADE_TEXT[curGrade];
  }
  startPlay("bunkai", target.kanji);
}
function chantBox(rec, withExpl){
  return `<div class="info-box"><div class="ib-title">おぼえうた（唱え方）</div><div class="chant">${esc(chantOf(rec))}</div>${withExpl && explOf(rec) ? `<div class="ib-sub">${esc(explOf(rec))}</div>` : ""}</div>`;
}
function formulaOf(rec){
  return rec.components.map(c => labelOf(c)).join(" ＋ ") + " ＝ " + rec.kanji;
}

/* ---------- トップ ---------- */
function renderTop(){
  const g = document.getElementById("gradeGrid");
  let html = "";
  for(let gr = 1; gr <= 6; gr++){
    const d = GRADE_DATA[gr];
    if(d && d.length){
      html += `<button class="grade-card" data-grade="${gr}">${gr}年生<span class="gstars">くみたて マスター ★ ${masteredCount(d)} / ${d.length}</span></button>`;
    } else {
      html += `<button class="grade-card disabled" disabled>${gr}年生<span class="soon">じゅんびちゅう</span></button>`;
    }
  }
  g.innerHTML = html;
  g.querySelectorAll(".grade-card[data-grade]").forEach(b => b.addEventListener("click", () => {
    sndTap();
    curGrade = Number(b.dataset.grade);
    DATA = GRADE_DATA[curGrade];
    TEXT = GRADE_TEXT[curGrade];
    renderGrade();
    showView("view-grade");
  }));
}

/* ---------- 学年トップ ---------- */
function renderGrade(){
  document.getElementById("gradeName").textContent = `${curGrade}年生`;
  document.getElementById("gradeCount").textContent = `（${DATA.length}字）`;
  const mg = document.getElementById("modeGrid");
  mg.innerHTML = Object.keys(MODES).map(m => {
    const M = MODES[m];
    return `<button class="mode-card" data-mode="${m}">
      <span class="micon">${M.icon}</span>
      <span class="mname"><ruby>${M.name}<rt>${M.ruby}</rt></ruby></span>
      <span class="mdesc">${M.desc}</span>
      <span class="mdone">${m === "test" ? "グループ 4つから ランダム" : `できた ${modeCount(m)} / ${DATA.length}`}</span></button>`;
  }).join("");
  mg.querySelectorAll(".mode-card").forEach(b => b.addEventListener("click", () => {
    sndTap();
    if(b.dataset.mode === "test") renderTestGroups();
    else renderPicker(b.dataset.mode);
  }));
  const nl = document.getElementById("nigateList");
  if(store.mistakes.length){
    nl.innerHTML = store.mistakes.map(k => `<button class="chip" data-k="${k}">${k}</button>`).join("");
    nl.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => startPlay("kumitate", c.dataset.k)));
  } else {
    nl.innerHTML = `<span class="chip-none">まだ ありません。くみたてで まちがえると ここに たまります。</span>`;
  }
  const ag = document.getElementById("allKanjiGrid");
  ag.innerHTML = DATA.map(r => kanjiBtnHTML(r)).join("");
  ag.querySelectorAll(".kbtn").forEach(b => b.addEventListener("click", () => startPlay("bunkai", b.dataset.k)));
}
function marksHTML(rec){
  const s = st(rec.kanji);
  const dot = (on) => `<span class="${on ? "on" : ""}">●</span>`;
  return `<span class="marks">${dot(s.b)}${dot(s.k)}${dot(s.s)}${dot(s.r)}</span>`;
}
function kanjiBtnHTML(rec){
  return `<button class="kbtn ${st(rec.kanji).k ? "mastered" : ""}" data-k="${rec.kanji}">${rec.kanji}${marksHTML(rec)}</button>`;
}

/* ---------- ピッカー ---------- */
let pickerMode = "bunkai";
function renderPicker(mode){
  pickerMode = mode;
  const M = MODES[mode];
  document.getElementById("pickerTitle").innerHTML = `<ruby>${M.name}<rt>${M.ruby}</rt></ruby> ： かんじを えらんでね`;
  const pg = document.getElementById("pickerGrid");
  pg.innerHTML = DATA.map(r => kanjiBtnHTML(r)).join("");
  pg.querySelectorAll(".kbtn").forEach(b => b.addEventListener("click", () => startPlay(mode, b.dataset.k)));
  showView("view-picker");
}

/* ---------- プレイ共通 ---------- */
let playMode = null, playKanji = null;
let playBackFn = () => renderPicker(playMode || "bunkai");
function startPlay(mode, kanji){
  playMode = mode; playKanji = kanji;
  TEST.active = false;
  playBackFn = () => renderPicker(mode);
  const rec = recOf(kanji), M = MODES[mode];
  document.getElementById("playTitle").innerHTML = `<ruby>${M.name}<rt>${M.ruby}</rt></ruby> ： ${kanji}`;
  document.getElementById("playProgress").textContent = `${M.ruby} ${modeCount(mode)} / ${DATA.length}`;
  setGuide("normal", GUIDE_OPEN[mode] || "");
  showView("view-play");
  if(mode === "bunkai") playBunkai(rec);
  else if(mode === "kumitate") playKumitate(rec);
  else if(mode === "kozo") playKozo(rec);
  else if(mode === "bushu") playBushu(rec);
}
function nextKanji(){
  const idx = DATA.findIndex(r => r.kanji === playKanji);
  const key = MODE_KEY[playMode];
  for(let i = 1; i <= DATA.length; i++){
    const r = DATA[(idx + i) % DATA.length];
    if(!st(r.kanji)[key]) return r.kanji;
  }
  return DATA[(idx + 1) % DATA.length].kanji;
}
function finishPanel(html){
  return html + `<button class="bigbtn" id="btnNext">つぎの かんじ →</button>
    <button class="bigbtn sub" id="btnBackPicker">いちらんに もどる</button>`;
}
function wireFinish(){
  const n = document.getElementById("btnNext");
  if(n) n.addEventListener("click", () => startPlay(playMode, nextKanji()));
  const b = document.getElementById("btnBackPicker");
  if(b) b.addEventListener("click", () => renderPicker(playMode));
}

/* ---------- 分解 ---------- */
function playBunkai(rec){
  const stage = document.getElementById("playStage");
  const panel = document.getElementById("playPanel");
  const tapped = new Set();
  stage.innerHTML = svgKanji(rec, {colored:true}) + `<div class="ib-sub">パーツを タップして みよう（${rec.components.length}つ）</div>`;
  function panelHTML(sel){
    let info;
    if(sel === null){
      info = `<div class="info-box"><div class="ib-title">パーツ</div><div class="ib-sub">色の ついた パーツを タップすると、名前と 場所が 分かるよ。</div></div>`;
    } else {
      const c = rec.components[sel];
      const pos = c.pos ? `場所：${POS_JA[c.pos]}` : "場所：全体";
      const rad = c.rad ? `<br>⭐ これは 部首の パーツ（${esc(rec.radicalName)}）` : "";
      const lt = partLinkTarget(c, rec.kanji);
      const link = lt ? `<button class="linkbtn" id="btnPartLink" data-k="${esc(lt.kanji)}" data-g="${lt.grade}">「${esc(lt.kanji)}」の ページを 見る →</button>` : "";
      info = `<div class="info-box"><div class="ib-title">パーツ ${sel + 1}</div><div class="ib-main">「${esc(labelOf(c))}」</div><div class="ib-sub">${pos}${rad}</div>${link}</div>`;
    }
    const ex = exampleOf(rec);
    const radComp = rec.components.find(c => c.rad);
    const radLine = rec.radicalState === "whole" ? `部首は「${esc(rec.radicalName)}」。この字 そのものが 部首だよ。`
      : rec.radicalState === "name" ? `部首は「${esc(rec.radicalName)}」。辞書の 分類の 名前で、パーツには 分かれないよ。`
      : `部首は「${esc(rec.radicalName)}」${radComp ? `（パーツの「${esc(labelOf(radComp))}」）` : ""}。`;
    return `${readingsHTML(rec)}
      <div class="formula">${esc(formulaOf(rec))}</div>
      <div class="ib-sub">${radLine}</div>
      ${info}
      ${chantBox(rec, true)}
      ${ex ? `<div class="info-box"><div class="ib-title">れいぶん</div><div class="ib-main" style="font-size:19px">${esc(ex.s)}</div><div class="ib-sub">${esc(ex.r)}</div></div>` : ""}
      <div id="bunkaiResult"></div>`;
  }
  panel.innerHTML = panelHTML(null);
  stage.querySelectorAll(".comp").forEach(g => {
    g.addEventListener("click", () => {
      const i = +g.dataset.i;
      tapped.add(i); sndTap();
      stage.innerHTML = svgKanji(rec, {colored:true, selected:i}) + `<div class="ib-sub">パーツを タップして みよう（${rec.components.length}つ）</div>`;
      stage.querySelectorAll(".comp").forEach(g2 => g2.addEventListener("click", () => {
        const j = +g2.dataset.i; tapped.add(j); sndTap();
        playBunkaiSelect(j);
      }));
      panel.innerHTML = panelHTML(i);
      wirePartLink();
      afterTap();
    });
  });
  function playBunkaiSelect(i){
    stage.querySelectorAll(".comp").forEach(g2 => {
      g2.classList.toggle("dim", +g2.dataset.i !== i);
    });
    panel.innerHTML = panelHTML(i);
    wirePartLink();
    afterTap();
  }
  function wirePartLink(){
    const b = document.getElementById("btnPartLink");
    if(b) b.addEventListener("click", () => { sndTap(); gotoKanji({kanji: b.dataset.k, grade: Number(b.dataset.g)}); });
  }
  function afterTap(){
    if(tapped.size >= rec.components.length && !st(rec.kanji).b){
      setSt(rec.kanji, "b"); sndGood();
      document.getElementById("playProgress").textContent = `ぶんかい ${modeCount("bunkai")} / ${DATA.length}`;
    }
    if(tapped.size >= rec.components.length){
      setGuide("happy", "ぜんぶの パーツが 分かったね！ その字の しくみが 見えたね。");
      const r = document.getElementById("bunkaiResult");
      if(r && !r.innerHTML) { r.innerHTML = finishPanel(`<div class="result-good">ぜんぶの パーツを 見つけたね！</div>`); wireFinish(); }
    }
  }
}

/* ---------- 組み立て ---------- */
function shuffle(a){ for(let i = a.length - 1; i > 0; i--){ const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function playKumitate(rec, opts){
  const isTest = !!(opts && opts.test);
  const stage = document.getElementById("playStage");
  const panel = document.getElementById("playPanel");
  const own = rec.components.map((c, i) => ({key: labelOf(c) + "|" + c.pos, el: c.el, label: labelOf(c), pos: c.pos, d: c.d, own:true, id:"own" + i}));
  const ownEls = new Set(rec.components.map(c => c.el));
  const ownLabels = new Set(rec.components.map(c => labelOf(c)));
  const pool = [];
  DATA.forEach(r => { if(r.kanji !== rec.kanji) r.components.forEach(c => { if(!ownEls.has(c.el) && !ownLabels.has(labelOf(c))) pool.push(c); }); });
  const distract = shuffle(pool.slice()).filter((c, i, a) => a.findIndex(x => labelOf(x) === labelOf(c)) === i)
    .slice(0, Math.max(2, 6 - own.length)).map((c, i) => ({key:"__d" + i, el: c.el, label: labelOf(c), pos: c.pos, d: c.d, own:false, id:"dis" + i}));
  const palette = shuffle(own.concat(distract));
  const placed = new Array(own.length).fill(null);
  let selected = null;
  const ex = exampleOf(rec);
  const exBlank = ex ? esc(ex.s).replace(esc(rec.kanji), `<span class="blank">〇</span>`) : "";
  stage.innerHTML = `
    <div class="prompt-reading">${rec.on.map(esc).join("・")}${rec.on.length && rec.kun.length ? " ／ " : ""}${rec.kun.map(esc).join("・")}</div>
    ${ex ? `<div class="prompt-ex">${exBlank}<br><span style="font-size:15px">${esc(ex.r).replace(rec.kanji, "〇")}</span></div>` : ""}
    <div class="slotframe" id="slots"></div>
    <div class="ib-sub">パーツを タップ → 置く 場所を タップ</div>`;
  function renderSlots(){
    const sl = document.getElementById("slots");
    const areas = rec.components.map(c => { const b = bboxOf(c); return b.w * b.h; });
    const zOf = i => 1 + areas.filter(a => a > areas[i]).length;
    sl.innerHTML = rec.components.map((c, i) => {
      const b = bboxOf(c);
      const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
      const wPct = Math.max(b.w, 30) / 109 * 100;
      const hPct = Math.max(b.h, 30) / 109 * 100;
      const left = Math.min(Math.max(cx / 109 * 100 - wPct / 2, 0), 100 - wPct);
      const top = Math.min(Math.max(cy / 109 * 100 - hPct / 2, 0), 100 - hPct);
      const p = placed[i];
      const label = c.pos ? POS_JA[c.pos] : posLabelFromCenter(cx, cy);
      return `<button class="slot2 ${p ? "filled" : ""}" data-slot="${i}" style="left:${left}%;top:${top}%;width:${wPct}%;height:${hPct}%;z-index:${zOf(i)}">
        <span class="slot-pos">${label}</span>
        ${p ? svgPart(p, COMP_COLORS[i % COMP_COLORS.length]) : ""}</button>`;
    }).join("");
    sl.querySelectorAll(".slot2").forEach(s => s.addEventListener("click", () => {
      const i = +s.dataset.slot;
      if(placed[i]){ placed[i] = null; selected = null; renderAll(); sndTap(); return; }
      if(selected){ placed[i] = selected; selected = null; renderAll(); sndTap(); }
    }));
    const db = document.getElementById("btnJudge");
    if(db) db.disabled = placed.some(p => !p);
  }
  function renderPalette(){
    const pa = document.getElementById("palette");
    pa.innerHTML = palette.map(p => {
      const used = placed.includes(p);
      return `<button class="partbtn ${used ? "used" : ""} ${selected === p ? "selected" : ""}" data-id="${p.id}">${svgPart(p)}<span class="plabel">${esc(p.label || p.el)}</span></button>`;
    }).join("");
    pa.querySelectorAll(".partbtn").forEach(b => b.addEventListener("click", () => {
      selected = palette.find(p => p.id === b.dataset.id) || null;
      renderPalette(); sndTap();
    }));
  }
  function renderAll(){ renderSlots(); renderPalette(); }
  panel.innerHTML = `
    <div class="info-box"><div class="ib-title">やり方</div><div class="ib-sub">読みと 文を ヒントに、正しい パーツを 選んで 置こう。パーツの 置く 場所（うえ・した・ひだり・みぎ）も 合わせてね。</div></div>
    ${isTest ? "" : chantBox(rec, false)}
    <div class="palette" id="palette"></div>
    <div id="judgeArea"><button class="bigbtn" id="btnJudge" disabled>できた！</button></div>`;
  renderAll();
  document.getElementById("btnJudge").addEventListener("click", () => {
    const allOk = placed.every((p, i) => p && p.key === own[i].key);
    if(isTest){ testJudge(rec, allOk); return; }
    if(allOk){
      setSt(rec.kanji, "k");
      store.mistakes = store.mistakes.filter(k => k !== rec.kanji); saveStore();
      sndGood(); celebrate(); setGuide("celeb", `「${rec.kanji}」が できた！ マスターだね。`);
      stage.innerHTML = svgKanji(rec, {colored:true}) + `<div class="result-good">「${rec.kanji}」が できた！ マスター ★</div>`;
      panel.innerHTML = chantBox(rec, true) + finishPanel("");
      wireFinish();
      document.getElementById("playProgress").textContent = `くみたて ${modeCount("kumitate")} / ${DATA.length}`;
    } else {
      sndBad(); setGuide("think", "うーん、ちがう パーツが あるみたい。赤い わくと、場所を 見直してみよう。");
      if(!store.mistakes.includes(rec.kanji)){ store.mistakes.push(rec.kanji); saveStore(); }
      document.querySelectorAll(".slot2").forEach((s, i) => {
        if(placed[i] && placed[i].key !== own[i].key) s.classList.add("badslot");
      });
      document.getElementById("judgeArea").insertAdjacentHTML("beforeend", `<div class="result-bad">ちがう パーツが あるよ。赤い わくを 見直してね。</div>`);
      setTimeout(() => { const rb = document.querySelector(".result-bad"); if(rb) rb.remove(); }, 2600);
    }
  });
}

/* ---------- 構造 ---------- */
function playKozo(rec){
  const stage = document.getElementById("playStage");
  const panel = document.getElementById("playPanel");
  stage.innerHTML = svgKanji(rec, {}) + `<div class="ib-sub">この 漢字の つくりは どれかな？</div>`;
  panel.innerHTML = `<div class="opt-grid">${STRUCT_ORDER.map(s =>
    `<button class="optbtn" data-s="${s}">${STRUCT_JA[s]}</button>`).join("")}</div>${chantBox(rec, false)}<div id="kozoResult"></div>`;
  panel.querySelectorAll(".optbtn").forEach(b => b.addEventListener("click", () => {
    if(b.dataset.s === rec.structure){
      b.classList.add("correct"); sndGood(); setGuide("happy", "そのとおり！ 形の タイプが 分かったね。");
      panel.querySelectorAll(".optbtn").forEach(x => x.disabled = true);
      setSt(rec.kanji, "s");
      stage.innerHTML = svgKanji(rec, {colored:true}) + `<div class="ib-sub">${esc(formulaOf(rec))}</div>`;
      document.getElementById("kozoResult").innerHTML = finishPanel(
        `<div class="result-good">せいかい！「${rec.kanji}」は ${STRUCT_JA[rec.structure]} の つくり。</div>
         <div class="info-box"><div class="ib-sub">${esc(explOf(rec) || formulaOf(rec))}</div></div>`);
      wireFinish();
      document.getElementById("playProgress").textContent = `こうぞう ${modeCount("kozo")} / ${DATA.length}`;
    } else {
      b.classList.add("wrong"); b.disabled = true; sndBad(); setGuide("think", "うーん、ちがうみたい。形を もう一度 見てみよう。");
      setTimeout(() => b.classList.remove("wrong"), 350);
    }
  }));
}

/* ---------- 部首 ---------- */
function playBushu(rec){
  const stage = document.getElementById("playStage");
  const panel = document.getElementById("playPanel");
  stage.innerHTML = svgKanji(rec, {}) + `<div class="ib-sub">この 漢字の 部首は どれかな？</div>`;
  const names = [...new Set(DATA.map(r => r.radicalName).filter(Boolean))].filter(n => n !== rec.radicalName);
  const opts = shuffle([rec.radicalName].concat(shuffle(names).slice(0, 3)));
  panel.innerHTML = `<div class="opt-grid">${opts.map(n =>
    `<button class="optbtn" data-n="${esc(n)}">${esc(n)}</button>`).join("")}</div>${chantBox(rec, false)}<div id="bushuResult"></div>`;
  panel.querySelectorAll(".optbtn").forEach(b => b.addEventListener("click", () => {
    if(b.dataset.n === rec.radicalName){
      b.classList.add("correct"); sndGood(); setGuide("happy", "せいかい！ 部首が 分かったね。");
      panel.querySelectorAll(".optbtn").forEach(x => x.disabled = true);
      setSt(rec.kanji, "r");
      const stateNote = rec.radicalState === "whole" ? "この字は、字 そのものが 部首だよ"
        : rec.radicalState === "name" ? "この字の 部首は、辞書の 分類の 名前。パーツには 分かれないよ"
        : "赤い パーツが 部首だよ";
      stage.innerHTML = svgKanji(rec, {radical:true, radicalAll: rec.radicalState === "whole"}) + `<div class="ib-sub">${stateNote}</div>`;
      const same = DATA.filter(r => r.radicalNo === rec.radicalNo && r.kanji !== rec.kanji).map(r => r.kanji);
      document.getElementById("bushuResult").innerHTML = finishPanel(
        `<div class="result-good">せいかい！ 部首は「${esc(rec.radicalName)}」</div>
         <div class="info-box"><div class="ib-sub">場所の 種類：${esc(rec.radicalPosType)}${same.length ? `<br>同じ 部首の 漢字：${same.join("・")}` : ""}</div></div>`);
      wireFinish();
      document.getElementById("playProgress").textContent = `ぶしゅ ${modeCount("bushu")} / ${DATA.length}`;
    } else {
      b.classList.add("wrong"); b.disabled = true; sndBad(); setGuide("think", "部首は、漢字を 分類する 名前だよ。パーツを 見直してみよう。");
      setTimeout(() => b.classList.remove("wrong"), 350);
    }
  }));
}

/* ---------- テスト（かんじマスターと同じ4グループ分け） ---------- */
const TEST = {active:false, group:0, items:[], idx:0, firstTry:0, wrong:[]};
const GROUP_MARKS = ["①","②","③","④"];
function groupItems(g){
  const start = Math.floor((g - 1) * DATA.length / 4);
  const end = Math.floor(g * DATA.length / 4);
  return DATA.slice(start, end);
}
function renderTestGroups(){
  const grid = document.getElementById("testGroupGrid");
  grid.innerHTML = [1,2,3,4].map(g => {
    const items = groupItems(g);
    const done = items.filter(r => st(r.kanji).k).length;
    const pct = items.length ? Math.round(done / items.length * 100) : 0;
    return `<button class="group-card" data-g="${g}">
      <span class="gname">グループ${GROUP_MARKS[g - 1]}</span>
      <span class="gprev">${items.slice(0, 10).map(r => r.kanji).join("")}</span>
      <span class="gmeta">${items.length}字 ・ くみたて マスター ${done} / ${items.length}字</span>
      <span class="gtrack"><i style="width:${pct}%"></i></span></button>`;
  }).join("");
  grid.querySelectorAll(".group-card").forEach(b => b.addEventListener("click", () => { sndTap(); startTest(Number(b.dataset.g)); }));
  showView("view-testgroups");
}
function startTest(g){
  TEST.active = true; TEST.group = g;
  TEST.items = shuffle(groupItems(g).slice());
  TEST.idx = 0; TEST.firstTry = 0; TEST.wrong = [];
  playBackFn = () => { TEST.active = false; renderTestGroups(); };
  showView("view-play");
  nextTestQuestion();
}
function nextTestQuestion(){
  if(TEST.idx >= TEST.items.length){ finishTest(); return; }
  const rec = TEST.items[TEST.idx];
  playMode = "test"; playKanji = rec.kanji;
  document.getElementById("playTitle").innerHTML = `<ruby>テスト<rt>てすと</rt></ruby> ： グループ${GROUP_MARKS[TEST.group - 1]}`;
  document.getElementById("playProgress").textContent = `${TEST.idx + 1} / ${TEST.items.length} 問目`;
  setGuide("normal", TEST.idx === 0 ? "テストだよ。おぼえうたは おやすみ。自分の 力で 組み立てよう！" : "つぎの 漢字だよ。");
  playKumitate(rec, {test:true});
}
function testJudge(rec, allOk){
  if(allOk){
    TEST.firstTry++;
    setSt(rec.kanji, "k");
    store.mistakes = store.mistakes.filter(k => k !== rec.kanji); saveStore();
    sndGood(); setGuide("happy", "せいかい！ 一回で 組み立てられたね。");
  } else {
    if(!store.mistakes.includes(rec.kanji)){ store.mistakes.push(rec.kanji); saveStore(); }
    TEST.wrong.push(rec.kanji);
    sndBad(); setGuide("think", "ざんねん…。正しい 組み立てを 見てみよう。");
  }
  const stage = document.getElementById("playStage");
  const panel = document.getElementById("playPanel");
  stage.innerHTML = svgKanji(rec, {colored:true}) + `<div class="${allOk ? "result-good" : "result-bad"}">${allOk ? "○ せいかい！" : "× ざんねん"} 「${rec.kanji}」</div>`;
  panel.innerHTML = chantBox(rec, true) + `<button class="bigbtn" id="btnTestNext">${TEST.idx + 1 >= TEST.items.length ? "けっかを 見る →" : "つぎの 漢字 →"}</button>`;
  document.getElementById("btnTestNext").addEventListener("click", () => { sndTap(); TEST.idx++; nextTestQuestion(); });
}
function finishTest(){
  TEST.active = false;
  playBackFn = () => renderTestGroups();
  const total = TEST.items.length, ok = TEST.firstTry;
  const stage = document.getElementById("playStage");
  const panel = document.getElementById("playPanel");
  document.getElementById("playProgress").textContent = "テスト おわり";
  setGuide("celeb", ok === total ? "パーフェクト！ 全部 一回で できたね！" : "テスト おつかれさま！ まちがえた字は 分解で 見直そう。");
  celebrate();
  stage.innerHTML = `<div class="test-score">${ok} <span>/ ${total} 問</span></div><div class="result-good">一回で 組み立てられた かず</div>`;
  let html = "";
  if(TEST.wrong.length){
    html += `<div class="info-box"><div class="ib-title">まちがえた かんじ（タップで 分解を 見る）</div><div class="chip-row">${TEST.wrong.map(k => `<button class="chip" data-k="${k}">${k}</button>`).join("")}</div></div>`;
  } else {
    html += `<div class="info-box"><div class="ib-sub">まちがえた字は ありませんでした。</div></div>`;
  }
  html += `<button class="bigbtn" id="btnTestRetry">もう一度 この グループ</button>
    <button class="bigbtn sub" id="btnTestGroups">グループを えらぶ</button>`;
  panel.innerHTML = html;
  panel.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => gotoKanji({kanji: c.dataset.k, grade: curGrade})));
  document.getElementById("btnTestRetry").addEventListener("click", () => { sndTap(); startTest(TEST.group); });
  document.getElementById("btnTestGroups").addEventListener("click", () => { sndTap(); renderTestGroups(); });
}

/* ---------- パーツずかん ---------- */
function renderParts(){
  const map = new Map();
  DATA.forEach(r => {
    if(r.components.length < 2) return;
    r.components.forEach(c => {
      const nm = labelOf(c);
      if(!map.has(nm)) map.set(nm, {comp:c, kanjis:[]});
      if(!map.get(nm).kanjis.includes(r.kanji)) map.get(nm).kanjis.push(r.kanji);
    });
  });
  const list = [...map.entries()].sort((a, b) => b[1].kanjis.length - a[1].kanjis.length);
  const el = document.getElementById("partsList");
  el.innerHTML = list.map(([name, v]) =>
    `<button class="part-chip" data-p="${esc(name)}">${svgPart(v.comp)}<span class="plabel">${esc(name)}</span><span class="pcount">${v.kanjis.length}字</span></button>`).join("");
  document.getElementById("partDetail").classList.add("hidden");
  el.querySelectorAll(".part-chip").forEach(b => b.addEventListener("click", () => {
    const v = map.get(b.dataset.p);
    const d = document.getElementById("partDetail");
    d.classList.remove("hidden");
    d.innerHTML = `<h3>「${esc(b.dataset.p)}」が 入っている 漢字</h3><div class="chip-row">${v.kanjis.map(k =>
      `<button class="chip" data-k="${k}">${k}</button>`).join("")}</div>`;
    d.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => startPlay("bunkai", c.dataset.k)));
    d.scrollIntoView({behavior:"smooth"});
  }));
  showView("view-parts");
}

/* ---------- 出典・初期化 ---------- */
function init(){
  const gi = document.getElementById("guideImg");
  if(gi){ gi.src = FACE.normal; gi.alt = GUIDE_CHAR.name; }
  renderTop();
  document.getElementById("btnParts").addEventListener("click", () => { sndTap(); renderParts(); });
  document.getElementById("btnSources").addEventListener("click", () => { sndTap(); showView("view-sources"); });
  document.getElementById("btnHome").addEventListener("click", () => { renderTop(); showView("view-top"); });
  const bs = document.getElementById("btnSound");
  const updSound = () => bs.textContent = store.sound ? "🔊 おと オン" : "🔇 おと オフ";
  updSound();
  bs.addEventListener("click", () => { store.sound = !store.sound; saveStore(); updSound(); if(store.sound) sndTap(); });
  document.querySelectorAll("[data-back]").forEach(b => b.addEventListener("click", () => {
    if(b.dataset.back === "top"){ renderTop(); showView("view-top"); }
    else { renderGrade(); showView("view-grade"); }
  }));
  document.getElementById("btnPlayBack").addEventListener("click", () => { playBackFn(); });
  showView("view-top");
}
document.addEventListener("DOMContentLoaded", init);
