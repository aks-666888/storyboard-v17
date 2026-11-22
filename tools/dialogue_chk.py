# -*- coding: utf-8 -*-
"""台词节奏硬检（dialogue_chk）：M1 剧本正文的台词密度 + 不许一路自语没人接。

来源：v2.9.52 用户点出「台词节奏不紧凑」。实跑对照——三份合格稿中间段
每百字 1.56/1.56/1.88 句、平均每段 2.2/2.2/3.0 句、零「没人答」冷场；
停电稿 0.59 句、每段 1.0 句、4 处冷场。因此定两条硬判：
  D1 中间段每百字台词 ≥1.0 句，且平均每段 ≥1.5 句（要你一句我一句，不要单人从头说到尾）
  D2 「抛出话却没人应」≤1 次

只数 ③ 故事剧本正文，且去掉开头交代段（那段按规矩不写台词）。
③ 段缺失由别的检查项管，这里不重复报。
"""
import re, sys, io, os

MIN_PER_100 = 1.0       # 中间段每百字台词下限
MIN_PER_PARA = 1.5      # 中间段平均每段台词下限（密对白类）
# 冷峻白描／诗性散文：话少是手法，不是缺陷（悬疑、写实、散文体本来就靠动作和白描撑），
# 只把「每段台词」放宽到 0.6，每百字下限不放（否则整片可以一句台词都没有）。
SPARSE_STYLES = (u"冷峻白描", u"诗性散文")
SPARSE_PER_PARA = 0.6
MAX_COLD = 1            # 「抛出话却没人应」最多几次
NO_REPLY_WORDS = [
    u"没人答", u"没答话", u"无人应答", u"无人应", u"没人应", u"不肯应",
    u"不答话", u"没应声", u"不应声", u"没回话", u"没人回", u"无人答",
]


def body(text):
    m = re.search(u"##\\s*③[^\\n]*\\n(.*?)(?=\\n##\\s*④|\\Z)", text, re.S)
    return m.group(1) if m else u""


def paras(body_text):
    return [p for p in re.split(r"\n\s*\n", body_text) if p.strip()]


def _style(text):
    m = re.search(u"- 风格：([^\n|｜]+)", text)
    return (m.group(1) if m else u"")


def run_all(text, path=None):
    """返回 [(编号, 检查名, 是否通过, 说明)]，M1 交付门直接勾。"""
    b = body(text)
    if not b.strip():
        return []
    ps = paras(b)
    mid = ps[1:] if len(ps) > 1 else []          # 去掉开头交代段
    seg = u"\n".join(mid)
    dlg = re.findall(u"「[^」]*」", seg)
    chars = len(re.sub(r"[\s「」]", u"", seg))
    density = (len(dlg) * 100.0 / chars) if chars else 0.0
    per_para = (len(dlg) * 1.0 / len(mid)) if mid else 0.0
    cold = sum(seg.count(w) for w in NO_REPLY_WORDS)
    st = _style(text)
    need_para = SPARSE_PER_PARA if any(w in st for w in SPARSE_STYLES) else MIN_PER_PARA
    ok1 = (not mid) or (density >= MIN_PER_100 and per_para >= need_para)
    return [
        (u"D1", u"台词密度与交锋（中间段每百字≥%.1f句、每段≥%.1f句）" % (MIN_PER_100, need_para),
         ok1, u"现每百字 %.2f 句、每段 %.2f 句（%d 句／%d 段／%d 字）｜风格「%s」"
         % (density, per_para, len(dlg), len(mid), chars, st or u"未登记")),
        (u"D2", u"不许一路自语没人接（冷场 ≤%d 次）" % MAX_COLD,
         cold <= MAX_COLD, u"「抛出话却没人应」写了 %d 次" % cold),
    ]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        good = (u"## ③ 故事剧本\n"
                u"楼道口老陈把快递递过去，年轻人说：「别拆，那是我寄的。」老陈低头核对存根。\n\n"
                u"年轻人问：「里头装的什么？」老陈说：「一叠取件条。」他把条子塞回袋里。\n\n"
                u"年轻人说：「头一页是你签的。」老陈说：「我在这儿分过件。」把那页翻出来没再说话。\n")
        bad = (u"## ③ 故事剧本\n"
               u"楼道口整栋停电，老陈拎着一包白蜡烛从一楼往上送，一层六户他挨家敲门。\n\n"
               u"老陈说：「六楼就剩这户。」门里不肯应，再敲还是没人应，他把蜡烛捏在手里。\n\n"
               u"老陈说：「屋里有人吧。」没人答，他把蜡烛插进门前的铁皮盒，手按在盒沿上。\n\n"
               u"老陈说：「是您画的吧。」门里没答话，拐杖点了两下，他贴着门板又听一回。\n")
        g = {x[0]: x[2] for x in run_all(good)}
        b = {x[0]: x[2] for x in run_all(bad)}
        assert g.get(u"D1") and g.get(u"D2"), u"合格密对白稿被误伤：%s" % g
        assert not b.get(u"D1") and not b.get(u"D2"), u"散稿没拦下：%s" % b
        print("dialogue_chk 正反考题通过（密对白过／独白散稿拦）")
        sys.exit(0)
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(u"用法：python dialogue_chk.py <剧本.md> 或 --test")
        sys.exit(1)
    t = io.open(sys.argv[1], encoding="utf-8").read()
    for code, name, ok, detail in run_all(t, sys.argv[1]):
        print(u"[%s] %s %s — %s" % (u"PASS" if ok else u"FAIL", code, name, detail))
