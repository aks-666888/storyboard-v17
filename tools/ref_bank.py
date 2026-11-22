# -*- coding: utf-8 -*-
"""ref_bank.py —— 每个类别绑一位具名标杆，并把手法拆成机器能判的动作（v2.9.41）

上一版只给关键词，几条判不了的就说「靠人看」。这一版把那几条改成规则：
  机器判不了，不是因为它笨，是因为判据没写清。写成「谁在说、说的是不是解释动机、
  同一句有没有重复变体、动词有没有落到那个物件上、镜头术语有没有出现」，就能判。

两类判据：
  m1 —— 剧本阶段判（台词与叙事）
  m2 —— 分镜阶段判（镜头术语与景别）
标杆只拆手法，不抄句子、不抄情节。
"""
import io
import re
import sys

BANK = {
    u"催泪": (u"编导李让（《告别》式）", [
        (u"题眼物件中途埋、末尾兑现", "m1", u"obj"),
        (u"结尾不解释，只留一个没做完的动作", "m1", u"open_end"),
        (u"台词留半句，不把话说满", "m1", u"half_line"),
        (u"第一人称旁白开口就交代关系", "m1", u"first_person"),
        (u"题眼物件给近景或特写，收在手上", "m2", u"cu_obj"),
    ]),
    u"喜剧": (u"周星驰", [
        (u"误会或错认三连，第三次才收", "m1", u"triple"),
        (u"台词重复变奏：同一句说三遍，第三遍改一个字", "m1", u"repeat"),
        (u"夸张动作落到具体物件上，不写抽象情绪", "m1", u"obj_verb"),
        (u"反应特写：别人一句话，镜头钉在被打脸的那张脸上", "m2", u"cu_face"),
    ]),
    u"视觉叙事": (u"张艺谋", [
        (u"人物钉在画面正中或正中轴线上", "m2", u"center"),
        (u"俯拍／顶拍压人，或仰拍抬人", "m2", u"high_low"),
        (u"道具成阵列（一排、一墙、一院）", "m1", u"array"),
        (u"大色块：一镜里主色不超过两种", "m2", u"color_block"),
    ]),
    u"冷峻写实": (u"贾樟柯", [
        (u"县城／街边实景，招牌和杂物都在画面里", "m1", u"street"),
        (u"人物不解释自己：台词里没有解释动机的句子", "m1", u"no_explain"),
        (u"长镜头跟着人走，不切碎", "m2", u"long_take"),
    ]),
    u"悬疑": (u"希区柯克", [
        (u"信息差：观众知道危险，人物不知道", "m1", u"info_gap"),
        (u"威胁物先给观众看，再让人物走近", "m1", u"threat_first"),
        (u"倒计时压着走，时间写在画面里", "m1", u"countdown"),
    ]),
    u"热血": (u"成龙／吴京式动作片", [
        (u"目标先喊出来，再付出代价", "m1", u"goal"),
        (u"挨打之后站起来，动作落在地上", "m1", u"getup"),
        (u"环境当武器：桌椅、梯子、水管都用上", "m1", u"env_weapon"),
    ]),
    u"让人暖": (u"是枝裕和", [
        (u"一家人围桌吃饭／一起做一件事", "m1", u"together"),
        (u"不写大事件，只写日常重复的小动作", "m1", u"daily_repeat"),
        (u"结尾停在原地，不升华", "m1", u"stay"),
    ]),
}

TOUCH = [u"照片", u"纸", u"包", u"钟", u"表", u"信", u"条", u"硬币", u"伞", u"杯", u"盒", u"牌"]
EXPLAIN = [u"因为我", u"其实我", u"我是为了", u"我不是", u"我就是想", u"你听我解释", u"说实话"]
M2_TERMS = {
    u"cu_face": [u"特写", u"近景", u"Close-Up", u"Close Up"],
    u"cu_obj": [u"特写", u"近景", u"Close-Up", u"Close Up"],
    u"center": [u"居中", u"对称", u"正对", u"Centered", u"Symmetrical", u"Frontal"],
    u"high_low": [u"俯拍", u"仰拍", u"顶拍", u"高机位", u"低机位", u"High Angle", u"Low Angle", u"Overhead"],
    u"long_take": [u"长镜头", u"一镜到底", u"跟着", u"Long Take", u"Steadicam"],
    u"color_block": [u"主色", u"色块", u"单色"],
}


def _reg(t):
    for ln in t.split(u"\n"):
        st = ln.strip()
        if st.startswith(u"- 参照"):
            m = re.search(u"参照[：:]\\s*([^\\n（(]+)", st)
            name = m.group(1).strip() if m else u""
            cat = next((k for k in BANK if k in st), None)
            return name, cat
    return u"", None


def _body(t):
    on, out = False, []
    for ln in t.split(u"\n"):
        st = ln.strip()
        if st.startswith(u"## ③"):
            on = True
            continue
        if on and st.startswith(u"## "):
            break
        if on and st and not re.match(r"^场[ \u3000]*\d+", st):
            out.append(st)
    return out


def _narr(paras):
    return [p for p in paras if not re.match(r"^[\u4e00-\u9fa5]{1,4}（[^）]{4,}）：", p)]


def _dialogue(paras):
    out = []
    for p in paras:
        if re.match(r"^[\u4e00-\u9fa5]{1,4}（[^）]{4,}）：", p):
            out.append(p)
        elif p.count(u"「") >= 2 or p.count(u"“") >= 2 or p.count(u"\"") >= 2:
            out.append(p)
    return out


def _rule(key, paras):
    body = u"".join(paras)
    dia = u"".join(_dialogue(paras))
    narr = _narr(paras)
    if key == u"obj":
        head = u"".join(narr[:max(1, len(narr) // 2)])
        first = next((x for x in TOUCH if x in head), None)
        return bool(first and first in narr[-1])
    if key == u"open_end":
        return any(w in narr[-1] for w in [u"还没", u"没来得及", u"停", u"又", u"回", u"站着", u"看着", u"看了一眼", u"低头"])
    if key == u"half_line":
        return bool(re.search(u"……|\\.\\.\\.", dia)) or any(w in dia for w in [u"算了", u"吧"])
    if key == u"first_person":
        head = u"".join(paras[:4])
        return (u"我" in dia or u"我" in head) and any(
            w in body for w in [u"爸", u"妈", u"弟", u"哥", u"姐", u"妹", u"儿子", u"女儿", u"叔", u"姨"])
    if key == u"triple":
        return sum(body.count(w) for w in [u"以为", u"认错", u"错了", u"误会"]) >= 3
    if key == u"repeat":
        lines = _dialogue(paras)
        for ln in lines:
            txt = re.sub(u"^[^：]*：", u"", ln).strip(u"“”。！？")
            if len(txt) >= 4 and sum(1 for x in lines if txt[:4] in x) >= 3:
                return True
        return False
    if key == u"obj_verb":
        return bool(re.search(u"(摔|翻|泼|踢|砸|推|拽|掀)[^。，]{0,6}(碗|桌|椅|桶|盘|杯|门)", body))
    if key == u"array":
        return bool(re.search(u"(一排|一墙|一整排|一院子|一片)[^。，]{0,6}(灯笼|纸|盒|瓶|罐|货|架|椅子)", body))
    if key == u"street":
        return sum(1 for w in [u"街", u"巷", u"招牌", u"店", u"摊"] if w in body) >= 2
    if key == u"no_explain":
        return not any(w in dia for w in EXPLAIN)
    if key == u"info_gap":
        return any(w in body for w in [u"不知道", u"没看见", u"还在", u"并不知道"])
    if key == u"threat_first":
        return bool(re.search(u"(刀|锁|门|影|手)[^。]{0,8}(他|她|走|伸|推)", body))
    if key == u"countdown":
        return any(w in body for w in [u"分钟", u"还剩", u"点", u"钟"])
    if key == u"goal":
        return any(w in dia for w in [u"要", u"必须", u"一定"]) and any(
            w in body for w in [u"摔", u"疼", u"血", u"湿", u"累", u"喘"])
    if key == u"getup":
        return bool(re.search(u"(摔|跌|倒)[^。]{0,10}(爬|站|撑|扶)", body))
    if key == u"env_weapon":
        return bool(re.search(u"(桌|椅|梯|管|绳|桶)[^。]{0,8}(砸|顶|挡|甩|抡|劈|架)", body))
    if key == u"together":
        return sum(1 for w in [u"饭", u"桌", u"一起", u"坐", u"帮", u"递", u"守", u"等"] if w in body) >= 2
    if key == u"daily_repeat":
        return any(w in body for w in [u"又", u"照旧", u"每天", u"还是"])
    if key == u"stay":
        return any(w in narr[-1] for w in [u"还", u"原", u"坐着", u"看着", u"没动", u"压在", u"按平"])
    return None


def _m2_rule(key, text):
    return any(t in text for t in M2_TERMS.get(key, []))


def run_all(path, stage=u"m1"):
    t = io.open(path, encoding="utf-8").read()
    name, cat = _reg(t)
    if not cat:
        return [(u"F0 登记参照标杆（- 参照：X（类别））",
                 [u"开题卡没登记参照：说不出照谁的手法，就只能空喊"])]
    bench, methods = BANK[cat]
    if bench.split(u"（")[0] not in name:
        return [(u"F0 参照与本类标杆对得上（%s）" % cat,
                 [u"登记「%s」，本类标杆是「%s」" % (name, bench)])]
    paras = _body(t)
    pending, bad, done = [], [], 0
    for mname, mstage, key in methods:
        if mstage != stage:
            pending.append(mname)
            continue
        if _rule(key, paras):
            done += 1
        else:
            bad.append(u"没做到「%s」" % mname)
    judged = done + len(bad)
    need = (judged + 1) // 2
    miss = [] if done >= need else [u"只做到 %d 条，本阶段至少 %d 条：%s" % (done, need, u"；".join(bad))]
    head = [(u"F1 参照标杆登记对得上（%s·%s）" % (cat, bench), []),
            (u"F2 标杆手法做到 %d/%d 条（%s阶段判，至少 %d 条）" % (done, judged, u"剧本" if stage == u"m1" else u"分镜", need), miss)]
    if pending:
        head.append((u"F3 留到%s阶段判的手法：%s" % (u"分镜" if stage == u"m1" else u"剧本", u"；".join(pending)), []))
    return head


def run_m2(script_path, sb_text):
    name, cat = _reg(io.open(script_path, encoding="utf-8").read())
    if not cat:
        return [(u"F0 分镜阶段沿用开题卡参照（未登记）", [u"开题卡没登记参照"])]
    bench, methods = BANK[cat]
    m2 = [(m, k) for m, s, k in methods if s == u"m2"]
    if not m2:
        return [(u"F2 本类没有分镜阶段要判的手法（%s）" % bench, [])]
    bad = [u"分镜里没看到「%s」" % m for m, k in m2 if not _m2_rule(k, sb_text)]
    return [(u"F2 分镜用上标杆的镜头手段（%s，共 %d 条）" % (bench, len(m2)), bad)]


def _selftest():
    ok = 0
    checks = [
        (u"题眼物件首尾同一件", _rule(u"obj", [u"他把那张照片推到柜台。", u"纸角被雨气泡软。", u"他把照片塞回胸袋。"]), True),
        (u"不解释自己", _rule(u"no_explain", [u"老周（男·55·含混）：\"我见过他。\""]), True),
        (u"解释动机被抓住", _rule(u"no_explain", [u"老周（男·55·含混）：\"我是为了找他。\""]), False),
        (u"台词三连变奏", _rule(u"repeat", [u"阿明（男·20·急）：\"再看一眼。\"",
                                       u"阿明（男·20·急）：\"再看一眼。\"",
                                       u"阿明（男·20·急）：\"再看一眼吧。\""]), True),
        (u"环境当武器", _rule(u"env_weapon", [u"他抡起椅子砸过去。"]), True),
        (u"误会三连", _rule(u"triple", [u"他以为认错。", u"又认错一次。", u"第三次误会。"]), True),
        (u"分镜特写术语", _m2_rule(u"cu_face", u"推近到他脸（Close-Up 特写）"), True),
    ]
    for nm, got, want in checks:
        ok += (got == want)
        print(u"[%s] %s" % (u"PASS" if got == want else u"FAIL", nm))
    print(u"结论：%d/%d" % (ok, len(checks)))
    return ok == len(checks)


if __name__ == u"__main__":
    if sys.argv[1:2] == [u"--test"]:
        sys.exit(0 if _selftest() else 1)
    for p in sys.argv[1:]:
        print(u"==", p)
        for nm, bad in run_all(p):
            print(u"[%s] %s" % (u"PASS" if not bad else u"FAIL", nm))
            for b in bad[:5]:
                print(u"    ", b)
