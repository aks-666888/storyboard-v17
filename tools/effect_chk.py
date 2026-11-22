# -*- coding: utf-8 -*-
"""effect_chk.py —— 按「这片要什么效果」核结构（v2.9.39）

一句话：短片不是只有催泪一种。先选效果，再照那种效果的结构核；选哪种都不许混着来。
效果七类，每片登记一种（开题卡：- 效果：X）：
  让人哭 共情 ／ 让人爽 打脸 ／ 让人悬 悬念 ／ 让人笑 喜剧
  让人怕 惊悚 ／ 让人燃 热血 ／ 让人暖 治愈
每条判据都是关系与位置，不看字数。
"""
import io
import re
import sys

EFFECTS = [u"让人哭", u"让人爽", u"让人悬", u"让人笑", u"让人怕", u"让人燃", u"让人暖"]

SUPPRESS = [u"不", u"没", u"退", u"拒", u"拦", u"推", u"赶", u"挡", u"拦下"]
FLIP = [u"反", u"终于", u"赢", u"拿回", u"翻", u"按回", u"塞回", u"认"]
THREAT = [u"刀", u"血", u"锁", u"黑", u"裂", u"砸", u"追", u"抓", u"掐", u"拽", u"湿", u"撞"]
LAUGH = [u"误会", u"认错", u"错了", u"以为", u"结果"]
HEAT = [u"上", u"冲", u"顶", u"喊", u"吼", u"咬", u"拼", u"撑", u"扛"]
WARM = [u"给", u"分", u"递到", u"塞进", u"按回", u"留下", u"放着"]
REVEAL = [u"才", u"原来", u"才发现", u"翻开", u"认出", u"看清"]


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


def _effect(t):
    for ln in t.split(u"\n"):
        st = ln.strip()
        if not st.startswith(u"- 效果"):
            continue
        for k in EFFECTS:
            if k in st:
                return k
        return None
    return None


def _count(paras, words, lo=0, hi=None):
    seg = paras[lo:hi]
    return sum(p.count(w) for p in seg for w in words)


def _checks(eff, paras):
    n = len(paras)
    half = max(1, n // 2)
    out = []
    if eff == u"让人哭":
        out.append((u"E1 前半有压制、后半有认账（错认才疼）",
                    [] if _count(paras, SUPPRESS, 0, half) >= 1 and _count(paras, FLIP, half) >= 1 else
                    [u"前半压制 %d 处，后半翻/认 %d 处" % (_count(paras, SUPPRESS, 0, half), _count(paras, FLIP, half))]))
        out.append((u"E2 有一处迟到才知道（信息在后面才翻）",
                    [] if _count(paras, REVEAL, half) >= 1 else [u"后半没出现「才／原来／认出」这类迟到揭示"]))
    if eff == u"让人爽":
        out.append((u"E1 前半至少两次被挡",
                    [] if _count(paras, SUPPRESS, 0, half) >= 2 else
                    [u"前半被挡只有 %d 次" % _count(paras, SUPPRESS, 0, half)]))
        out.append((u"E2 后半至少一次翻盘，且翻在有人的场面里",
                    [] if _count(paras, FLIP, half) >= 1 else [u"后半没有翻盘动作"]))
    if eff == u"让人悬":
        q = sum(p.count(u"？") + p.count(u"?") for p in paras)
        tail = sum(1 for p in paras if any(w in p[-40:] for w in [u"没", u"不", u"还没", u"等", u"停"]))
        hang = _count(paras, [u"没", u"还没", u"等", u"停", u"锁着"])
        out.append((u"E1 有未解的问题被抛出",
                    [] if (q >= 1 or _count(paras, REVEAL) >= 1 or hang >= 1) else [u"全篇没有一个没答的问题"]))
        need = max(1, n // 2)
        out.append((u"E2 段落收在没落地的那一刻（至少 %d 段）" % need,
                    [] if tail >= need else [u"收在悬处的段落只有 %d 段" % tail]))
    if eff == u"让人笑":
        out.append((u"E1 有错认／误会（先让人当真）",
                    [] if _count(paras, LAUGH) >= 2 else [u"错认／误会只出现 %d 次" % _count(paras, LAUGH)]))
        out.append((u"E2 同一个笑料重复到第三次才收",
                    [] if _count(paras, LAUGH) >= 3 else [u"笑料没有三连，只有 %d 次" % _count(paras, LAUGH)]))
    if eff == u"让人怕":
        out.append((u"E1 威胁物在画面里出现过两次以上",
                    [] if _count(paras, THREAT) >= 2 else [u"威胁物只出现 %d 次" % _count(paras, THREAT)]))
        out.append((u"E2 主角有拦不住的动作（而不是只站着怕）",
                    [] if _count(paras, [u"想", u"伸手", u"跑", u"退", u"锁上", u"抓住"]) >= 1 else
                    [u"没有拦不住／做不到的动作"]))
    if eff == u"让人燃":
        out.append((u"E1 有明确的要什么（目标说出口或做出来）",
                    [] if _count(paras, [u"要", u"得", u"必须", u"一定"]) >= 1 else [u"没有说出／做出目标"]))
        out.append((u"E2 有力气使出去的动作（冲／顶／扛／撑）",
                    [] if _count(paras, HEAT) >= 1 else [u"没有出力动作"]))
    if eff == u"让人暖":
        out.append((u"E1 有给出／分给的动作，两次以上",
                    [] if _count(paras, WARM) >= 2 else [u"给出动作只有 %d 次" % _count(paras, WARM)]))
        out.append((u"E2 结尾回到开头那件东西上",
                    [] if any(w in paras[-1] for w in [u"还", u"原", u"那", u"又"]) else
                    [u"末段没回照开头的东西"]))
    return out


def run_all(path):
    t = io.open(path, encoding="utf-8").read()
    paras = _paras(t)
    eff = _effect(t)
    if not eff:
        return [(u"E0 先登记效果卡（这片要哪一种反应）",
                 [u"开题卡没写「- 效果：让人哭／爽／悬／笑／怕／燃／暖」，不知道要什么效果就没法核"])]
    return [(u"E0 效果卡已登记（%s）" % eff, [])] + _checks(eff, paras)


def _selftest():
    cases = [
        (u"让人哭", [u"他没给钱，转身走。", u"老周才认出照片上的人。"], True),
        (u"让人哭", [u"他接过钱。", u"他走了。"], False),
        (u"让人爽", [u"先拦下他。", u"又拦住他。", u"他终于拿回了本子。"], True),
        (u"让人悬", [u"门锁着。", u"他没回来。"], True),
        (u"让人笑", [u"他认错了人。", u"又认错一次。", u"第三次才认对。"], True),
        (u"让人怕", [u"刀口对着门。", u"他伸手去抓。"], True),
        (u"让人燃", [u"他要走到底。", u"他扛起箱子。"], True),
        (u"让人暖", [u"他把钱递到孩子手里。", u"把饼分给隔壁。", u"钱还压在碗下。"], True),
    ]
    ok = 0
    for eff, paras, want in cases:
        bad = [b for _, b in _checks(eff, paras)]
        got = not any(bad)
        ok += (got == want)
        print(u"[%s] %s" % (u"PASS" if got == want else u"FAIL", eff))
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
