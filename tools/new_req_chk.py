# -*- coding: utf-8 -*-
"""新要求硬检（唯一规则源）。

来源：用户 2026-11-14《爆款短片剧本创作技能》里的六条禁止事项、
九字段分镜、术语库、爆款自检六条、类型识别与风格适配；
与 SKILL.md 〇·A 的冲突裁定一一对应。

用法：
    python new_req_chk.py <稿子路径> [--stage m1|m2] [--m1 底本路径]
    python new_req_chk.py --test

三处接入：m1_gate / m2_gate 全量调用；sb_core.scan_text 只调文本类
（N1/N2/N4/N5/N6），结构类（N3/N7/N8/N9）由两道门禁查，避免短文本误伤。
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame_parse
import term_bank  # noqa: E402

# ---------------- 词表 ----------------

AI_CONNECT = ["首先", "其次", "此外", "总而言之", "综上所述", "再者", "总之", "由此可见", "一方面", "另一方面"]
HOLLOW = ["人生就是这样", "爱需要勇气", "生活总会好起来", "时间会给出答案", "愿我们都被温柔以待",
          "一切都会好起来的", "这就是生活", "真爱无关", "岁月静好", "且行且珍惜"]
HOLLOW_PAT = [r"人生就是", r"时间会(?:证明|给出|告诉)", r"总会(?:好|过去|来)", r"其实我们(?:都|每个人)",
              r"说到底", r"归根结底"]
STALL = ["平局", "无变化", "无信息差", "待补", "未交代", "待填"]
META_HINT = ("禁", "不许", "要求", "判据", "术语", "自检", "硬律", "口径", "裁定", "条款", "映射", "规格")


# ---------------- 文本切分 ----------------

def _cut_requirements(text):
    """去掉要求节、附表、章节标题、表格行、元指令行，只留叙事与台词。"""
    t = re.sub(r"## ⑥.*?(?=## ⑦|\Z)", "", text, flags=re.S)
    t = re.sub(r"## (?:③\s*)?附表.*", "", t, flags=re.S)
    t = re.sub(r"## ⑧.*", "", t, flags=re.S)
    out = []
    for line in t.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">"):
            continue
        if any(w in s for w in META_HINT):
            continue
        if s.startswith("【") and s.endswith("】"):
            continue  # 技术行不参与文笔类检查
        out.append(s)
    return "\n".join(out)


def _shots(text):
    """切出分镜正文的 (镜号, 秒数, 技术行, 散文正文)。

    新写法把画面和台词写在同一段里，甚至同一行；旧过滤式「行首带七项括号」会把
    整行（连同前面的画面描述）一起丢掉，导致 N4/N5/N6/N10 全空跑。这里只抠掉
    台词那一截，画面文字必须留下。
    """
    body = re.split(r"## (?:③\s*)?附表", text)[0]
    blocks = re.findall(
        r"\*\*镜(\d+)（([\d.]+)秒）\*\*\s*\n(.*?)(?=\n\*\*镜\d+|\Z)", body, re.S)
    out = []
    for no, sec, blk in blocks:
        lines = [l.strip() for l in blk.strip().splitlines() if l.strip()]
        tag = lines[0] if lines and lines[0].startswith("【") else ""
        kept = []
        for l in lines:
            if l.startswith("【"):
                continue
            # 「角色（七项）：「……」」可能接在画面句后面，也可能独占一行
            l = re.sub(r"[^\s，。！？；]*（[男女]·[^）]*）\s*[：:]\s*[「“\"'][^」”\"']*[」”\"']",
                       u"", l)
            if re.match(r"^[^\s]{0,10}（[男女]·[^）]*）\s*[：:]", l):
                l = u""
            if l.strip():
                kept.append(l.strip())
        prose = " ".join(kept)
        out.append((int(no), sec, tag, prose))
    return out


# ---------------- 各项检查 ----------------

def check_n1(text):
    """N1 AI 味连接词（只在叙事与台词里查）。"""
    body = _cut_requirements(text)
    return [w for w in AI_CONNECT if w in body]


def check_n2(text):
    """N2 空洞升华与正确废话。"""
    body = _cut_requirements(text)
    got = [w for w in HOLLOW if w in body]
    for p in HOLLOW_PAT:
        m = re.search(p, body)
        if m:
            got.append(m.group(0))
    return list(dict.fromkeys(got))


def check_n3(text):
    """N3 流水账：②d 段落动作表须 ≥4 行、每行有对抗/变化/信息差，无停滞判定。"""
    m = re.search(r"## ②d(.*?)(?=## ③|\Z)", text, re.S)
    if not m:
        return ["缺 ②d 段落动作表"]
    rows = [r for r in m.group(1).splitlines() if r.strip().startswith("|")]
    data = [r for r in rows if not re.match(r"^\|\s*[-:| ]+\|?$", r.strip())]
    data = [r for r in data if "段落" not in r or "谁" not in r][:20]
    if len(data) < 4:
        return ["②d 只有 %d 行（须 ≥4）" % len(data)]
    bad = [r.strip()[:40] for r in data if any(w in r for w in STALL)]
    return bad


def check_n4_n5_n6_n7(text):
    """N4 相邻取景重复 / N5 光影无变化 / N6 动作重复停滞 / N7 禁【】标签（散文写法）。"""
    shots = _shots(text)
    n4, n5, n6, n7 = [], [], [], []
    if not shots:
        # 结构防线：有分镜内容却解析不出镜号行（如「镜 1　8 秒。…」），说明格式不合规，
        # 不许静默放过——否则 N 系列与 M2 交付门等于空跑。
        if re.search(r"^\s*镜\s*\d", text, re.M) or u"秒。" in text or u"秒．" in text:
            n7.append(u"镜号行格式不合规：必须单独一行写 **镜N（X秒）**，下面接一段散文")
        return n4, n5, n6, n7
    frames, lights, actions = [], [], []
    for no, _sec, tag, prose in shots:
        if tag:
            n7.append("镜%d 出现【】技术标签（分镜须一镜一段散文）" % no)
        fr = frame_parse.frame_code(prose)
        li = frame_parse.light_set(prose)
        frames.append(fr)
        lights.append(li if li else None)
        clean = re.sub(r"[，。！？、；：\s]", "", prose)
        actions.append(clean[:12])
    for i in range(1, len(shots)):
        a, b = shots[i - 1][0], shots[i][0]
        pa = re.sub(r"[\s，。！？、；：]", "", shots[i - 1][3])
        pb = re.sub(r"[\s，。！？、；：]", "", shots[i][3])
        same = bool(pa and pa == pb)
        if same:
            n4.append("镜%d→镜%d 画面句一字不差，取景没换" % (a, b))
            n5.append("镜%d→镜%d 画面句一字不差，光影没换" % (a, b))
        if not same and frames[i] and frames[i] == frames[i - 1]:
            n4.append("镜%d→镜%d 取景同：%s／%s" % (a, b, frames[i][0] or "-", frames[i][1] or "-"))
        if not same and lights[i] and lights[i] == lights[i - 1]:
            n5.append("镜%d→镜%d 光影同 %s" % (a, b, "/".join(sorted(lights[i]))[:20]))
        if actions[i] and actions[i] == actions[i - 1]:
            n6.append("镜%d→镜%d 开头动作重复「%s」" % (a, b, actions[i]))
    nonempty = [x for x in lights if x]
    if len(nonempty) >= 3 and all(x == nonempty[0] for x in nonempty):
        n5.append("全片所有镜同一套光影")
    return n4, n5, n6, n7


def check_n8(text):
    """N8 M1「⑧ 爆款自检六条」表必须在、六条都落地。"""
    m = re.search(r"## ⑧(.*?)(?=\Z)", text, re.S)
    if not m:
        return ["缺 ⑧ 爆款自检六条"]
    seg = m.group(1)
    rows = [r for r in seg.splitlines() if r.strip().startswith("|")]
    keys = ["黄金三秒", "反转密度", "情绪曲线", "爽点", "身份反差", "结尾钩子"]
    got = [k for k in keys if k in seg]
    miss = [k for k in keys if k not in got]
    bad = [r.strip()[:40] for r in rows if any(w in r for w in STALL)]
    return (["⑧ 缺检查项：" + "/".join(miss)] if miss else []) + bad


def check_n9(text):
    """N9 类型识别 + 编剧风格适配说明必须写明（不许虚构）。"""
    m = re.search(r"## ⓪(.*?)(?=## ①|\Z)", text, re.S)
    if not m:
        return ["缺 ⓪ 选题与爆款匹配说明"]
    seg = m.group(1)
    bad = []
    if "类型" not in seg:
        bad.append("⓪ 没写识别出的短片类型")
    if "风格" not in seg:
        bad.append("⓪ 没写本次适配的编剧风格（或「按该类型通用叙事手法」）")
    for w in ["某片", "某某编剧", "虚构一部", "编一个导演"]:
        if w in seg:
            bad.append("⓪ 出现占位/虚构说法「%s」" % w)
    return bad


# 词库（term_bank）与 SKILL §8.10 把「镜头慢慢往前压／镜头跟着人走」列为可直接写进句子的
# 中文画面说法，故单个「镜头」不算术语外露；只拦标签式搭配，避免规矩自己打自己。
JARGON_WORDS = [u"特写", u"近景", u"中景", u"全景", u"远景", u"空镜", u"机位", u"运镜",
                u"画外音", u"旁白", u"景别", u"构图", u"光影",
                u"镜头语言", u"长镜头", u"镜头感", u"换镜头", u"镜头切换"]


LABEL_HINTS = [u'取景', u'运镜', u'构图', u'光影', u'景别', u'人物动作', u'台词', u'音效', u'时长', u'分镜编号']


def check_n10(text):
    """N10（分镜层，v2.9.33）：不写【】字段行、不写「取景：」这类小标题；
    专业术语（中英对照）写进句子是正选，不判违规。

    词库教的中文字面说法（镜头慢慢往前压…）是允许的：JARGON_WORDS 只收标签式搭配，
    单个「镜头」不判违规，规矩不打自己。
    """
    bad = []
    for no, _sec, tag, prose in _shots(text):
        if u'【' in prose or u'】' in prose:
            bad.append(u'镜%d 正文出现【】字段标签' % no)
            continue
        for lb in LABEL_HINTS:
            if re.search(lb + u'\\s*[：:]', prose):
                bad.append(u'镜%d 正文出现「%s：」小标题' % (no, lb))
                break
        # v2.9.33：专业术语（含中英对照）写进句子是正选，不再拦
    return bad[:8]


def check_shot_terms(text):
    """N11（分镜层，v2.9.36）：按用户规范，每镜取景／运镜／构图／光影四项
    都要用中英对照专业术语写进句子，缺一类即不合格；术语不许单独成行，
    必须落在有画面内容的句子里。

    只认术语库里「英文原词＋中文释义」的完整条目，模糊人话不算达标。
    """
    bad = []
    for no, _sec, _tag, prose in _shots(text):
        hit = term_bank.hit_all(prose)
        miss = [c for c in term_bank.CATS if not hit[c]]
        if miss:
            bad.append(u"镜%s 没写%s的中英对照术语" % (no, u"／".join(miss)))
            continue
        words = [w for c in term_bank.CATS for w in hit[c]]
        for raw in prose.splitlines():
            line = raw.strip()
            if not any(w in line for w in words):
                continue
            rest = re.sub(u"[（(][^）)]*[A-Za-z][^）)]*[）)]", u"", line)
            if len(re.findall(u"[\u4e00-\u9fa5]", rest)) < 6:
                bad.append(u"镜%s 术语单独成行，没落进画面句子" % no)
                break
    return bad[:8]


M1_BODY_PAT = re.compile(r"##\s*③[^\n]*\n(.*?)(?=\n##\s|\Z)", re.S)


def _m1_body(text):
    """只取 ③ 故事剧本那一节的正文（剧本层判术语用）。"""
    m = M1_BODY_PAT.search(text)
    return m.group(1) if m else ""


def check_n10_m1(text):
    """N10（剧本层）：正文不写英文、不写景别／机位／后期术语。"""
    body = _m1_body(text)
    if not body.strip():
        return [u"缺 ③ 故事剧本正文，无法判术语外露"]
    bad = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s or s.startswith(("|", "#", ">", "-")):
            continue
        s = re.sub(u"^段\\s*\\d+[　\\s]*", u"", s)
        if re.match(u"^场\\s*\\d+", s) or u"待填" in s:
            continue
        m = re.search(u"[A-Za-z]{2,}", s)
        if m:
            bad.append(u"剧本正文出现英文「%s」" % m.group(0)[:12])
        for w in JARGON_WORDS:
            if w in s:
                bad.append(u"剧本正文出现术语「%s」" % w)
    return bad[:8]


# ---------------- 统一入口 ----------------

def run_all(text, stage="m1", m1_text=None):
    """返回 [(编号, 名称, 是否通过, 说明)]。"""
    out = []

    def add(code, name, bad):
        out.append((code, name, len(bad) == 0, "；".join(bad) if bad else "0 处"))

    add("N1", "禁 AI 味连接词", check_n1(text))
    add("N2", "禁空洞升华与正确废话", check_n2(text))
    if stage == "m1":
        add("N3", "禁流水账（②d 每行有对抗/变化/信息差）", check_n3(text))
        add("N8", "⑧ 爆款自检六条齐备", check_n8(text))
        add("N9", "类型识别与编剧风格适配说明", check_n9(text))
        add("N10", "剧本正文不外露术语（无英文、无景别机位词）", check_n10_m1(text))
    else:
        n4, n5, n6, n7 = check_n4_n5_n6_n7(text)
        add("N4", "相邻分镜取景不重复", n4)
        add("N5", "分镜光影有变化", n5)
        add("N6", "人物动作不重复不停滞", n6)
        add("N7", "分镜一律散文，禁【】技术标签", n7)
        add("N10", "正文不写成字段标签行（术语写进句子）", check_n10(text))
        add("N11", "每镜四项中英对照术语写进句子", check_shot_terms(text))
        if m1_text:
            add("N8", "底本 ⑧ 爆款自检六条齐备", check_n8(m1_text))
            add("N9", "底本类型识别与风格适配", check_n9(m1_text))
            add("N10", "底本剧本正文不外露术语", check_n10_m1(m1_text))
    return out


def as_issues(text, stage="storyboard"):
    """给主引擎 scan_text 用：只接文本类，返回 (行号, 类别, 命中, 片段) 四元组。"""
    issues = []
    for code, name, ok, detail in run_all(text, "m2" if stage == "storyboard" else "m1"):
        if code in ("N3", "N7", "N8", "N9"):
            continue  # 结构类交给门禁，避免短文本误伤；N11 术语必填须主引擎同源硬拦
        if code == "N10" and stage != "storyboard":
            continue  # 剧本层术语检查要看整篇 ③ 节，片段扫描交给 m1_gate
        if not ok:
            issues.append((0, name, detail, code))
    return issues


# ---------------- 自测 ----------------

def _test():
    good_m1 = """## ⓪ 选题与爆款匹配说明
本次识别为都市情感类型，依据题材与情绪基调判定。适配的编剧风格按该类型通用叙事手法，不虚构人名。
## ②d 段落动作表
| 段 | 谁+动词+对象 | 对抗与谁赢 | 不可逆变化 | 信息差 |
| 一 | 她递过纸条 | 她赢 | 纸条到了对方手上 | 对方不知内里 |
| 二 | 狗挣脱跑开 | 狗赢 | 绳断了 | 她不知项圈留枝上 |
| 三 | 她掰开扣环 | 她赢 | 照片露出来 | 观众先不知照片 |
| 四 | 她敲了三下门 | 她赢 | 照片塞回门缝 | 门里人不知她来过 |
## ③ 故事剧本
他抬手敲了三下门，门里应了一声。
## ⑧ 爆款自检六条
| 检查 | 落地 |
| 黄金三秒 | 开场三秒门被敲响 |
| 反转密度 | 两处：绳断、照片 |
| 情绪曲线 | 四阶段齐 |
| 爽点/虐点 | 守护被看见 |
| 身份反差 | 表面敷衍实际接住 |
| 结尾钩子 | 门缝里的照片 |
"""
    bad_m1 = good_m1.replace("他抬手敲了三下门，门里应了一声。",
                             "首先他抬手敲了三下门，其次门里应了一声。总而言之，人生就是这样。")
    good_m2 = (u"## ③ 分镜脚本\n"
               u"**镜1（6.0秒）**\n"
               u"楼道里那盏灯只亮半边，只框住他一只手和半扇门，离门两步，从门左前方平着看，画面往门上微微推近。\n"
               u"冷白日光从门缝里漏出来，落在门板上。他抬手敲了三下门，指节在木门上顿了顿（Medium Close-Up 中近景 · Dolly In 物理推镜 · Frame within Frame 框中框 · Key Light 主光）。\n"
               u"小林（女·26·清亮·平·中·随意·楼道声）：\u201c我上来了。\u201d\n"
               u"**镜2（6.0秒）**\n"
               u"门从里侧拉开一道缝，从下往上看，门板的竖边把画面分成两半。\n"
               u"屋里那盏煤油灯的黄光铺到台阶上。门把转动，门开了一道缝，暖光落到台阶上（Low Angle 低仰视角 · Truck Left 左横移 · Split Frame 分割画面构图 · Practical Light 场景固有光源）。\n"
               u"小林（女·26·清亮·平·中·随意·楼道声）：\u201c我进来了。\u201d\n"
               u"## 附表\n| 镜 | 秒 |\n")
    bad_m2 = (u"## ③ 分镜脚本\n"
               u"**镜1（6.0秒）**\n"
               u"楼道里那盏灯只亮半边，只框住他一只手和半扇门，离门两步，从门左前方平着看。\n"
               u"冷白日光从门缝里漏出来，落在门板上。他抬手敲了三下门，指节在木门上顿了顿。\n"
               u"**镜2（6.0秒）**\n"
               u"楼道里那盏灯只亮半边，只框住他一只手和半扇门，离门两步，从门左前方平着看。\n"
               u"冷白日光从门缝里漏出来，落在门板上。他抬手敲了三下门，指节在木门上顿了顿。此外，愿我们都被温柔以待。\n"
               u"## 附表\n| 镜 | 秒 |\n")
    bad_m1_eng = good_m1.replace(u"他抬手敲了三下门，门里应了一声。",
                                  u"他抬手敲了三下门，门里应了一声，这里给一个近景。")
    bad_tag = good_m2.replace(u"楼道里那盏灯只亮半边，", u"【中景·平视·手持跟拍·中心构图·冷白荧光】\n楼道里那盏灯只亮半边，")
    bad_eng = good_m2.replace(u"楼道里那盏灯只亮半边，", u"取景：中近景（Close-Up），楼道里那盏灯只亮半边，")
    cases = [
        ("好 M1 全过", all(x[2] for x in run_all(good_m1, "m1"))),
        ("坏 M1 被 N1/N2 拦", any(x[0] == "N1" and not x[2] for x in run_all(bad_m1, "m1"))
         and any(x[0] == "N2" and not x[2] for x in run_all(bad_m1, "m1"))),
        ("好 M2 全过（纯中文散文）", all(x[2] for x in run_all(good_m2, "m2"))),
        ("坏 M2 被 N4/N5/N6/N1/N2 拦",
         {x[0] for x in run_all(bad_m2, "m2") if not x[2]} >= {"N1", "N2", "N4", "N5", "N6"}),
        ("正文写成字段标签被 N10 拦", any(x[0] == "N10" and not x[2] for x in run_all(bad_eng, "m2"))),
        ("剧本正文写景别词被 N10 拦", any(x[0] == "N10" and not x[2] for x in run_all(bad_m1_eng, "m1"))),
        ("分镜出现【】技术标签被 N7 拦", any(x[0] == "N7" and not x[2] for x in run_all(bad_tag, "m2"))),
        ("术语库中英对照、逐条收进技能且可命中", all(len(term_bank.TERMS[c]) >= 10 for c in term_bank.CATS)
         and len(term_bank.english_terms()) == len(term_bank.all_terms())
         and len(term_bank.chinese_terms()) == len(term_bank.all_terms())
         and all(term_bank.TERMS[c][0] in io.open(os.path.join(
             os.path.dirname(os.path.abspath(__file__)), "..", "storyboard-v17", "SKILL.md"),
             encoding="utf-8").read() for c in term_bank.CATS)
         and bool(term_bank.hit("取景", "Close-Up 近景"))),
        ("专业术语写进句子不被 N10 拦、「取景：」标签被 N10 拦",
         all(x[2] for x in run_all(
             u"## ③ 分镜脚本\n**镜1（6秒）**\nMedium Close-Up 中近景，Dolly In 物理推镜，他推开门站着。\n## 附表\n", "m2") if x[0] == "N10")
         and any(x[0] == "N10" and not x[2] for x in run_all(
             u"## ③ 分镜脚本\n**镜1（6秒）**\n取景：中近景，他推开门站着。\n## 附表\n", "m2"))),
    ]
    for name, ok in cases:
        print(("PASS " if ok else "FAIL ") + name)
    print("结论：%d/%d 通过" % (sum(1 for _n, o in cases if o), len(cases)))
    return 0 if all(o for _n, o in cases) else 1


def main():
    if "--test" in sys.argv:
        return _test()
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    if not path:
        print("用法：new_req_chk.py <稿件> [m1|m2] [--m1 底本] 或 --test")
        return 2
    stage = "m1"
    if "--stage" in sys.argv:
        _si = sys.argv.index("--stage")
        if _si + 1 < len(sys.argv):
            stage = sys.argv[_si + 1]
    elif len(sys.argv) > 2 and sys.argv[2] in ("m1", "m2"):
        stage = sys.argv[2]
    text = io.open(path, encoding="utf-8").read()
    if "--stage" not in sys.argv and not (len(sys.argv) > 2 and sys.argv[2] in ("m1", "m2")):
        stage = "m2" if ("**镜" in text or "## ③ 分镜脚本" in text) else "m1"
    m1 = None
    if "--m1" in sys.argv:
        i = sys.argv.index("--m1")
        if i + 1 < len(sys.argv):
            m1 = io.open(sys.argv[i + 1], encoding="utf-8").read()
    bad = 0
    for code, name, ok, detail in run_all(text, stage, m1):
        print(("[%s] %s %s  （%s）" % ("PASS" if ok else "FAIL", code, name, detail)))
        bad += 0 if ok else 1
    print("结论：%d 项不合格" % bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
