# -*- coding: utf-8 -*-
"""craft_chk.py —— 作家／编剧技法的可判定部分（M1 剧本层）

K1 展示不告诉（麦基《故事》）：禁心理词、禁叙述者替人物下判断
K2 解说押后（麦基）：台词不许解释动机、不许社交寒暄
K3 契诃夫之枪：开篇出现的具名道具，后文必须再用到
K4 开篇与结尾镜像（斯奈德《救猫咪》Final Image）：首末段共享同一件具名物
K5 中点假胜假败（斯奈德 50% 处）：中段必须有一次得而复失或失而复得
K6 抽象词零容忍：幸福／温暖／感动／命运／成长这类词不许进正文
K7 白描细节（汪曾祺式）：每段至少一处可触细节（量词＋实物、材质、灰／湿／皱／毛边）
"""
import io
import re
import sys

PSY = [u"心里", u"感到", u"觉得", u"明白了", u"懂了", u"回忆起", u"想起", u"难过", u"害怕",
       u"紧张", u"感动", u"温暖", u"心酸", u"委屈", u"愤怒", u"他心想", u"她知道他"]
ABSTRACT = [u"幸福", u"温暖", u"感动", u"命运", u"成长", u"治愈", u"救赎", u"历练", u"正能量",
            u"人生", u"岁月静好", u"释然", u"亲情的力量"]
SMALLTALK = [u"你好", u"谢谢", u"再见", u"没事", u"没关系", u"不好意思", u"辛苦了", u"麻烦你"]
EXPLAIN = [u"因为", u"所以", u"其实我是", u"我这是为了", u"的原因", u"我是想"]
TOUCH = [u"串", u"道", u"摊", u"张", u"枚", u"包", u"条", u"截", u"层", u"角", u"毛", u"灰", u"湿", u"皱", u"折", u"圈"]
NAMED = [u"货架", u"纸巾", u"照片", u"硬币", u"伞", u"抽屉", u"烟盒", u"纸杯", u"抹布", u"塑料夹", u"手机",
         u"纸条", u"旧闹钟", u"螺丝刀", u"放大镜", u"绒布", u"登记簿", u"存根", u"取件条",
         u"纸包", u"牛皮纸包", u"关东煮", u"货架", u"纸巾"]


_PROP_HINT = (u"题眼道具", u"题眼", u"关键道具", u"道具")
_PROP_LINE = re.compile(r"^[\s\-*>|#]*[|]?\s*(?:题眼道具|题眼|关键道具|道具)\s*(?:[|：:])\s*(.+)$", re.M)
_PAREN = re.compile(r"（[^）]*）|\([^\)]*\)")
_PROP_SPLIT = re.compile(r"[、，,；;/／|]+")


def _props(path):
    """本片自己登记过的具名道具：读开题卡里「题眼道具：」那一行。
    每片道具都不同，写死清单必然漏判新题材，所以以稿内登记为准，
    括号里的定语与解释先剥掉，只留道具名本身。"""
    try:
        t = io.open(path, encoding="utf-8").read()
    except Exception:
        return []
    out = []
    for m in _PROP_LINE.finditer(t):
        val = _PAREN.sub(u"", m.group(1)).strip()
        for part in _PROP_SPLIT.split(val):
            it = part.strip().strip(u"*-|> ")
            if 2 <= len(it) <= 8 and u"道具" not in it and u"题眼" not in it and it not in out:
                out.append(it)
    return out


def _split(path):
    t = io.open(path, encoding="utf-8").read()
    lines = t.split(u"\n")
    on, body = False, []
    for ln in lines:
        st = ln.strip()
        if st.startswith(u"## ③"):
            on = True
            continue
        if on and st.startswith(u"## "):
            break
        if on and st and not re.match(r"^场[ \u3000]*\d+", st):
            body.append(st)
    paras, cur = [], None
    for st in body:
        if re.match(r"^[\u4e00-\u9fa5]{1,4}（[^）]{4,}）：", st):
            if cur is not None:
                cur[1].append(st)
            continue
        cur = [st, []]
        paras.append(cur)
    return paras


def _prose(paras):
    return [p[0] for p in paras]


def k_show(paras):
    return [u"替人物下判断／直说心理：%s" % w for p in _prose(paras) for w in PSY if w in p]


def k_explain(paras):
    bad = []
    for p in paras:
        for d in p[1]:
            for w in SMALLTALK:
                if w in d:
                    bad.append(u"台词是社交寒暄：%s" % d[16:36])
            for w in EXPLAIN:
                if w in d:
                    bad.append(u"台词解释动机：%s" % d[16:36])
    return bad


def k_gun(paras, props=None):
    """开篇（前 1/3）出现的具名道具，全文出现次数必须 ≥2。
    查的对象是本片登记过的道具；没登记才退回旧样表。"""
    n = len(paras)
    early = u"".join(_prose(paras)[:max(1, n // 3)])
    whole = u"".join(_prose(paras))
    bad = []
    for it in (props or NAMED):
        if it in early and whole.count(it) < 2:
            bad.append(u"%s 开篇亮了枪，后文没用上" % it)
    return bad


def k_mirror(paras, key=None, props=None):
    """开篇与结尾必须有一件是同一件具名物（镜像）。
    候选物 = 本片登记的道具 + 题眼 + 旧样表：只要任一件在首末都在，就算镜像成立。
    不同题材道具各不同，只认固定表会误判新片，只认登记又怕稿里没登记，所以取并集。"""
    first, last = _prose(paras)[0], _prose(paras)[-1]
    cands = list(props or []) + list(NAMED) + ([key] if key else [])
    common = [it for it in cands if it and it in first and it in last]
    if not common:
        return [u"开篇与结尾没有共享具名物（缺结尾镜像）"]
    return []


def _key(path):
    t = io.open(path, encoding="utf-8").read()
    for ln in t.split(u"\n"):
        if u"题眼道具" in ln:
            m = re.search(u"题眼道具[：:](.+)", ln)
            if not m:
                continue
            val = re.sub(r"（[^）]*）|\([^)]*\)", u"", m.group(1)).strip().strip(u"。")
            if u"的" in val:
                val = val.split(u"的")[-1].strip()
            val = re.sub(u"^[一那这]+(张|把|部|只|条|个|支|枚)", u"", val).strip(u"「」“” ")
            if val:
                return val
    return None


def k_midpoint(paras):
    n = len(paras)
    mid = _prose(paras)[n // 3:2 * n // 3 + 1]
    mark = [u"以为", u"原来", u"没等", u"刚", u"反倒", u"却"]
    if not any(w in m for m in mid for w in mark):
        return [u"中段没有得而复失／失而复得（缺中点翻转）"]
    return []


def k_abstract(paras):
    t = u"".join(_prose(paras)) + u"".join(d for p in paras for d in p[1])
    return [u"抽象词进正文：%s" % w for w in ABSTRACT if w in t]


def k_detail(paras):
    bad = []
    for i, p in enumerate(_prose(paras), 1):
        if not any(w in p for w in TOUCH):
            bad.append(u"段 %d 没有可触细节：%s" % (i, p[:18]))
    return bad


def run_all(path):
    paras = _split(path)
    if not paras:
        return [(u"K0 正文可解析", [u"没解析到正文段"])]
    _k = _key(path)
    _pr = _props(path) or None
    return [(u"K1 展示不告诉（麦基）", k_show(paras)),
            (u"K2 台词不寒暄不解释动机（麦基·解说押后）", k_explain(paras)),
            (u"K3 契诃夫之枪（开篇道具后文必用）", k_gun(paras, _pr)),
            (u"K4 开篇与结尾镜像（斯奈德）", k_mirror(paras, _k, _pr)),
            (u"K5 中点假胜假败（斯奈德 50%）", k_midpoint(paras)),
            (u"K6 抽象词零容忍", k_abstract(paras)),
            (u"K7 每段一处白描细节（汪曾祺式）", k_detail(paras))]


def _selftest():
    cases = [
        (u"直说心理", k_show([[u"他心里一沉，感到害怕。", []]]), True),
        (u"展示代替告知", k_show([[u"他把伞收拢，手在伞柄上停了两秒。", []]]), False),
        (u"寒暄台词", k_explain([[u"他递过伞。", [u"老周（男·55）：「谢谢你啊。」"]]]), True),
        (u"对抗台词", k_explain([[u"他递过伞。", [u"老周（男·55）：「明天还你。」"]]]), False),
        (u"枪没用上", k_gun([[u"他抄起螺丝刀。", []]]), True),
        (u"枪用上了", k_gun([[u"他抄起螺丝刀。", []], [u"螺丝刀磕在台面上。", []]]), False),
        (u"无镜像", k_mirror([[u"他把伞塞过去。", []], [u"他走进雨里。", []]]), True),
        (u"有镜像", k_mirror([[u"他把伞塞过去。", []], [u"他握着那把伞走进雨里。", []]]), False),
        (u"抽象词", k_abstract([[u"那一刻很温暖。", []]]), True),
        (u"无抽象词", k_abstract([[u"硬币按回他手心。", []]]), False),
    ]
    ok = 0
    for name, bad, want in cases:
        got = bool(bad)
        ok += (got == want)
        print(u"[%s] %s" % (u"PASS" if got == want else u"FAIL", name))
    print(u"结论：%d/%d" % (ok, len(cases)))
    return ok == len(cases)


if __name__ == u"__main__":
    if sys.argv[1:2] == [u"--test"]:
        sys.exit(0 if _selftest() else 1)
    for p in sys.argv[1:]:
        print(u"==", p)
        for name, bad in run_all(p):
            print(u"[%s] %s" % (u"PASS" if not bad else u"FAIL", name))
            for b in bad:
                print(u"    ", b)
