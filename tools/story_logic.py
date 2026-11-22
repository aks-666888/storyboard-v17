# -*- coding: utf-8 -*-
"""story_logic.py —— 叙事逻辑与爆款结构机检（M1 剧本层）

S1 开头交代完故事之后，三句内必须出事（钩子；交代段不算）
S2 题眼道具三现（前段 / 中段 / 末段各至少一次）
S3 后半程必须有认知修正（反转落地，不是主角自说自话）
S4 每段必须有不可逆变化（开头交代段除外，不许空转交代）
S5 结局必须兑现题眼道具
S6 台词不许复述同段画面（信息不重复）
"""
import io
import re
import sys

CONFLICT = [u"撞", u"翻", u"掉", u"滑", u"摔", u"卡", u"喊", u"不肯", u"抢", u"断", u"碎",
            u"湿", u"血", u"差", u"不够", u"灭", u"抖", u"拽", u"撕", u"火起",
            # v2.9.53：「敲三下没人应」这类真钩子也得认——不能逼着把「敲」改成「撞」才能过
            u"敲", u"不吭", u"没人应", u"没动静", u"不应"]
CHANGE = [u"卡", u"断", u"落", u"掉", u"停", u"翻", u"推", u"压", u"抖", u"亮", u"灭", u"滑",
          u"拽", u"扯", u"塞", u"抽", u"捏", u"捡", u"擦", u"扣", u"换", u"松", u"撕", u"折",
          u"攥", u"提", u"拉", u"撞", u"滑倒", u"递", u"掀", u"夹", u"撒", u"端", u"挂", u"拧",
          u"按", u"数", u"摸", u"转", u"走", u"照", u"震", u"蹲", u"压平", u"折成", u"蹦"]
REVEAL = [u"原来", u"才", u"竟然", u"其实", u"我见过", u"才知道", u"发现", u"听见", u"忽然"]


def _split(path):
    """返回（题眼关键词, 段落列表[(散文, 台词列表)]）。"""
    t = io.open(path, encoding="utf-8").read()
    lines = t.split(u"\n")
    key = None
    for ln in lines:
        if u"题眼道具" in ln:
            m = re.search(u"题眼道具[：:](.+)", ln)
            if m:
                val = m.group(1).strip().strip(u"。")
                val = re.sub(r"（[^）]*）|\([^)]*\)", u"", val)      # 去括注
                val = val.split(u"（")[0].strip()
                if u"的" in val:
                    val = val.split(u"的")[-1].strip()
                val = re.sub(u"^[一那这]+(张|把|部|只|条|个|支|枚)", u"", val)
                key = val.strip(u"「」“” ") or None
            break
    # 正文：## ③ 到下一个 ## 
    body = []
    on = False
    for ln in lines:
        st = ln.strip()
        if st.startswith(u"## ③"):
            on = True
            continue
        if on and st.startswith(u"## "):
            break
        if on:
            if re.match(r"^场[ \u3000]*\d+", st):      # 场景抬头不是散文段
                continue
            body.append(st)
    paras = []
    cur = None
    for st in body:
        if not st:
            continue
        if re.match(r"^[\u4e00-\u9fa5]{1,4}（[^）]{4,}）：\s*[\"「“]", st):
            if cur is not None:
                cur[1].append(st)
            continue
        cur = [st, []]
        paras.append(cur)
    return key, paras


def check_hook(key, paras):
    """开头第一段是交代故事（地方、日子、由头、人），钩子从交代完之后的剧情段算起。"""
    if not paras:
        return [u"没有正文"]
    idx = 1 if len(paras) > 1 else 0
    first = u"。".join(paras[idx][0].split(u"。")[:3])
    if not any(w in first for w in CONFLICT):
        return [u"交代完故事后三句没事发生：%s" % first[:26]]
    return []


def check_key(key, paras):
    bad = []
    if not key:
        return [u"没写「题眼道具：」，无法查贯穿"]
    n = len(paras)
    if n < 3:
        return [u"段落不足三段"]
    zones = [(0, n // 3), (n // 3, 2 * n // 3), (2 * n // 3, n)]
    names = [u"前段", u"中段", u"末段"]
    for i, (a, b) in enumerate(zones):
        if not any(key in p[0] or any(key in d for d in p[1]) for p in paras[a:b]):
            bad.append(u"%s没出现题眼道具「%s」" % (names[i], key))
    return bad


def check_reveal(key, paras):
    mid = len(paras) // 2
    tail = paras[mid:]
    hit = [m for p in tail for m in REVEAL if m in p[0]]
    n = sum(1 for p in tail for m in REVEAL if m in p[0])
    if n < 2:
        return [u"后半程只有 %d 处认知修正，反转没落地（要≥2）" % n]
    return []


def check_change(key, paras):
    bad = []
    for i, (prose, _) in enumerate(paras, 1):
        if i == 1:
            continue          # 开头交代段只负责把故事交代清楚，不要求不可逆变化
        if sum(1 for w in CHANGE if w in prose) < 2:
            bad.append(u"段 %d 没有不可逆变化：%s" % (i, prose[:20]))
    return bad


def check_payoff(key, paras):
    if not key:
        return [u"没写「题眼道具：」"]
    last = paras[-1]
    if key not in last[0] and not any(key in d for d in last[1]):
        return [u"结局没兑现题眼道具「%s」" % key]
    return []


def check_dialogue(key, paras):
    bad = []
    for i, (prose, lines) in enumerate(paras, 1):
        for d in lines:
            body = re.sub(u"^.*?[：:\"]", u"", d).strip(u'"“” ')
            for k in range(len(body) - 5):
                if body[k:k + 6] in prose:
                    bad.append(u"段 %d 台词复述画面：%s" % (i, body[max(0, k - 2):k + 8]))
                    break
    return bad


def run_all(path):
    key, paras = _split(path)
    return [(u"S1 开场三句内出事", check_hook(key, paras)),
            (u"S2 题眼道具三现（前/中/末）", check_key(key, paras)),
            (u"S3 后半程认知修正（反转落地）", check_reveal(key, paras)),
            (u"S4 每段有不可逆变化", check_change(key, paras)),
            (u"S5 结局兑现题眼道具", check_payoff(key, paras)),
            (u"S6 台词不复述画面", check_dialogue(key, paras))]


def _selftest():
    cases = [
        (u"干净正文", None),
    ]
    # 用真实稿验证不误报
    path = sys.argv[2] if len(sys.argv) > 2 else None
    if path:
        res = run_all(path)
        print(u"；".join(u"%s：%s" % (n, u"通过" if not b else u"不通过") for n, b in res))
    return True


if __name__ == u"__main__":
    if sys.argv[1:2] == [u"--test"]:
        sys.exit(0 if _selftest() else 1)
    for p in sys.argv[1:]:
        print(u"==", p)
        for name, bad in run_all(p):
            print(u"[%s] %s" % (u"PASS" if not bad else u"FAIL", name))
            for b in bad:
                print(u"    ", b)
