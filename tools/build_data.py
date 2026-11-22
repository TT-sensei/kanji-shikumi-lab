# -*- coding: utf-8 -*-
"""漢字のしくみラボ: 1年生80字の統合データ生成 v2
sources (text/data only, nothing executed):
 - kanjiapp kanji-data.js / kanjiExampleData_1.js (TT-sensei original data, fetched as text)
 - KANJIDIC2 xml.gz (EDRDG, CC BY-SA 4.0): classical radical no, stroke count
 - KanjiVG SVG per kanji (CC BY-SA 3.0): decomposition tree, positions, radical flags
Component rules: top-level groups; part-family merge; whole-kanji group merge;
hand overrides (OVERRIDES) for educational decomposition.
"""
import gzip, json, re, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

OUT = Path(__file__).resolve().parent.parent / "data"  # リポジトリ内の data/
SVG = "{http://www.w3.org/2000/svg}"
KVG = "{http://kanjivg.tagaini.net}"
Path("/tmp/kanjiapp").mkdir(exist_ok=True)
Path("/tmp/kvg").mkdir(exist_ok=True)

for fn in ("kanji-data.js", "kanjiExampleData_1.js"):
    fp = Path("/tmp/kanjiapp") / fn
    if not fp.exists():
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/TT-sensei/kanjiapp/main/{fn}", fp)
kd_gz = Path("/tmp/kanjidic2.xml.gz")
if not kd_gz.exists():
    urllib.request.urlretrieve("https://www.edrdg.org/kanjidic/kanjidic2.xml.gz", kd_gz)

src = Path("/tmp/kanjiapp/kanji-data.js").read_text(encoding="utf-8")
packed = re.search(r'1:"([^"]+)"', src).group(1)
readings, order = {}, []
for entry in packed.split("|"):
    k, r = entry.split(":", 1)
    on, kun = [], []
    for tok in r.split(","):
        tok = tok.strip()
        if tok:
            (on if re.match(r'^[ァ-ヶー]', tok) else kun).append(tok)
    readings[k] = {"on": on, "kun": kun}
    order.append(k)

exsrc = Path("/tmp/kanjiapp/kanjiExampleData_1.js").read_text(encoding="utf-8")
examples = {}
for km in re.finditer(r'"(.?)":\s*\[(.*?)\]', exsrc, re.S):
    items = re.findall(r'sentence:\s*"([^"]+)",\s*reading:\s*"([^"]+)",\s*level:\s*(\d+)', km.group(2))
    if items:
        examples[km.group(1)] = [{"s": s, "r": r, "l": int(l)} for s, r, l in items]

kd = gzip.open(kd_gz, "rt", encoding="utf-8").read()
info = {}
for block in re.findall(r"<character>.*?</character>", kd, re.S):
    lit = re.search(r"<literal>(.)</literal>", block).group(1)
    if lit in readings:
        rad = re.search(r'<rad_value rad_type="classical">(\d+)</rad_value>', block)
        st = re.search(r"<stroke_count>(\d+)</stroke_count>", block)
        info[lit] = {"radicalNo": int(rad.group(1)) if rad else None,
                     "strokes": int(st.group(1)) if st else None}

def fetch_svg(ch):
    fn = f"{ord(ch):05x}.svg"
    p = Path("/tmp/kvg") / fn
    if not p.exists():
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji/{fn}", p)
    return p

def group_paths(g):
    return [p.get("d") for p in g.iter(SVG + "path")]

def group_rad(g):
    return any(el.get(KVG + "radical") for el in g.iter())

def raw_components(root, kanji):
    """walk top level; returns list of comps with _grp ref for splitting"""
    comps = []
    def walk(g):
        for child in g:
            if child.tag == SVG + "path":
                comps.append({"el": kanji, "pos": "", "rad": False, "d": [child.get("d")], "_grp": None, "_bare": True})
            elif child.tag == SVG + "g":
                el = child.get(KVG + "element")
                if el:
                    comps.append({"el": el, "pos": child.get(KVG + "position") or "",
                                  "part": child.get(KVG + "part"), "rad": group_rad(child),
                                  "d": group_paths(child), "_grp": child})
                else:
                    before = len(comps)
                    walk(child)
                    # tag the comps that came from this no-element group
                    for c in comps[before:]:
                        c["_noel_pos"] = child.get(KVG + "position") or ""
                        if c["el"] == kanji and c.get("_bare"):
                            c["_noel_grp"] = True
                    if len(comps) == before:  # group held raw paths directly
                        comps.append({"el": None, "pos": child.get(KVG + "position") or "",
                                      "rad": group_rad(child), "d": group_paths(child), "_grp": child})
    walk(root)
    # no-element groups whose children were bare paths got flattened above as bare comps;
    # regroup consecutive bare comps that share _noel_grp marker into one None comp
    regrouped, buf = [], []
    def flush():
        if buf:
            regrouped.append({"el": None, "pos": buf[0].get("_noel_pos", ""), "rad": False,
                              "d": [d for c in buf for d in c["d"]], "_grp": None})
            buf.clear()
    for c in comps:
        if c.get("_noel_grp"):
            buf.append(c)
        else:
            flush()
            regrouped.append(c)
    flush()
    return regrouped

def merge_parts(comps, kanji):
    # 1) part-family merge (same element, part attrs, may interleave)
    out, partmap = [], {}
    for c in comps:
        if c.get("part"):
            key = c["el"]
            if key in partmap:
                partmap[key]["d"].extend(c["d"])
                partmap[key]["rad"] = partmap[key]["rad"] or c["rad"]
                continue
            partmap[key] = c
            out.append(c)
        else:
            out.append(c)
    comps = out
    # 2) whole-kanji element merge (el == kanji, except bare single leftovers handled by overrides later)
    out, whole = [], None
    for c in comps:
        if c["el"] == kanji and not c.get("_bare"):
            if whole is None:
                whole = dict(c); out.append(whole)
            else:
                whole["d"].extend(c["d"]); whole["rad"] = whole["rad"] or c["rad"]
        else:
            out.append(c)
    # 3) consecutive same (el,pos) merge
    res = []
    for c in out:
        if res and res[-1]["el"] == c["el"] and res[-1]["pos"] == c["pos"] and c["el"] is not None:
            res[-1]["d"].extend(c["d"]); res[-1]["rad"] = res[-1]["rad"] or c["rad"]
        else:
            res.append(c)
    return res

def C(el, pos, d, rad=False):
    return {"el": el, "pos": pos, "rad": rad, "d": list(d)}

# hand overrides: function(raw_comps, kanji) -> comps  (raw = after merge_parts)
def ov_split_paths(idx, specs):
    def f(comps, kanji):
        base = comps[idx]
        out, k = [], 0
        for el, pos, n in specs:
            out.append(C(el, pos, base["d"][k:k+n], base["rad"]))
            k += n
        return comps[:idx] + out + comps[idx+1:]
    return f

def ov_relabel(idx, el, pos=None):
    def f(comps, kanji):
        comps[idx] = dict(comps[idx], el=el, pos=pos if pos is not None else comps[idx]["pos"])
        return comps
    return f

def ov_whole(comps, kanji):
    d = [p for c in comps for p in c["d"]]
    rad = any(c["rad"] for c in comps)
    return [C(kanji, "", d, rad)]

OVERRIDES = {
    "先": ov_relabel(0, "龶", "top"),
    "白": ov_relabel(0, "丿", "top"),
    "赤": ov_relabel(1, "灬", "bottom"),
    "本": ov_relabel(1, "一", "bottom"),
    "虫": ov_whole, "七": ov_whole, "九": ov_whole,
    "五": ov_whole, "年": ov_whole, "八": ov_whole,
}

def split_lin(comps):
    # 森: replace 林 comp with its 木 subgroups (re-walk the group)
    out = []
    for c in comps:
        if c["el"] == "林" and c.get("_grp") is not None:
            for sub in c["_grp"]:
                if sub.tag == SVG + "g" and sub.get(KVG + "element"):
                    out.append(C(sub.get(KVG + "element"), sub.get(KVG + "position") or "bottom",
                                 group_paths(sub), group_rad(sub)))
            continue
        out.append(c)
    return out

# 画単位の分割: (内部名, 表示名, 位置, 画インデックス群)。全画を document 順に並べ替えてから適用する。
STROKE_SPLITS = {
    "二": [("一","一","top",[0]), ("一","一","bottom",[1])],
    "三": [("一","一","top",[0]), ("一","一","",[1]), ("一","一","bottom",[2])],
    "十": [("一","一","top",[0]), ("丨","丨","",[1])],
    "大": [("一","一","top",[0]), ("人","人","",[1,2])],
    "日": [("囗","囗","kamae",[0,1,3]), ("一","一","",[2])],
    "火": [("丶","丶","",[0]), ("丶","丶","",[1]), ("人","人","",[2,3])],
    "木": [("十","十","top",[0,1]), ("八","ハ","bottom",[2,3])],
    "金": [("人","人","top",[0,1]), ("一","一","",[2]), ("土","土","",[3,4,7]), ("丷","丷","bottom",[5,6])],
    "土": [("十","十","top",[0,1]), ("一","一","bottom",[2])],
    "田": [("囗","囗","kamae",[0,1,4]), ("十","十","",[2,3])],
    "目": [("囗","囗","kamae",[0,1,4]), ("二","二","",[2,3])],
    "車": [("日","日","",[0,1,2,3,5]), ("十","十","",[4,6])],
    "竹": [("竹","ケ","left",[0,1,2]), ("竹","ケ","right",[3,4,5])],
    "左": [("ナ","ナ","top",[0,1]), ("工","工","bottom",[2,3,4])],
    "王": [("三","三","",[0,2,3]), ("丨","丨","",[1])],
    "先": [("丿","ノ","top",[0]), ("土","土","",[1,2,3]), ("儿","ル","bottom",[4,5])],
    "立": [("丶","丶","top",[0]), ("一","一","",[1]), ("八","ハ","",[2,3]), ("一","一","bottom",[4])],
    "青": [("土","土","top",[0,1,2]), ("一","一","",[3]), ("月","月","bottom",[4,5,6,7])],
    "円": [("冂","冂","kamae",[0,1]), ("一","一","",[2]), ("一","一","",[3])],
    "生": [("丿","ノ","top",[0]), ("土","土","bottom",[1,2,3,4])],
    "石": [("厂","厂","top",[0,1]), ("口","口","bottom",[2,3,4])],
}
STRUCT_OVERRIDES = {"十": "parts", "大": "parts", "火": "parts", "車": "parts", "王": "parts"}
# 表示名（子ども向け）の上書き: 内部名の並びと対応する表示名リスト
LABELS = {
    "休": ["イ","木"], "学": ["ツ","冖","子"], "四": ["囗","ル"], "文": ["亠","メ"],
    "気": ["气","メ"], "六": ["亠","ハ"], "上": ["ト","一"], "下": ["一","ト"],
    "貝": ["目","ハ"], "見": ["目","ル"], "千": ["ノ","十"], "白": ["ノ","日"],
    "足": ["口","止"], "右": ["ナ","口"],
}
def apply_stroke_split(comps, kanji):
    strokes = [d for c in comps for d in c["d"]]
    out = []
    for el, label, pos, idxs in STROKE_SPLITS[kanji]:
        out.append({"el": el, "label": label, "pos": pos, "rad": False,
                    "d": [strokes[i] for i in idxs]})
    return out

RADICAL_NAMES = {1:"いち",2:"ぼう",5:"おつ",7:"に",9:"ひと",10:"にんにょう",11:"いる",12:"はち",
    13:"まきがまえ",17:"うけばこ",19:"ちから",24:"じゅう",30:"くち",31:"くにがまえ",32:"つち",
    36:"ゆうべ",37:"だい",38:"おんな",39:"こ",42:"しょう",46:"やま",47:"かわ",48:"こう",51:"かん",
    64:"て",67:"ぶん",72:"ひ",74:"つき",75:"き",77:"とめる",84:"きがまえ",85:"みず",86:"ひ",
    94:"いぬ",96:"たま",100:"せい",102:"た",106:"しろ",109:"め",112:"いし",116:"あな",117:"たつ",
    118:"たけ",120:"いと",128:"みみ",140:"くさ",142:"むし",147:"みる",154:"かい",155:"あか",
    157:"あし",159:"くるま",167:"かね",173:"あめ",174:"あお",180:"おと"}
VARIANT_NAMES = {"亻":"にんべん","氵":"さんずい","扌":"てへん","艹":"くさかんむり","宀":"うかんむり",
    "冖":"わかんむり","灬":"れっか","阝":"こざとへん"}
POS_TYPE = {"left":"へん","right":"つくり","top":"かんむり","bottom":"あし","kamae":"かまえ"}
RADICAL_ELEMENT = {1:"一",2:"丨",5:"乙",7:"二",9:"人",10:"儿",11:"入",12:"八",13:"冂",17:"凵",19:"力",
    24:"十",30:"口",31:"囗",32:"土",36:"夕",37:"大",38:"女",39:"子",42:"小",46:"山",47:"川",48:"工",
    51:"干",64:"手",67:"文",72:"日",74:"月",75:"木",77:"止",84:"气",85:"水",86:"火",94:"犬",96:"玉",
    100:"生",102:"田",106:"白",109:"目",112:"石",116:"穴",117:"立",118:"竹",120:"糸",128:"耳",
    140:"艹",142:"虫",147:"見",154:"貝",155:"赤",157:"足",159:"車",167:"金",173:"雨",174:"青",180:"音"}
RADICAL_VARIANTS = {9:["亻","人"],85:["氵","水"],64:["扌","手"],96:["玉","王"],140:["艹"],147:["見"]}

def derive_structure(comps):
    if len(comps) <= 1:
        return "single"
    pos = [c["pos"] for c in comps]
    if any(p == "kamae" for p in pos):
        return "enclose"
    if any(p in ("top", "bottom") for p in pos):
        return "vertical"
    if any(p in ("left", "right") for p in pos):
        return "horizontal"
    return "parts"

records, problems = [], []
for ch in order:
    tree = ET.parse(fetch_svg(ch))
    sp = next(g for g in tree.getroot().iter(SVG + "g") if (g.get("id") or "").startswith("kvg:StrokePaths"))
    comps = merge_parts(raw_components(list(sp)[0], ch), ch)
    if ch in STROKE_SPLITS:
        comps = apply_stroke_split(comps, ch)
    if ch == "森":
        comps = split_lin(comps)
    if ch in OVERRIDES:
        comps = OVERRIDES[ch](comps, ch)
    for c in comps:
        c.pop("_grp", None); c.pop("part", None); c.pop("_bare", None)
        c.pop("_noel_grp", None); c.pop("_noel_pos", None)
        c.setdefault("label", c["el"])
    if ch in LABELS:
        for c, lab in zip(comps, LABELS[ch]):
            c["label"] = lab
    if any(c["el"] is None for c in comps):
        problems.append((ch, "None element remains"))
    rno = info[ch]["radicalNo"]
    targets = RADICAL_VARIANTS.get(rno, [RADICAL_ELEMENT.get(rno, "")])
    rad_comp = next((c for c in comps if c["el"] in targets), None)
    for c in comps:
        c["rad"] = (c is rad_comp)
    if RADICAL_ELEMENT.get(rno) == ch or ch in {"王"}:
        radical_state = "whole"   # 字そのもの（または玉の形違いの王）が部首
    elif rad_comp is not None:
        radical_state = "part"    # 部首が構成部品として見える
    else:
        radical_state = "name"    # 辞書上の分類のみ（独立表示できない）
    rname = RADICAL_NAMES.get(rno, "")
    if rad_comp and rad_comp["el"] in VARIANT_NAMES:
        rname = VARIANT_NAMES[rad_comp["el"]]
    if rad_comp is None:
        ptype = "そのほか"
    elif rad_comp["pos"] == "bottom" and rad_comp["el"] not in ("儿", "龰", "灬", "心"):
        ptype = "そのほか"
    else:
        ptype = POS_TYPE.get(rad_comp["pos"], "そのほか")
    records.append({"kanji": ch, "grade": 1, "on": readings[ch]["on"], "kun": readings[ch]["kun"],
        "strokes": info[ch]["strokes"], "radicalNo": rno, "radicalName": rname,
        "radicalPosType": ptype, "radicalState": radical_state,
        "structure": STRUCT_OVERRIDES.get(ch, derive_structure(comps)),
        "components": [{"el": c["el"], "label": c.get("label", c["el"]), "pos": c["pos"], "rad": bool(c["rad"]), "d": c["d"]} for c in comps],
        "examples": examples.get(ch, [])})

print("structures:", Counter(r["structure"] for r in records))
print("comp counts:", Counter(len(r["components"]) for r in records))
print("problems:", problems)
for r in records:
    comps = " ".join(f"{c['el']}@{c['pos'] or '-'}{'R' if c['rad'] else ''}({len(c['d'])})" for c in r["components"])
    print(f"{r['kanji']} 部{r['radicalNo']}{r['radicalName']}/{r['radicalPosType']} {r['structure']:10s} | {comps}")
(OUT / "kanji1.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "radicals.json").write_text(json.dumps(RADICAL_NAMES, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote kanji1.json", (OUT / "kanji1.json").stat().st_size, "bytes")
# アプリが読む JS 版も同時生成する
(OUT / "kanji1.js").write_text("window.KSL_G1=" + json.dumps(records, ensure_ascii=False) + ";", encoding="utf-8")
_txt = Path(__file__).resolve().parent.parent / "original" / "text1.json"
if _txt.exists():
    _t = json.loads(_txt.read_text(encoding="utf-8"))
    (_txt.parent / "text1.js").write_text("window.KSL_TEXT=" + json.dumps(_t, ensure_ascii=False) + ";", encoding="utf-8")
    print("wrote kanji1.js and original/text1.js")
