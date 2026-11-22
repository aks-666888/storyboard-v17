# -*- coding: utf-8 -*-
# logic_chk.py —— 常识与场记逻辑硬检（v2.9.35）
# 只查三类机器能判死的「逻辑自打架」：
#   L1 门型一致：同一稿里不许同时出现两种门（玻璃门／卷闸门／木门…）
#   L2 时序锚点连续：镜段必须从 1 起、首尾相接、覆盖到最后一镜，不许重叠或回跳
#   L3 没点的烟不许被摁灭（「不点／没点」与「摁灭／点着」同稿冲突）
import re

DOOR = [u"玻璃门", u"卷闸门", u"卷帘门", u"木门", u"铁门", u"防盗门", u"推拉门", u"感应门", u"旋转门"]
_QUIT = [u"摁灭", u"掐灭", u"捻灭"]
_UNLIT = [u"不点", u"没点", u"没点着", u"没点火"]


def door_types(text):
    """返回稿子里出现过的门型列表（>1 即逻辑打架）。"""
    return [d for d in DOOR if d in text]


def check_door(text):
    ds = door_types(text)
    if len(ds) > 1:
        return [u"同一稿出现 %d 种门：%s（同场门型必须唯一）" % (len(ds), u"／".join(ds))]
    return []


def check_smoke(text):
    hit = [w for w in _UNLIT if w in text]
    quit_ = [w for w in _QUIT if w in text]
    if hit and quit_:
        return [u"烟没点（%s）却被摁灭（%s）：动作逻辑接不上" % (u"／".join(hit), u"／".join(quit_))]
    return []


_RANGE = re.compile(u"镜\\s*(\\d+)\\s*[–\\-—~至]\\s*镜?\\s*(\\d+)")


def check_timeline(text, shot_count):
    """从「片内时间锚点表」里取镜段，核连续覆盖。"""
    i = text.find(u"时间锚点")
    if i < 0:
        return []
    seg = text[i:]
    j = seg.find(u"\n## ")
    if j > 0:
        seg = seg[:j]
    rows = [ln for ln in seg.split(u"\n") if ln.strip().startswith(u"|")]
    rng = []
    for ln in rows:
        m = _RANGE.search(ln)
        if m:
            rng.append((int(m.group(1)), int(m.group(2))))
    if not rng:
        return [u"时间锚点表里没有「镜 A–B」镜段"]
    out = []
    if rng[0][0] != 1:
        out.append(u"镜段没从镜 1 起（现从镜 %d 起）" % rng[0][0])
    for k in range(1, len(rng)):
        if rng[k][0] != rng[k - 1][1] + 1:
            out.append(u"镜 %d 与镜 %d 之间有断口或重叠" % (rng[k - 1][1], rng[k][0]))
    if shot_count and rng[-1][1] != shot_count:
        out.append(u"镜段只到镜 %d，本片共 %d 镜" % (rng[-1][1], shot_count))
    return out


_BODY = [u"手", u"腕", u"指", u"脸", u"肩", u"头", u"腿", u"膝", u"背", u"腰", u"臂", u"身"]
_DIR_ACT = re.compile(u"画[左右][^，。；]{0,8}?([\u4e00-\u9fa5]{1,2})(伸|捏|抓|拽|递|摸|按|擦|拢|攥|扣|抽|推|拉|捡|扶|探)")


def check_dir_adverb(text):
    """画左／画右只标站位，不许拿来修饰动作；且动手的分句要点明哪只手（v2.9.35 L4）。"""
    bad = []
    body = []
    for ln in text.split(u"\n"):
        st = ln.strip()
        if not st or st.startswith((u"#", u"-", u"|", u">", u"**")):
            continue
        if st.startswith(u"段 ") or u"|" in st:
            continue
        body.append(st)
    for cl in re.split(u"[。；！？，]", u"\n".join(body)):
        m = _DIR_ACT.search(cl)
        if m and not any(w in cl for w in _BODY):
            bad.append(u"方位词当动作副词：%s（改写成「人在画左，他右手…」）" % cl.strip()[:22])
            continue
        if re.search(u"(没|不|未|别)[^。；！？，]{0,3}伸手", cl):
            continue
        if any(w in cl for w in (u"伸手", u"伸手去", u"抬起手")) and not re.search(u"左手|右手|两手|双手|那只手|一只手", cl):
            bad.append(u"只手没点名：%s（写清左手还是右手）" % cl.strip()[:22])
    return bad


def run_all(text, shot_count=0):
    return [(u"L1 门型一致", check_door(text)),
            (u"L2 时序锚点连续覆盖", check_timeline(text, shot_count)),
            (u"L3 没点的烟不许摁灭", check_smoke(text)),
            (u"L4 方位词不修饰动作、手要点明哪只", check_dir_adverb(text))
            ]



def _selftest():
    cases = [
        (u"门型打架", check_door(u"他推开门进店，玻璃门在画左；出门时拉卷闸门。"), True),
        (u"时序断口", check_timeline(u"\n## 片内时间锚点表\n| 镜 1–3 | 当夜 | 店内 |\n| 镜 5–6 | 次夜 | 店内 |\n", 6), True),
        (u"烟没点却摁灭", check_smoke(u"他叼着烟没点。后来他把烟在桶沿上摁灭。"), True),
        (u"方位词当动作副词", check_dir_adverb(u"他站在柜台外画左伸手探进帘缝。"), True),
        (u"手没点名", check_dir_adverb(u"他伸手把抽屉拉开。"), True),
        (u"干净稿", check_dir_adverb(u"他站在柜台外画左，右手把抽屉拉开。"), False),
        (u"否定式放过", check_dir_adverb(u"她两只手扶着柜台，没伸手去碰旧钟。"), False),
        (u"门型统一", check_door(u"玻璃门在画左，门边放着伞架。"), False),
    ]
    ok = 0
    for name, bad, want in cases:
        got = bool(bad)
        res = u"PASS" if got == want else u"FAIL"
        ok += (got == want)
        print(u"[%s] %s" % (res, name))
    print(u"结论：%d/%d" % (ok, len(cases)))
    return ok == len(cases)

if __name__ == u"__main__":
    import io
    import sys
    if sys.argv[1:2] == [u"--test"]:
        sys.exit(0 if _selftest() else 1)
    for p in sys.argv[1:]:
        t = io.open(p, encoding=u"utf-8").read()
        for name, bad in run_all(t):
            print(u"%s：%s" % (name, (u"；".join(bad) if bad else u"通过")))
