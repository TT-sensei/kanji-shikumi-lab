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

for fn in ("kanji-data.js", "kanjiExampleData_1.js", "kanjiExampleData_2.js", "kanjiExampleData_3.js"):
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

def parse_examples(fn):
    ex = {}
    t = Path("/tmp/kanjiapp", fn).read_text(encoding="utf-8")
    for km in re.finditer(r'"(.?)":\s*\[(.*?)\]', t, re.S):
        items = re.findall(r'sentence:\s*"([^"]+)",\s*reading:\s*"([^"]+)",\s*level:\s*(\d+)', km.group(2))
        if items:
            ex[km.group(1)] = [{"s": a, "r": b, "l": int(c)} for a, b, c in items]
    return ex
examples = parse_examples("kanjiExampleData_1.js")
packed2 = re.search(r'2:"([^"]+)"', src).group(1)
readings2, order2 = {}, []
for entry in packed2.split("|"):
    k, r = entry.split(":", 1)
    on, kun = [], []
    for tok in r.split(","):
        tok = tok.strip()
        if tok:
            (on if re.match(r'^[ァ-ヶー]', tok) else kun).append(tok)
    readings2[k] = {"on": on, "kun": kun}
    order2.append(k)
examples2 = parse_examples("kanjiExampleData_2.js")
packed3 = re.search(r'3:"([^"]+)"', src).group(1)
readings3, order3 = {}, []
for entry in packed3.split("|"):
    k, r = entry.split(":", 1)
    on, kun = [], []
    for tok in r.split(","):
        tok = tok.strip()
        if tok:
            (on if re.match(r'^[ァ-ヶー]', tok) else kun).append(tok)
    readings3[k] = {"on": on, "kun": kun}
    order3.append(k)
examples3 = parse_examples("kanjiExampleData_3.js")

kd = gzip.open(kd_gz, "rt", encoding="utf-8").read()
info = {}
for block in re.findall(r"<character>.*?</character>", kd, re.S):
    lit = re.search(r"<literal>(.)</literal>", block).group(1)
    if lit in readings or lit in readings2 or lit in readings3:
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
    157:"あし",159:"くるま",167:"かね",173:"あめ",174:"あお",180:"おと",
    3:"てん",8:"なべぶた",15:"にすい",18:"かたな",21:"さじ",27:"がんだれ",29:"また",33:"さむらい",
    35:"ふゆがしら",40:"うかんむり",41:"すん",50:"はば",53:"まだれ",57:"ゆみ",58:"けいがしら",
    59:"さんづくり",60:"ぎょうにんべん",61:"こころ",63:"とびらのと",66:"ぼくにょう",69:"おの",
    70:"ほう",73:"いわく",76:"あくび",80:"はは",82:"け",88:"ちち",93:"うし",101:"もちいる",
    111:"や",113:"しめす",115:"のぎ",119:"こめ",124:"はね",125:"おい",130:"にく",132:"みずから",
    137:"ふね",139:"いろ",144:"ぎょうがまえ",146:"にし",148:"つの",149:"ごん",150:"たに",
    156:"そうにょう",162:"しんにょう",166:"さと",168:"ながい",169:"もん",181:"おおがい",
    182:"かぜ",184:"しょく",185:"くび",187:"うま",189:"たか",195:"うお",196:"とり",
    199:"むぎ",201:"き",203:"くろ",
    4:"の",6:"はねぼう",14:"わかんむり",23:"はこがまえ",28:"む",44:"しかばね",56:"しきがまえ",
    78:"がつ",104:"やまいだれ",105:"はつがしら",107:"けがわ",108:"さら",123:"ひつじ",143:"ち",
    145:"ころも",151:"まめ",158:"み",161:"たつ",163:"おおざと",164:"とり",170:"こざと",
    172:"ふるとり",176:"めん",209:"はな"}
VARIANT_NAMES = {"亻":"にんべん","氵":"さんずい","扌":"てへん","艹":"くさかんむり","宀":"うかんむり",
    "冖":"わかんむり","灬":"れっか","阝":"こざとへん","刂":"りっとう","忄":"りっしんべん",
    "礻":"ねへん","ネ":"ねへん","阜":"こざとへん","邑":"おおざと","衤":"ころもへん"}
POS_TYPE = {"left":"へん","right":"つくり","top":"かんむり","bottom":"あし","kamae":"かまえ"}
RADICAL_ELEMENT = {1:"一",2:"丨",5:"乙",7:"二",9:"人",10:"儿",11:"入",12:"八",13:"冂",17:"凵",19:"力",
    24:"十",30:"口",31:"囗",32:"土",36:"夕",37:"大",38:"女",39:"子",42:"小",46:"山",47:"川",48:"工",
    51:"干",64:"手",67:"文",72:"日",74:"月",75:"木",77:"止",84:"气",85:"水",86:"火",94:"犬",96:"玉",
    100:"生",102:"田",106:"白",109:"目",112:"石",116:"穴",117:"立",118:"竹",120:"糸",128:"耳",
    140:"艹",142:"虫",147:"見",154:"貝",155:"赤",157:"足",159:"車",167:"金",173:"雨",174:"青",180:"音",
    3:"丶",8:"亠",15:"冫",18:"刀",21:"匕",27:"厂",29:"又",33:"士",35:"夂",40:"宀",41:"寸",50:"巾",
    53:"广",57:"弓",58:"彐",59:"彡",60:"彳",61:"心",63:"戸",66:"攵",69:"斤",70:"方",73:"曰",76:"欠",
    80:"毋",82:"毛",88:"父",93:"牛",101:"用",111:"矢",113:"示",115:"禾",119:"米",124:"羽",125:"老",
    130:"肉",132:"自",137:"舟",139:"色",144:"行",146:"襾",148:"角",149:"言",150:"谷",156:"走",
    162:"辶",166:"里",168:"長",169:"門",181:"頁",182:"風",184:"食",185:"首",187:"馬",189:"高",
    195:"魚",196:"鳥",199:"麦",201:"黄",203:"黒",
    4:"丿",6:"亅",14:"冖",23:"匚",28:"厶",44:"尸",56:"弋",78:"歹",104:"疒",105:"癶",107:"皮",
    108:"皿",123:"羊",143:"血",145:"衣",151:"豆",158:"身",161:"辰",163:"邑",164:"酉",170:"阜",
    172:"隹",176:"面",209:"鼻"}
RADICAL_VARIANTS = {9:["亻","人"],85:["氵","水"],64:["扌","手"],96:["玉","王"],140:["艹"],147:["見"],
    18:["刂","刀"],40:["宀"],61:["忄","心"],80:["毋","母"],113:["礻","示","ネ"],125:["耂","老"],
    130:["月","肉"],149:["言"],156:["走"],162:["辶"],184:["飠","食"],201:["黄"],203:["黒"],
    86:["火","灬"],
    4:["丿"],6:["亅"],14:["冖"],23:["匚"],28:["厶"],44:["尸"],56:["弋"],78:["歹"],104:["疒"],
    105:["癶"],107:["皮"],108:["皿"],123:["羊"],143:["血"],145:["衣","衤"],151:["豆"],158:["身"],
    161:["辰"],163:["邑"],164:["酉"],170:["阜"],172:["隹"],176:["面"],209:["鼻"]}

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

# ================= 2年生 =================
# ユーザーの唱え歌データ（部品リスト）を正として、KanjiVG の分解ツリーと照合する。
_draft = (Path(__file__).resolve().parent.parent / "original" / "chants2-user-draft.js").read_text(encoding="utf-8")
USER2 = {}
for _m in re.finditer(r'\["(.)",\[(.*?)\],"([^"]+)"\]', _draft):
    _ps = [x.strip().strip('"') for x in _m.group(2).split(",") if x.strip()]
    USER2[_m.group(1)] = {"parts": _ps, "chant": _m.group(3)}

ALIAS2 = {"イ": ["亻"], "ル": ["儿"], "ハ": ["八", "丷"], "メ": ["乂"], "ノ": ["丿"], "ト": ["卜"],
          "ツ": ["⺍", "丷", "⺌"], "ナ": ["丆", "𠂇"], "ム": ["厶"], "リ": ["刂"], "ミ": ["彡"], "ソ": ["丷", "八"],
          "ヨ": ["彐", "⺕"], "ネ": ["礻", "示"], "ク": ["勹", "𠂊"], "ヒ": ["匕"], "ラ": [], "マ": [],
          "辶": ["⻌", "辶"], "易": ["昜", "易"], "廿": ["龷", "廿"], "丷": ["八", "丷"], "止": ["龰", "止"]}

def parse_node(g):
    node = {"el": g.get(KVG + "element"), "pos": g.get(KVG + "position") or "",
            "rad": bool(g.get(KVG + "radical")), "items": []}
    for child in g:
        if child.tag == SVG + "path":
            node["items"].append(("p", child.get("d")))
        elif child.tag == SVG + "g":
            node["items"].append(("g", parse_node(child)))
    return node

def node_flat(node, counter):
    """(画インデックス, d) のリストを document 順に返す"""
    out = []
    for kind, v in node["items"]:
        if kind == "p":
            out.append((counter[0], v)); counter[0] += 1
        else:
            out.extend(node_flat(v, counter))
    return out

def collect_nodes(node, acc):
    for kind, v in node["items"]:
        if kind == "g":
            acc.append(v)
            collect_nodes(v, acc)

def annotate_flat(root):
    """全ノードに全体通しの画インデックス付き _flat を付ける"""
    counter = [0]
    def rec(node):
        flat = []
        for kind, v in node["items"]:
            if kind == "p":
                flat.append((counter[0], v)); counter[0] += 1
            else:
                flat.extend(rec(v))
        node["_flat"] = flat
        return flat
    rec(root)
    return counter[0]

def align_parts(root, parts, alias=None):
    """ユーザーの部品リストに一致するツリーノードの分割を探す。見つからなければ None。
    候補の優先順: 内部名が合うノード → 同名ノードの合体（囲みの枠など） → 名なしグループ → 浮いた画のまとまり。"""
    total = annotate_flat(root)
    nodes = []
    collect_nodes(root, nodes)
    tier1, tier3 = [], []
    by_el = {}
    for n in nodes:
        flat = n["_flat"]
        if not flat:
            continue
        if n["el"]:
            tier1.append({"idxs": [i for i, _ in flat], "d": [d for _, d in flat], "el": n["el"], "pos": n["pos"]})
            by_el.setdefault(n["el"], []).append(n)
        else:
            tier3.append({"idxs": [i for i, _ in flat], "d": [d for _, d in flat], "el": None, "pos": n["pos"]})
    tier2 = []
    for el, ns_ in by_el.items():
        if len(ns_) >= 2:
            pairs = sorted([p for n in ns_ for p in n["_flat"]])
            tier2.append({"idxs": [i for i, _ in pairs], "d": [d for _, d in pairs], "el": el, "pos": ns_[0]["pos"]})
    # 浮いた画（root・名なしグループ直下の画）の最大ラン
    tier4 = []
    def loose_runs(node, is_root=False):
        run = []
        for kind, v in node["items"]:
            if kind == "p":
                run.append(v)
            else:
                if run:
                    tier4.append(run); run = []
                if v["el"] is None:
                    loose_runs(v)
        if run:
            tier4.append(run)
    loose_runs(root, True)
    idx_of = {}
    for i, d in root["_flat"]:
        idx_of[d] = i
    tier4 = [{"idxs": [idx_of[d] for d in run], "d": list(run), "el": None, "pos": ""} for run in tier4 if run]
    cands = tier1 + tier2 + tier3 + tier4
    def els_for(label):
        return set((alias or ALIAS2).get(label, [])) | {label}
    def search(pi, used, min_start, strict):
        if pi == len(parts):
            return [] if len(used) == total else None
        label = parts[pi]
        els = els_for(label)
        for c in cands:
            if c["el"] is not None and c["el"] not in els:
                continue
            st = set(c["idxs"])
            if st & used:
                continue
            if strict and min(c["idxs"]) < min_start:
                continue
            rest = search(pi + 1, used | st, min(c["idxs"]), strict)
            if rest is not None:
                return [c] + rest
        return None
    return search(0, frozenset(), -1, True) or search(0, frozenset(), -1, False)

def radical_stroke_idxs(root):
    counter = [0]
    idx_of = {}
    def walk(node):
        s = set()
        for kind, v in node["items"]:
            if kind == "p":
                s.add(counter[0]); counter[0] += 1
            else:
                s |= walk(v)
        if node["rad"]:
            idx_of[id(node)] = s
        return s
    walk(root)
    out = set()
    for v in idx_of.values():
        out |= v
    return out

STRUCT_OVERRIDES2 = {"近": "enclose", "週": "enclose", "道": "enclose", "通": "enclose", "遠": "enclose"}
# 画単位の分割（2年生）: 自動照合で決まらない字を、画の形を実測して手で決めたもの。
# (内部名, 表示名, 位置, 画インデックス群)
STROKE_SPLITS2 = {
    "言": [("亠","亠","top",[0,1]), ("二","二","",[2,3]), ("口","口","bottom",[4,5,6])],
    "用": [("冂","冂","kamae",[0,1,2]), ("十","十","",[3,4])],
    "食": [("人","人","top",[0,1]), ("良","良","bottom",[2,3,4,5,6,7,8])],
    "肉": [("冂","冂","kamae",[0,1]), ("人","人","",[2,3]), ("人","人","",[4,5])],
    "首": [("丷","丷","top",[0,1]), ("一","一","",[2]), ("自","自","bottom",[3,4,5,6,7,8])],
    "毎": [("丿","ノ","top",[0]), ("母","母","bottom",[1,2,3,4,5])],
    "夜": [("亠","亠","top",[0,1]), ("亻","イ","",[2,3]), ("夕","夕","bottom",[4,5,6,7])],
    "来": [("木","木","",[0,3,4,5,6]), ("丷","ソ","top",[1,2])],
    "里": [("田","田","top",[0,1,2,3,4]), ("土","土","bottom",[5,6])],
    "半": [("丷","丷","top",[0,1]), ("二","二","",[2,3]), ("丨","丨","",[4])],
    "弟": [("丷","ソ","top",[0,1]), ("弓","弓","",[2,3,4,5]), ("丿","ノ","bottom",[6])],
    "帰": [("刂","リ","left",[0,1]), ("彐","ヨ","",[2,3,4,5,6]), ("巾","巾","right",[7,8,9])],
    "楽": [("白","白","top",[0,1,2,3,4]), ("幺","幺","",[5,6,7,8]), ("木","木","bottom",[9,10,11,12])],
    "交": [("六","六","top",[0,1,2,3]), ("乂","メ","bottom",[4,5])],
    "午": [("丿","ノ","top",[0]), ("干","十","bottom",[1,2,3])],
    "南": [("十","十","top",[0,1]), ("冂","冂","kamae",[2,3]), ("丷","ソ","",[4,5]), ("干","十","bottom",[6,7,8])],
}
records2, unmatched2 = [], []
for ch in order2:
    tree = ET.parse(fetch_svg(ch))
    sp = next(g for g in tree.getroot().iter(SVG + "g") if (g.get("id") or "").startswith("kvg:StrokePaths"))
    root = parse_node(list(sp)[0])
    uparts = USER2[ch]["parts"]
    rad_idxs = radical_stroke_idxs(root)
    counter = [0]
    all_flat = node_flat(root, counter)
    idx_of_d = {}
    for i, d in all_flat:
        idx_of_d.setdefault(d, i)
    if ch in STROKE_SPLITS2:
        comps = [{"el": el, "label": lab, "pos": pos, "rad": False,
                  "d": [all_flat[i][1] for i in idxs], "_idxs": list(idxs)}
                 for el, lab, pos, idxs in STROKE_SPLITS2[ch]]
    elif not uparts:
        comps = [{"el": ch, "label": ch, "pos": "", "rad": False, "d": [d for _, d in all_flat], "_idxs": [i for i, _ in all_flat]}]
    else:
        got = align_parts(root, uparts)
        if got is None:
            unmatched2.append(ch)
            comps = merge_parts(raw_components(list(sp)[0], ch), ch)
            for c in comps:
                c.pop("_grp", None); c.pop("part", None); c.pop("_bare", None)
                c.pop("_noel_grp", None); c.pop("_noel_pos", None)
                c["label"] = c["el"]
                c["_idxs"] = [idx_of_d.get(d, -1) for d in c["d"]]
        else:
            comps = [{"el": c["el"], "label": lab, "pos": c["pos"], "rad": False,
                      "d": c["d"], "_idxs": c["idxs"]} for c, lab in zip(got, uparts)]
    rno = info[ch]["radicalNo"]
    targets = set(RADICAL_VARIANTS.get(rno, [])) | {RADICAL_ELEMENT.get(rno, "")}
    rad_comp = None
    for c in comps:
        if c["el"] in targets or (rad_idxs and set(c["_idxs"]) == rad_idxs):
            rad_comp = c
            break
    for c in comps:
        c["rad"] = (c is rad_comp)
        c.pop("_idxs", None)
    if RADICAL_ELEMENT.get(rno) == ch or (len(comps) == 1 and rad_comp is not None):
        radical_state = "whole"
    elif rad_comp is not None:
        radical_state = "part"
    else:
        radical_state = "name"
    rname = RADICAL_NAMES.get(rno, "")
    if rad_comp and rad_comp["el"] in VARIANT_NAMES:
        rname = VARIANT_NAMES[rad_comp["el"]]
    if rad_comp is None:
        ptype = "そのほか"
    elif rad_comp["pos"] == "bottom" and rad_comp["el"] not in ("儿", "龰", "灬", "心"):
        ptype = "そのほか"
    else:
        ptype = POS_TYPE.get(rad_comp["pos"], "そのほか")
    records2.append({"kanji": ch, "grade": 2, "on": readings2[ch]["on"], "kun": readings2[ch]["kun"],
        "strokes": info[ch]["strokes"], "radicalNo": rno, "radicalName": rname,
        "radicalPosType": ptype, "radicalState": radical_state,
        "structure": STRUCT_OVERRIDES2.get(ch, derive_structure(comps)),
        "components": [{"el": c["el"], "label": c.get("label", c["el"]), "pos": c["pos"], "rad": bool(c["rad"]), "d": c["d"]} for c in comps],
        "examples": examples2.get(ch, [])})

print("G2 structures:", Counter(r["structure"] for r in records2))
print("G2 comp counts:", Counter(len(r["components"]) for r in records2))
print("G2 radical states:", Counter(r["radicalState"] for r in records2))
print("G2 unmatched (fallback to KanjiVG top-level):", len(unmatched2), unmatched2)
print("G2 empty radicalName:", [r["kanji"] for r in records2 if not r["radicalName"]])
(OUT / "kanji2.json").write_text(json.dumps(records2, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "kanji2.js").write_text("window.KSL_G2=" + json.dumps(records2, ensure_ascii=False) + ";", encoding="utf-8")
_txt2 = Path(__file__).resolve().parent.parent / "original" / "text2.json"
if _txt2.exists():
    _t2 = json.loads(_txt2.read_text(encoding="utf-8"))
    (_txt2.parent / "text2.js").write_text("window.KSL_TEXT2=" + json.dumps(_t2, ensure_ascii=False) + ";", encoding="utf-8")
print("wrote kanji2.json", (OUT / "kanji2.json").stat().st_size, "bytes")


# ================= 3年生 =================
# ユーザーが他AIと作成した唱え歌データ（部品リスト）を正として、2年生と同じ方法で照合する。
_draft3 = (Path(__file__).resolve().parent.parent / "original" / "chants3-user-draft.js").read_text(encoding="utf-8")
USER3 = {}
for _m in re.finditer(r'\["(.)",\[(.*?)\],"([^"]+)"\]', _draft3):
    _ps = [x.strip().strip('"') for x in _m.group(2).split(",") if x.strip()]
    USER3[_m.group(1)] = {"parts": _ps, "chant": _m.group(3)}

ALIAS3 = dict(ALIAS2)
ALIAS3.update({"阝": ["阜", "邑", "⻖", "⻏"], "艹": ["艸", "艹"], "コ": ["𠂉", "𠂊"],
               "匚": ["匸"], "食": ["飠"], "巳": ["己"], "小": ["⺌"], "入": ["人"],
               "水": ["氺"], "柬": ["東"], "乚": ["乙", "乚"], "羊": ["⺷"], "爫": ["⺤"],
               "自": ["𠂤"]})

STRUCT_OVERRIDES3 = {"運": "enclose", "進": "enclose", "送": "enclose", "速": "enclose",
                     "追": "enclose", "返": "enclose", "遊": "enclose"}
# 歯: ユーザーの部品「人」は画が合わない（下部は凵+米）ため「凵」に直す（報告済みの判断）。
USER3["歯"]["parts"] = ["止", "凵", "米"]
# 画単位の分割（3年生）: 自動照合で決まらない字を、KanjiVGの画タイプと画順で実測して手で決めたもの。
# (内部名, 表示名, 位置, 画インデックス群)
STROKE_SPLITS3 = {
    "央": [("冂","冂","kamae",[0,1]), ("大","大","bottom",[2,3,4])],
    "屋": [("尸","尸","tare",[0,1,2]), ("一","一","",[3]), ("厶","ム","",[4,5]), ("土","土","bottom",[6,7,8])],
    "開": [("門","門","kamae",[0,1,2,3,4,5,6,7]), ("二","二","",[8,9]), ("丿","ノ","",[10]), ("丨","丨","",[11])],
    "寒": [("宀","宀","top",[0,1,2]), ("艹","艹","",[3,4,5]), ("二","二","",[6,7]), ("八","ハ","",[8,9]), ("冫","冫","bottom",[10,11])],
    "感": [("戊","戊","top",[0,1,6,7,8]), ("一","一","",[2]), ("口","口","",[3,4,5]), ("心","心","bottom",[9,10,11,12])],
    "宮": [("宀","宀","top",[0,1,2]), ("口","口","",[3,4,5]), ("丿","丨","",[6]), ("口","口","bottom",[7,8,9])],
    "局": [("尸","尸","tare",[0,1,2]), ("勹","一","",[3]), ("口","口","bottom",[4,5,6])],
    "決": [("氵","氵","left",[0,1,2]), ("𠂉","コ","",[3,4]), ("人","人","right",[5,6])],
    "研": [("石","石","left",[0,1,2,3,4]), ("二","二","",[5,6]), ("丿","ノ","",[7]), ("丨","丨","",[8])],
    "実": [("宀","宀","top",[0,1,2]), ("三","ソ","",[3,4]), ("大","大","bottom",[5,6,7])],
    "重": [("丿","ノ","top",[0]), ("一","一","",[1]), ("里","里","bottom",[2,3,4,5,6,7,8])],
    "商": [("亠","亠","top",[0,1]), ("八","ハ","",[2,3]), ("冂","冂","kamae",[4,5]), ("儿","ル","",[6,7]), ("口","口","bottom",[8,9,10])],
    "勝": [("月","月","left",[0,1,2,3]), ("丷","ソ","top",[4,5]), ("夫","夫","",[6,7,8,9]), ("力","力","bottom",[10,11])],
    "送": [("辶","辶","nyo",[6,7,8]), ("丷","ソ","top",[0,1]), ("天","夫","",[2,3,4,5])],
    "族": [("方","方","left",[0,1,2,3]), ("丿","ノ","",[4]), ("一","一","",[5]), ("矢","矢","right",[6,7,8,9,10])],
    "調": [("言","言","left",[0,1,2,3,4,5,6]), ("冂","冂","kamae",[7,8]), ("士","土","",[9,10,11]), ("口","口","bottom",[12,13,14])],
    "豆": [("一","一","top",[0]), ("口","口","",[1,2,3]), ("一","一","",[6]), ("八","ハ","bottom",[4,5])],
    "島": [("丿","ノ","top",[0]), ("白","白","",[1,2,3,4,5]), ("一","一","",[6]), ("山","山","bottom",[7,8,9])],
    "勉": [("𠂊","ク","",[0,1]), ("日","日","",[2,3,4,5]), ("儿","ル","bottom",[6,7]), ("力","力","",[8,9])],
    "味": [("口","口","left",[0,1,2]), ("一","一","",[3]), ("木","木","right",[4,5,6,7])],
    "遊": [("辶","辶","nyo",[9,10,11]), ("方","方","",[0,1,2,3]), ("丿","ノ","",[4]), ("一","一","",[5]), ("子","子","",[6,7,8])],
    "予": [("マ","マ","top",[0,1]), ("一","一","",[2]), ("亅","亅","bottom",[3])],
    "羊": [("䒑","ソ","top",[0,1,2]), ("王","王","bottom",[3,4,5])],
    "旅": [("方","方","left",[0,1,2,3]), ("丿","ノ","",[4]), ("一","一","",[5]), ("亻","人","",[6,7]), ("人","人","bottom",[8,9])],
}

records3, unmatched3 = [], []
for ch in order3:
    tree = ET.parse(fetch_svg(ch))
    sp = next(g for g in tree.getroot().iter(SVG + "g") if (g.get("id") or "").startswith("kvg:StrokePaths"))
    root = parse_node(list(sp)[0])
    uparts = USER3[ch]["parts"]
    rad_idxs = radical_stroke_idxs(root)
    counter = [0]
    all_flat = node_flat(root, counter)
    idx_of_d = {}
    for i, d in all_flat:
        idx_of_d.setdefault(d, i)
    if ch in STROKE_SPLITS3:
        comps = [{"el": el, "label": lab, "pos": pos, "rad": False,
                  "d": [all_flat[i][1] for i in idxs], "_idxs": list(idxs)}
                 for el, lab, pos, idxs in STROKE_SPLITS3[ch]]
    elif not uparts:
        comps = [{"el": ch, "label": ch, "pos": "", "rad": False, "d": [d for _, d in all_flat], "_idxs": [i for i, _ in all_flat]}]
    else:
        got = align_parts(root, uparts, ALIAS3)
        if got is None:
            unmatched3.append(ch)
            comps = merge_parts(raw_components(list(sp)[0], ch), ch)
            for c in comps:
                c.pop("_grp", None); c.pop("part", None); c.pop("_bare", None)
                c.pop("_noel_grp", None); c.pop("_noel_pos", None)
                c["label"] = c["el"]
                c["_idxs"] = [idx_of_d.get(d, -1) for d in c["d"]]
        else:
            comps = [{"el": c["el"], "label": lab, "pos": c["pos"], "rad": False,
                      "d": c["d"], "_idxs": c["idxs"]} for c, lab in zip(got, uparts)]
    rno = info[ch]["radicalNo"]
    targets = set(RADICAL_VARIANTS.get(rno, [])) | {RADICAL_ELEMENT.get(rno, "")}
    rad_comp = None
    for c in comps:
        if c["el"] in targets or (rad_idxs and set(c["_idxs"]) == rad_idxs):
            rad_comp = c
            break
    for c in comps:
        c["rad"] = (c is rad_comp)
        c.pop("_idxs", None)
    if RADICAL_ELEMENT.get(rno) == ch or (len(comps) == 1 and rad_comp is not None):
        radical_state = "whole"
    elif rad_comp is not None:
        radical_state = "part"
    else:
        radical_state = "name"
    rname = RADICAL_NAMES.get(rno, "")
    if rad_comp and rad_comp["el"] in VARIANT_NAMES:
        rname = VARIANT_NAMES[rad_comp["el"]]
    if rad_comp is None:
        ptype = "そのほか"
    elif rad_comp["pos"] == "bottom" and rad_comp["el"] not in ("儿", "龰", "灬", "心"):
        ptype = "そのほか"
    else:
        ptype = POS_TYPE.get(rad_comp["pos"], "そのほか")
    records3.append({"kanji": ch, "grade": 3, "on": readings3[ch]["on"], "kun": readings3[ch]["kun"],
        "strokes": info[ch]["strokes"], "radicalNo": rno, "radicalName": rname,
        "radicalPosType": ptype, "radicalState": radical_state,
        "structure": STRUCT_OVERRIDES3.get(ch, derive_structure(comps)),
        "components": [{"el": c["el"], "label": c.get("label", c["el"]), "pos": c["pos"], "rad": bool(c["rad"]), "d": c["d"]} for c in comps],
        "examples": examples3.get(ch, [])})

print("G3 structures:", Counter(r["structure"] for r in records3))
print("G3 comp counts:", Counter(len(r["components"]) for r in records3))
print("G3 radical states:", Counter(r["radicalState"] for r in records3))
print("G3 unmatched (fallback to KanjiVG top-level):", len(unmatched3), unmatched3)
print("G3 empty radicalName:", [r["kanji"] for r in records3 if not r["radicalName"]])
(OUT / "kanji3.json").write_text(json.dumps(records3, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "kanji3.js").write_text("window.KSL_G3=" + json.dumps(records3, ensure_ascii=False) + ";", encoding="utf-8")
_txt3 = Path(__file__).resolve().parent.parent / "original" / "text3.json"
if _txt3.exists():
    _t3 = json.loads(_txt3.read_text(encoding="utf-8"))
    (_txt3.parent / "text3.js").write_text("window.KSL_TEXT3=" + json.dumps(_t3, ensure_ascii=False) + ";", encoding="utf-8")
print("wrote kanji3.json", (OUT / "kanji3.json").stat().st_size, "bytes")
