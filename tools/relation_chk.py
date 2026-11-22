# -*- coding: utf-8 -*-
"""relation_chk.py —— 查「关系」不查「字数」（v2.9.38）

一句话：通不通、顺不顺，是关系问题——谁指谁、几件、动到哪、因果立不立、转折有没有对立面。
字数只说明节奏，不说明对错，所以这里一个字数判据都没有。

R1 他／她指的是谁：同一段里出现两个以上人物时，代称容易指飞
R2 数目对不对得上：同一件东西，前后说的数量不一致
R3 动作有没有落点：推／递／塞／放之后必须写落到哪
R4 因果立不立得住：写了「因为／所以／于是」，同段必须有能当原因的事件
R5 转折有没有对立面：写了「却／反倒／可是」，同段必须有相反的状态
"""
import io
import re
import sys

VERB = [u"撑", u"掀", u"关", u"开", u"推", u"递", u"塞", u"放", u"按", u"抽", u"捏", u"捡", u"擦", u"挂", u"捞", u"夹",
        u"倒", u"扣", u"扔", u"搁", u"摆", u"搬", u"抬", u"挪", u"拉", u"拽", u"揣", u"装"]
PLACE = [u"到", u"在", u"进", u"给", u"上", u"里", u"下", u"边", u"旁", u"内", u"外", u"手", u"袋", u"台", u"柜", u"地", u"口", u"角", u"缝", u"回", u"盒", u"兜", u"架", u"桶", u"盘", u"屉"]
CAUSE = [u"因为", u"所以", u"于是", u"因此"]
# 「倒」单字会撞上「倒扣／倒手／倒水」这类实义动词，只认成句的转折词
TURN = [u"却", u"反倒", u"可是", u"反而", u"倒是"]
OPPOSITE = [u"没", u"不", u"停", u"空", u"湿", u"冷", u"暗", u"抖", u"歪", u"断", u"卡"]
NUM = u"一二两三四五六七八九十几半"
THINGS = [u"硬币", u"零钱", u"钱", u"张", u"包", u"串", u"根", u"枚", u"叠", u"杯", u"瓶", u"条", u"页", u"筒"]


def _names(text):
    out = set()
    for ln in text.split(u"\n"):
        for m in re.finditer(u"([\u4e00-\u9fa5]{2,4})（[男女]", ln):
            out.add(m.group(1))
    return out


def _paras(t):
    on, body = False, []
    for ln in t.split(u"\n"):
        st = ln.strip()
        if st.startswith(u"## ③"):
            on = True
            continue
        if on and st.startswith(u"## "):
            break
        if on and st and not re.match(r"^场[ \u3000]*\d+", st):
            if re.match(r"^[\u4e00-\u9fa5]{1,4}（[^）]{4,}）：", st):
                continue
            body.append(st)
    return body


def r_pronoun(paras, names):
    bad = []
    for i, p in enumerate(paras, 1):
        hit = [n for n in names if n in p]
        if len(hit) >= 2 and len(re.findall(u"他|她", p)) >= 5:
            bad.append(u"段 %d 里有 %s 和「他」混着用：代称容易指飞（%s）"
                       % (i, u"、".join(hit), p[:20]))
    return bad


def r_count(paras):
    bad = []
    got = {}
    for p in paras:
        for m in re.finditer(u"([%s]+)(枚|包|张|串|根|条|块|杯|页|个|只|颗|把|叠)([\u4e00-\u9fa5]{1,3})" % NUM, p):
            q, thing = m.group(1), m.group(3)
            thing = re.sub(u"^[的了]", u"", thing)
            if any(thing.startswith(x) for x in (u"天", u"年", u"月", u"日", u"时", u"夜")):
                continue
            if thing in THINGS or len(thing) >= 2:
                got.setdefault(thing, set()).add(q)
    conv = {u"一": 1, u"二": 2, u"两": 2, u"三": 3, u"四": 4, u"五": 5, u"六": 6, u"七": 7, u"八": 8, u"九": 9, u"半": 0.5}
    for thing, qs in got.items():
        vals = {conv[q] for q in qs if q in conv}
        if len(vals) >= 2 and max(vals) <= 9:
            bad.append(u"「%s」前后数目对不上：%s" % (thing, u"／".join(sorted(qs))))
    return bad


def r_landing(paras, names):
    bad = []
    core = [u"递", u"塞", u"推", u"放", u"挂", u"按", u"扣"]
    for i, p in enumerate(paras, 1):
        for cl in re.split(u"[。；，]", p):
            if not any(v in cl for v in core):
                continue
            if not (u"他" in cl or u"她" in cl or any(n in cl for n in names)):
                continue
            if re.search(u"拖把|门|伞|椅|盖子", cl):
                continue
            if any(w in cl for w in PLACE):
                continue
            bad.append(u"段 %d 移交动作没写落到哪：%s" % (i, cl.strip()[:18]))
    return bad


def r_cause(paras):
    bad = []
    for i, p in enumerate(paras, 1):
        if any(w in p for w in CAUSE):
            if not any(w in p for w in VERB):
                bad.append(u"段 %d 写了因果，却没有能当事的动作：%s" % (i, p[:18]))
    return bad


def r_turn(paras):
    bad = []
    for i, p in enumerate(paras, 1):
        if any(w in p for w in TURN):
            cl = p
            if not any(w in cl for w in OPPOSITE):
                bad.append(u"段 %d 写了转折，却没有对立面：%s" % (i, p[:18]))
    return bad


STYLES = [u"冷峻白描", u"抒情细节", u"市井口语", u"诗性散文"]


def r_style(t):
    if u"风格" not in t:
        return [u"开题卡没登记风格：先定这片走哪种大师指纹（冷峻白描／抒情细节／市井口语／诗性散文），没有卡就没法对尺子"]
    for ln in t.split(u"\n"):
        st = ln.strip()
        if not st.startswith(u"- 风格"):
            continue
        if any(k in st for k in STYLES):
            return []
        return [u"登记的风格不在四类里：%s" % st[:18]]
    return [u"开题卡没写「- 风格：…」这一行：先定这片走哪种大师指纹，没有卡就没法对尺子"]


def run_all(path):
    t = io.open(path, encoding="utf-8").read()
    paras = _paras(t)
    names = _names(t)
    return [(u"R1 代称指得清（他／她是谁）", r_pronoun(paras, names)),
            (u"R2 数目前后对得上", r_count(paras)),
            (u"R3 动作有落点（动到哪）", r_landing(paras, names)),
            (u"R4 因果立得住", r_cause(paras)),
            (u"R5 转折有对立面", r_turn(paras)),
            (u"R6 风格卡已登记（挑哪套大师指纹）", r_style(t))]


def _selftest():
    cases = [
        (u"两个人物加他指飞", r_pronoun([u"老周和阿哲在柜台边，他把包递过去，他又退开，他站住，他才放低，他又回头，他咳了一声。"], {u"老周", u"阿哲"}), True),
        (u"单人物他清楚", r_pronoun([u"老周在柜台边，他把伞递过去。"], {u"老周"}), False),
        (u"数目打架", r_count([u"他数了两枚硬币。", u"桌上还剩三枚硬币。"]), True),
        (u"数目一致", r_count([u"他数了两枚硬币。", u"他把两枚硬币推过去。"]), False),
        (u"动作没落点", r_landing([u"他把包递。"], set()), True),
        (u"动作有落点", r_landing([u"他把包递到老周手里。"], set()), False),
        (u"空因果", r_cause([u"因为下雨，他很冷。"]), True),
        (u"实因果", r_cause([u"因为下雨，他把伞撑开。"]), False),
        (u"空转折", r_turn([u"他本以为会赢，却很高兴。"]), True),
        (u"实转折", r_turn([u"他本以为会赢，却停了手。"]), False),
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
            for b in bad[:6]:
                print(u"    ", b)
