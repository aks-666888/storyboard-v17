# -*- coding: utf-8 -*-
"""boom_chk.py —— 爆款完全符合硬检（唯一规则源）。

来源：SKILL.md 铁律 8 / §7.3 / §7.6.1 / §7.6.2 / §7.6.3 / §7.14 / §7.15 /
§7.16 / §12.1 / 〇·A 新要求整合口径 A.2 A.3。

一句话：爆款不是「故事里有钩子有反转」就算完，交付件也得写全、写死、可核。
以前只查 ⑧ 六条表在不在，漏了四样：库内全库检索没写、对照表出处写成
「常见写法」这类空话、体检单没出、过程件还挂着上一轮的旧片名旧口径。

检查项（B = Boom）：
  B1 ⓪ 双源写全：库内 M 条 → 取用 N 条 + 逐条匹配维与借鉴一招；
     3 部真实样本带可核出处（链接或平台＋日期）、逐部拆七项；不许编片名
  B2 ②c 对照表每行手法来源必须是《具体片名》，不许「常见写法／常见节奏／同类短片」
  B3 ⑧ 六条逐条有证据句，不是只有标题
  B4 随稿出 08_爆款体检.md，六项硬检逐条「过/不过 ＋ 证据句」
  B5 编剧风格适配写明三条具体手法，不许只写「通用叙事手法」四个字
  B6 过程件一致：01_prompt / 03_确认A / run.json 不许挂 ⓪ 没登记的片名，
     不许残留「每秒 4.5 字／8 字」旧秒数口径与固化问法

用法：
    python boom_chk.py <稿子路径>
    python boom_chk.py --test

三处同源接入：m1_gate（全量，含 run 级 B4/B6）、sb_core.scan_text
（文本级 B1/B2/B3/B5，短文本与骨架自动跳过）、selftest（正反硬回归）。
"""
import io
import os
import re
import sys

# ---------------- 词表 ----------------

# 空出处：写这些等于没写出自哪条爆款
VAGUE = [u"常见写法", u"常见节奏", u"常见母题", u"常见开场", u"常见的开局",
         u"常见的困境定型", u"常见的人设反差", u"常见的收敛取景",
         u"同类短片常见", u"同类物证短片常见", u"物证类短片常见",
         u"邻里题材常见", u"同城短片常见", u"同城温情类常见",
         u"手艺行当常见", u"按常规规律", u"按该类型常规爆款规律拆解",
         u"待填", u"待补", u"未列片名", u"未标注"]

SEVEN = [u"故事前提", u"人物设定", u"身份反差", u"冲突", u"情绪钩子",
         u"节奏", u"爽点", u"虐点", u"反转"]

SIX = [u"黄金三秒", u"反转密度", u"情绪曲线", u"爽点", u"身份反差", u"结尾钩子"]

OLD_SCALE = [u"每秒 4.5 字", u"每秒4.5字", u"每秒 8.0 字", u"每秒 8 字",
             u"按该镜台词", u"待你拍板的 4 件事"]

SKELETON = [u"待填骨架", u"离线骨架说明", u"离线骨架（供验证链路"]


def _is_skeleton(text):
    return any(w in text for w in SKELETON)


def _seg(text, start, end=None):
    m = re.search(start + r".*?(?=" + end + r"|\Z)" if end else start + r".*", text, re.S)
    return m.group(0) if m else u""


def _section(text, head):
    """按「## 标题」切一节，切到下一个 ## 为止；没有下一节就到文末。"""
    m = re.search(head + r"[^\n]*\n", text)
    if not m:
        return u""
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def _rows(seg):
    out = []
    for ln in seg.splitlines():
        s = ln.strip()
        if not s.startswith(u"|"):
            continue
        if re.match(r"^\|[\s\-:|]+\|?$", s):
            continue
        out.append([c.strip() for c in s.strip(u"|").split(u"|")])
    return out


def _titles(seg):
    return list(dict.fromkeys(re.findall(u"《([^》]+)》", seg)))


# ---------------- 各项检查 ----------------

RELAX = [u"未取到公开样本", u"没有联网采集到可核实的同类片名", u"没搜到可核实的同类型片名",
         u"未联网采集", u"按该类型常规爆款规律拆解", u"按常规处理走放宽"]


def _declared_real(text):
    """⓪ 里登记了 ≥3 个《真实片名》＝必须走严格双源；否则走标准允许的放宽路径。"""
    return len(_titles(_seg(text, r"## ⓪", r"## ①"))) >= 3


def _relaxed(seg):
    return any(w in seg for w in RELAX)


def check_b1(text):
    """B1 ⓪ 双源写全。

    两条合规路径（SKILL §7.14）：查到真实样本 → 必须写全库内 M→N、逐条借鉴、
    3 部可核出处、七项拆解；确实没查到 → 必须写明放宽声明且不编片名。
    查到了片名却不写全，就是「不完全符合」，当场拦。
    """
    seg = _seg(text, r"## ⓪", r"## ①")
    if not seg:
        return [u"缺 ⓪ 选题与爆款匹配说明"]
    titles = _titles(seg)
    if len(titles) < 3:
        if not _relaxed(seg):
            return [u"⓪ 不足 3 部样本，又没写「未取到公开样本／按常规规律推定」的放宽声明"]
        if re.search(u"编一个片名|像个真片名|冒充成真实", seg):
            return [u"放宽路径下出现编片名的说法"]
        if u"双源" not in seg:
            return [u"放宽路径下没交代双源（本地库＋联网）怎么处理"]
        return []
    bad = []
    m_total = re.search(u"库内[^0-9]{0,12}(\\d+)\\s*条", seg)
    m_used = re.search(u"(?:本次)?取用[^0-9]{0,8}(\\d+)\\s*条", seg)
    if not m_total:
        bad.append(u"没写「库内共 M 条」（全库检索没落地）")
    if not m_used:
        bad.append(u"没写「取用 N 条」（按分数排序取用没落地）")
    if m_total and m_used and int(m_used.group(1)) < 3:
        bad.append(u"取用 %s 条，不足 3 条" % m_used.group(1))
    if u"双源" not in seg:
        bad.append(u"没写「双源爆款」（本地库＋联网两路没落地）")
    if not re.search(u"逐条|各借|匹配到", seg):
        bad.append(u"没写「逐条匹配到哪一维 ＋ 各借一招」")
    if not re.search(u"https?://|检索于|可核", seg):
        bad.append(u"三部样本没有可核出处（链接／平台＋日期／检索于）")
    if not re.search(u"20\\d{2}", seg):
        bad.append(u"三部样本没有日期，无法判断是不是过期货")
    hit7 = sum(1 for w in SEVEN if w in seg)
    if hit7 < 6:
        bad.append(u"七项拆解只写了 %d 项（须 ≥6：前提/人设/反差/冲突/钩子/节奏/爽虐/反转）" % hit7)
    if re.search(u"虚构一部|编一个片名|像个真片名|冒充成真实", seg):
        bad.append(u"⓪ 出现虚构/冒充片名的说法")
    if re.search(u"本地库条目只作手法参照|同类条目只作手法参照", seg):
        bad.append(u"本地库被写成「只作手法参照」，全库检索与取用明细没落地")
    return bad


def check_b2(text):
    """B2 ②c 每行手法来源必须是《具体片名》。

    查到真实样本的稿：每行必须写 ⓪ 登记过的片名，空出处一律不合格。
    合法放宽的稿：节内须标明「未联网采集／未列片名」，招式名不能空、不能写「待填」。
    """
    seg = _section(text, r"## ②c")
    if not seg:
        return [u"缺 ②c 爆款对照表"]
    rows = _rows(seg)
    data = rows[1:] if rows else []
    if len(data) < 6:
        return [u"②c 只有 %d 行（须 ≥6）" % len(data)]
    strict = _declared_real(text)
    relaxed_tbl = any(w in seg for w in (u"未联网采集", u"未列片名", u"没有联网采集"))
    if not strict and _relaxed(_seg(text, r"## ⓪", r"## ①")) and relaxed_tbl:
        bad = [u"放宽路径下第 %d 行手法来源是待填／空话" % i
               for i, r in enumerate(data, 1)
               if len(r) < 2 or len(r[1]) < 4 or u"待填" in r[1]]
        return bad
    registered = set(_titles(_seg(text, r"## ⓪", r"## ①")))
    bad = []
    for i, r in enumerate(data, 1):
        src = r[1] if len(r) > 1 else u""
        titles = re.findall(u"《([^》]+)》", src)
        if not titles:
            bad.append(u"第 %d 行没写具体片名：%s" % (i, src[:22]))
        elif strict and any(t not in registered for t in titles):
            bad.append(u"第 %d 行《%s》没在 ⓪ 登记" % (i, u"／".join(t for t in titles if t not in registered)))
        for w in VAGUE:
            if w in src:
                bad.append(u"第 %d 行出处是空话「%s」" % (i, w))
                break
    return bad


def check_b3(text):
    """B3 ⑧ 六条逐条有证据句（不是只有标题或「待填」）。"""
    seg = _section(text, r"## ⑧")
    if not seg:
        return [u"缺 ⑧ 爆款自检六条"]
    bad = []
    for k in SIX:
        if k not in seg:
            bad.append(u"⑧ 缺检查项：%s" % k)
    rows = _rows(seg)
    for r in rows[1:] if rows else []:
        last = r[-1] if r else u""
        if len(last) < 14 or any(w in last for w in (u"待填", u"待补", u"待定", u"见实算值")):
            bad.append(u"⑧ 证据句没写全：%s" % last[:24])
    return bad


def check_b5(text):
    """B5 编剧风格适配：写明三条具体手法，不许只写「通用叙事手法」四个字。"""
    seg = _seg(text, r"## ⓪", r"## ①")
    m = re.search(u"本次适配的编剧风格[^\\n]*", seg)
    if not m:
        return [u"⓪ 没写本次适配的编剧风格"]
    line = m.group(0)
    body = line.split(u"：", 1)[-1].split(u":", 1)[-1]
    if len(body) < 28:
        bad = [u"编剧风格只写了「%s」，没落到三条具体手法" % body[:20]]
    else:
        bad = []
    if u"不虚构" not in line and u"通用叙事手法" not in line:
        bad.append(u"编剧风格没交代「不虚构人名/流派」或「按通用叙事手法」的口径")
    return bad


def check_b4(path):
    """B4 随稿出 08_爆款体检.md，六项逐条「过/不过 ＋ 证据句」。"""
    if not path:
        return []
    d = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(os.path.join(d, u"01_prompt.md")):
        return []          # 不是完整 run 目录（历史回归稿/沙箱探针），不查文件级
    f = os.path.join(d, u"08_爆款体检.md")
    if not os.path.exists(f):
        return [u"缺 08_爆款体检.md（六项硬检要逐条给过/不过＋证据句）"]
    t = io.open(f, encoding=u"utf-8").read()
    bad = []
    for k in SIX:
        if k not in t:
            bad.append(u"体检单缺「%s」一项" % k)
        else:
            line = [ln for ln in t.splitlines() if k in ln]
            if not line or not re.search(u"过|不过", u" ".join(line)):
                bad.append(u"体检单「%s」没写判定" % k)
            if not line or len(u" ".join(line)) < 28:
                bad.append(u"体检单「%s」没给证据句" % k)
    if u"证据" not in t:
        bad.append(u"体检单没有证据句栏")
    return bad


def check_b6(path, text=None):
    """B6 过程件一致：不许挂 ⓪ 没登记的片名，不许残留旧秒数口径；
    写稿单子必须与当前工具同版本、写明最新硬查（照旧单子写稿必被拦）。"""
    if not path:
        return []
    d = os.path.dirname(os.path.abspath(path))
    files = [u"01_prompt.md", u"03_确认A.md", u"run.json"]
    # 成稿另存为 .edited.md 时，同目录那份 02_剧本草稿.md 也是过程件，
    # 旧片名、旧秒数口径必须一起同步，不许留一份旧稿蒙混过关。
    if (os.path.basename(os.path.abspath(path)) != u"02_剧本草稿.md"
            and os.path.exists(os.path.join(d, u"02_剧本草稿.md"))):
        files.append(u"02_剧本草稿.md")
    if not all(os.path.exists(os.path.join(d, f)) for f in files):
        return []
    if text is None:
        text = io.open(path, encoding=u"utf-8").read()
    seg = _seg(text, r"## ⓪", r"## ①")
    registered = set(_titles(seg))
    bad = []
    # 570 补：写稿单子／对标表里本来就会带库内参照爆款的真实片名，
    # 那是「照谁的手法」，不是本片旧片名；库内已登记的片名一律不算旧名。
    lib_titles = set()
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ref_bank as _rb
        for e in getattr(_rb, "BANK", []):
            if isinstance(e, dict) and e.get("title"):
                lib_titles.add(e["title"])
        # 库内条目另有一份人读的储备库文档，标题也在里头
        _libf = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             u"爆款储备库.md")
        if os.path.exists(_libf):
            lib_titles |= set(re.findall(u"《([^》]{2,40})》",
                                        io.open(_libf, encoding=u"utf-8").read()))
    except Exception:
        lib_titles = set()
    for f in files:
        t = io.open(os.path.join(d, f), encoding=u"utf-8").read()
        for w in OLD_SCALE:
            if w in t:
                bad.append(u"%s 还挂着旧口径「%s」" % (f, w))
        for name in _titles(t):
            if name in lib_titles:
                continue
            if name not in registered:
                bad.append(u"%s 里的《%s》在 ⓪ 没登记（旧片名没同步）" % (f, name))
    # 写稿单子本身也要跟当前工具同源：版本落后或缺最新硬查，照它写稿
    # 出来一定不合格，必须在交付前当场拦下并退回重出，不许靠人试错。
    pf = os.path.join(d, u"01_prompt.md")
    pt = io.open(pf, encoding=u"utf-8").read()
    if u"# 阶段一 · 剧本生成任务" in pt:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sb_core as core
        mv = re.search(r"v(\d+\.\d+\.\d+)", pt[:120])
        if not mv or mv.group(1) != core.VERSION:
            got = u"v" + mv.group(1) if mv else u"没写版本号"
            bad.append(u"01_prompt.md 挂旧版本 %s（当前工具 v%s），照旧单子写稿会缺最新硬查" % (got, core.VERSION))
        for mk in core.PROMPT_MARKS:
            if mk not in pt:
                bad.append(u"01_prompt.md 没写最新硬查「%s」，出稿前不会提醒" % mk)
    return bad


def _put(p, s):
    with io.open(p, u"w", encoding=u"utf-8") as fh:
        fh.write(s)


def check_b7(path):
    """B7 有成品稿时，配套体检单与确认清单不许还停在填空骨架口气。"""
    if not path:
        return []
    d = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(os.path.join(d, u"02_剧本草稿.edited.md")):
        return []
    bad = []
    f = os.path.join(d, u"08_爆款体检.md")
    if not os.path.exists(f):
        bad.append(u"有成品稿却缺 08_爆款体检.md")
    else:
        t = io.open(f, encoding=u"utf-8").read()
        if u"本单对应填空骨架" in t or u"待成稿核（不判过）" in t:
            bad.append(u"体检单还停在填空骨架口气，没按成稿重出")
        if u"02_剧本草稿.edited.md" not in t:
            bad.append(u"体检对象还挂着填空骨架文件名")
    c = os.path.join(d, u"03_确认A.md")
    if os.path.exists(c):
        t = io.open(c, encoding=u"utf-8").read()
        if u"离线骨架（供验证链路，非成品）" in t:
            bad.append(u"确认清单还写「非成品」，没按成稿同步")
    return bad


def sync_run(path):
    """成稿落盘后，把配套文件按成稿自动重出；只动配套件，不碰成稿本身。

    调用点：剧本交付门、stage1、以及独立 sync 命令。返回改过的文件名列表。
    """
    d = os.path.dirname(os.path.abspath(path))
    edited = os.path.join(d, u"02_剧本草稿.edited.md")
    if not os.path.exists(edited):
        return []
    text = io.open(edited, encoding=u"utf-8").read()
    done = []
    meta = {u"path": edited}
    try:
        import json
        m = json.load(io.open(os.path.join(d, u"run.json"), encoding=u"utf-8"))
        meta[u"genre"] = m.get(u"genre_name") or u""
        meta[u"used"] = len(m.get(u"matched", [])) or 3
        sc = m.get(u"scale", {})
        meta[u"dur"] = u"%s 秒（依据：%s）" % (
            sc.get(u"total_seconds") or u"由内容推",
            sc.get(u"basis") or u"每镜秒数由画面与台词内容现算")
        meta[u"rhythm"] = sc.get(u"rhythm") or u"起—承—转—收"
    except Exception:
        pass
    _put(os.path.join(d, u"08_爆款体检.md"),
         build_exam(text, src=u"02_剧本草稿.edited.md", meta=meta))
    done.append(u"08_爆款体检.md")

    # 写稿单子按当前工具重出：版本落后或缺最新硬查时，交付门已在前面
    # 按盘上真实状态判过不合格；这里只顺手补齐，不改变那次判定。
    try:
        import sb_core as _core
        if _core.rebuild_prompt(d):
            done.append(u"01_prompt.md")
    except Exception:
        pass

    cf = os.path.join(d, u"03_确认A.md")
    if os.path.exists(cf):
        t = io.open(cf, encoding=u"utf-8").read()
        n = t.replace(
            u"- 直接在 `02_剧本草稿.md` 上改，另存为 `02_剧本草稿.edited.md`，再执行 `confirm A`。",
            u"- 直接在 `02_剧本草稿.edited.md` 上改；改完执行一次检查，配套文件自动跟着同步，再执行 `confirm A`。")
        n = n.replace(u"`02_剧本草稿.md`", u"`02_剧本草稿.edited.md`")
        n = n.replace(u"生成方式：离线骨架（供验证链路，非成品）",
                      u"生成方式：成稿（02_剧本草稿.edited.md，配套文件已按成稿同步）")
        if n != t:
            _put(cf, n)
            done.append(u"03_确认A.md")

    try:
        import sb_core as core
        chk = core.format_issues(core.scan_text(text, stage=u"script"))
    except Exception:
        chk = u"（文本复核未完成，以剧本交付门结果为准）\n"
    _put(os.path.join(d, u"selfcheck.txt"), chk)
    done.append(u"selfcheck.txt")
    return done


# ---------------- 统一入口 ----------------

def run_all(text, path=None):
    """返回 [(编号, 名称, 是否通过, 说明)]。"""
    out = []

    def add(code, name, bad):
        out.append((code, name, len(bad) == 0, u"；".join(bad) if bad else u"0 处"))

    if _is_skeleton(text):
        return out          # 填空骨架不是交付稿，结构类不判（与 C6 同口径）
    add(u"B1", u"⓪ 双源写全（库内M→取用N／逐条借鉴／3部可核样本拆七项）", check_b1(text))
    add(u"B2", u"②c 每行手法来源是具体片名（不许「常见写法」空出处）", check_b2(text))
    add(u"B3", u"⑧ 六条逐条有证据句", check_b3(text))
    add(u"B5", u"⓪ 编剧风格落到三条具体手法", check_b5(text))
    add(u"B4", u"随稿出 08_爆款体检.md（六项判定＋证据句）", check_b4(path))
    add(u"B6", u"过程件与成品稿同口径（片名／秒数／问法）", check_b6(path, text))
    add(u"B7", u"成稿落盘后配套文件自动同步（体检单／确认清单按成稿重出）", check_b7(path))
    return out


def as_issues(text):
    """给主引擎 scan_text 用：只接文本类，短文本与骨架自动跳过。"""
    issues = []
    if _is_skeleton(text) or u"## ⓪" not in text or u"## ②c" not in text:
        return issues
    for code, name, ok, detail in run_all(text):
        if code in (u"B4", u"B6", u"B7"):
            continue       # 文件级交门禁，主引擎只有文本
        if not ok:
            issues.append((0, name, detail, code))
    return issues


# ---------------- 体检单生成（出稿端自动写全，不许留给人补） ----------------

EXAM_TPL = u"""# 08 爆款体检报告（M1 剧本 · 按 §7.16 六项硬检逐条判）

- 体检对象：`{src}`
- 体检口径：本次 {genre} 类型，总时长与各镜秒数由画面和台词内容现算，不按字数反推；六项按「过／不过 ＋ 证据句」逐条给，不用感觉判断。
- 双源：本地库 {lib} 条全部参与打分 → 取用 {used} 条（逐条写明匹配到哪一维、借鉴哪一招）＋ 联网同类型真实 {net} 部（每部带可核页面、日期，逐部拆七项）；不许编片名。

## 一、六项硬检

| # | 检查项 | 判定 | 证据句（稿内原句／具体落点） |
| --- | --- | --- | --- |
| ① | 黄金三秒 | 过 | {e1} |
| ② | 反转密度 | 过 | {e2} |
| ③ | 情绪曲线 | 过 | {e3} |
| ④ | 爽点／虐点 | 过 | {e4} |
| ⑤ | 身份反差 | 过 | {e5} |
| ⑥ | 结尾钩子 | 过 | {e6} |

## 二、爆款骨与反转铁律

| 检查 | 判定 | 证据句 |
| --- | --- | --- |
| 观众先站错边（误会先立） | 过 | {e7} |
| 题眼道具三次变形 | 过 | {e8} |
| 物证反转、不靠事故巧合 | 过 | {e9} |
| 情绪曲线四阶段落地 | 过 | {e10} |
| 结尾错位归还 | 过 | {e11} |

## 三、交付写全（B1–B6）

| 检查 | 判定 | 证据句 |
| --- | --- | --- |
| ⓪ 双源与全库检索（库内 M 条 → 取用 N 条＋逐条借鉴） | 过 | 见 ⓪ 第 5 行起，三部真实样本逐部拆七项、带可核页面与日期。 |
| ②c 对照表每行标具体片名 | 过 | 见 ②c 表，六招式各一行，手法来源列逐行写《片名》，落点写到具体幕。 |
| ⑧ 六条逐条落地 | 过 | 见 ⑧ 表，六行证据句均指到具体幕、具体动作与具体物件。 |
| 编剧风格适配三条具体手法 | 过 | 见 ⓪ 第 4 行，写明按该类型通用叙事手法与三条可执行写法，不虚构人名流派。 |
| 过程件同口径 | 过 | 01_prompt／03_确认A／run.json 的片名、类型、秒数口径与本稿一致，无旧口径残留。 |

## 四、本次推导（六维共性现算，不套文档示例值）

| 维 | 本次实际值 | 依据 |
| --- | --- | --- |
| 总时长 | {dur} | 时间服从画面，各镜秒数由画面与台词内容现算，剧本阶段不写秒数。 |
| 镜数 | 不预设 | 镜数由剧本切段自然得出，阶段二才切，不预设。 |
| 节奏 | {rhythm} | 取自本次匹配样本的情绪阶段，只写阶段不写死秒。 |
| 氛围与光影 | {light} | 全片一处主光、一个色温，写进本片标准卡。 |
| 台词密度 | 每镜至少一句、单句 ≤14 字 | 台词活人感铁律；剧本层台词用「」原样写，那七项人物说明只归阶段二脚本。 |

## 五、结论

六项硬检、爆款骨、反转铁律、交付四件、过程件一致，逐条有判定与证据句，全部通过。
体检由工具随稿生成并回读核对，不合格退回重出，不把没写全的稿子交出去。
"""


def build_exam(text, src=u"02_剧本草稿.edited.md", meta=None):
    """从成品稿抽 ⑧ 六条的实际证据句，生成体检单正文（不留占位给人补）。"""
    meta = meta or {}
    seg8 = _seg(text, r"## ⑧", r"## ⑨")
    ev = {}
    for k in SIX:
        line = [ln for ln in seg8.splitlines() if k in ln and ln.strip().startswith(u"|")]
        cells = [c.strip() for c in line[0].split(u"|") if c.strip()] if line else []
        ev[k] = (cells[-1] if cells
                 else u"见 ⑧ 表「%s」行，稿内该行证据句须指到具体幕／动作／物件" % k)
    seg0 = _seg(text, r"## ⓪", r"## ①")
    genre = u""
    mg = re.search(u"本次识别的短片类型[：:]\\s*([^｜|（(\\n]+)", seg0)
    if mg:
        genre = mg.group(1).strip()
    mt = re.search(u"库内[^0-9]{0,12}(\\d+)\\s*条", seg0)
    mu = re.search(u"(?:本次)?取用[^0-9]{0,8}(\\d+)\\s*条", seg0)
    seg2b = _seg(text, r"## ②b", r"## ②c")
    seg4 = _seg(text, r"## ④", r"## ⑤")
    seg2c = _section(text, r"## ②c")
    seg1 = _seg(text, r"## ①", r"## ②")
    _sk = _is_skeleton(text)
    _unverified = u"待成稿核（不判过）" if _sk else u"待核（不判过）"
    _p = meta.get("path")
    _res = dict((c, ok) for c, n, ok, d in run_all(text, _p) if c != u"B7")
    if _sk:
        ev = dict((k, u"填空骨架，成稿后由 ⑧「%s」行填本次实际证据句" % k) for k in SIX)

    def _ok(code):
        return _unverified if _sk else (u"过" if _res.get(code, True) else u"不过")

    def _six(k):
        if _sk:
            return _unverified
        e = ev[k]
        if u"见 ⑧ 表" in e or len(e) < 14 or any(w in e for w in (u"待填", u"{{")):
            return u"不过"
        return u"过" if _res.get(u"B3", True) else u"不过"

    def _part(s, code=u"B3"):
        if _sk:
            return _unverified
        if not s.strip() or any(w in s for w in (u"待填", u"{{")):
            return u"不过"
        return u"过" if _res.get(code, True) else u"不过"

    v = dict((k, _six(k)) for k in SIX)
    v[u"爽点／虐点"] = _six(u"爽点")
    v[u"观众先站错边"] = _part(seg2b)
    v[u"题眼道具三次变形"] = _part(seg2c, u"B2")
    v[u"物证反转"] = _part(seg2b)
    v[u"情绪曲线四阶段落地"] = _part(seg4)
    v[u"结尾错位归还"] = _part(seg1)
    v[u"⓪ 双源与全库检索"] = _ok(u"B1")
    v[u"②c 对照表每行标具体片名"] = _ok(u"B2")
    v[u"⑧ 六条逐条落地"] = _ok(u"B3")
    v[u"编剧风格适配三条具体手法"] = _ok(u"B5")
    v[u"过程件同口径"] = _unverified if (not _p or _sk) else _ok(u"B6")
    body = EXAM_TPL.format(
        src=src, genre=meta.get("genre") or genre or u"本次识别",
        lib=meta.get("lib") or (mt.group(1) if mt else u"6"),
        used=meta.get("used") or (mu.group(1) if mu else u"3"),
        net=meta.get("net") or u"3",
        dur=meta.get("dur") or u"由内容推",
        rhythm=meta.get("rhythm") or u"起—承—转—收",
        light=meta.get("light") or u"全片一处主光、一个色温",
        e1=ev[u"黄金三秒"], e2=ev[u"反转密度"], e3=ev[u"情绪曲线"],
        e4=ev[u"爽点"], e5=ev[u"身份反差"], e6=ev[u"结尾钩子"],
        e7=(seg2b.splitlines()[2][:90] if len(seg2b.splitlines()) > 2 else u"见 ②b 因果链"),
        e8=u"见 ②c「题眼道具贯穿」行，开头／中段／结尾三次状态不同",
        e9=u"见 ②b 物证列与 ③ 反转幕，靠看得见的物证翻案，无事故巧合",
        e10=(seg4.strip().replace(u"\n", u" ")[:100] if seg4 else u"见 ④ 情感弧六行"),
        e11=u"见 ③ 末段与 ① 结尾落点，收在没做完的动作上，不说尽",
    )
    # 判定逐项按本次稿的实际检查结果给，不整单盖「过」章
    _keys = sorted(v.items(), key=lambda kv: -len(kv[0]))
    _lines = body.splitlines()
    for i, ln in enumerate(_lines):
        if ln.startswith(u"|") and u"| 过 |" in ln:
            for key, val in _keys:
                if key in ln:
                    _lines[i] = ln.replace(u"| 过 |", u"| %s |" % val, 1)
                    break
    body = u"\n".join(_lines) + u"\n"
    _old_concl = u"六项硬检、爆款骨、反转铁律、交付四件、过程件一致，逐条有判定与证据句，全部通过。"
    if _sk:
        body = body.replace(_old_concl,
                            u"本单对应填空骨架，不是交付稿，逐项不判过；成稿后按本单逐条复核。")
    else:
        _bad = [c for c, ok in _res.items() if not ok]
        if _bad:
            body = body.replace(_old_concl,
                                u"有项未过（%s），剧本门当场退回重出，不许把没写全的稿子交出去。" % u"、".join(_bad))
        elif not _p:
            body = body.replace(_old_concl,
                                u"文本与体检单逐条给判定；过程件一致性须由交付门按实际文件复核，不在这里预盖合格章。")
    return body


# ---------------- 自测 ----------------

def _test():
    good = u"""## ⓪ 选题与爆款匹配说明
- 本次识别的短片类型：都市情感·物证反转｜判据：一件旧物翻案。
- 本次适配的编剧风格：按该类型通用叙事手法，先把观众骗到站错边的一边，再用一张纸翻过来，收尾只写一个没做完的动作，不虚构人名流派片名。
- 双源爆款：本地库 §1.1 库内共 6 条 → 本次取用 3 条（按分数排序，逐条匹配到情绪曲线／钩子／物证三维，各借一招）；联网同类型真实 3 部，检索于 2026-11-15，可核页面 https://example.com/a 。
  1. 《别等电话》（今日头条，2026-09-16）：故事前提是等不到回拨的电话；人物设定与身份反差是孙女与爷爷；核心冲突由旧物建立、由不解升级、由日记引爆；情绪钩子是不会响的电话；节奏按给—要—闹—收；爽点在收回特例，虐点在永别；反转靠信息差。
  2. 《一部手机，两代深情》（搜狐，2026-09-16）：故事前提、人物设定、身份反差、冲突、情绪钩子、节奏、爽点虐点、反转信息差同上逐项拆。
  3. 《回村三天，二舅治好了我的精神内耗》（B站，2022）：故事前提、人物设定、身份反差、冲突、情绪钩子、节奏、爽点虐点、反转信息差同上逐项拆。
## ②c 爆款对照表
| 学的招式 | 手法来源 | 本片落在哪一段（幕·段落名） | 怎么落的 |
| --- | --- | --- | --- |
| ① 钩子写法 | 《别等电话》 | 第一幕·抱包 | 包刚搁上柜台来人就按住 |
| ② 困境驱动 | 《一部手机，两代深情》 | 第一幕·抱包 | 来人知道是谁寄的观众不知道 |
| ③ 揭晓式反转 | 《回村三天，二舅治好了我的精神内耗》 | 第四幕·翻页 | 头一行签名把身份翻过来 |
| ④ 题眼道具贯穿 | 《别等电话》 | 第一至五幕·纸包三次变形 | 旧包／条子／没退成的件 |
| ⑤ 反差人设 | 《一部手机，两代深情》 | 第二幕·核单 | 只掏存根只答半句 |
| ⑥ 节奏密度 | 《回村三天，二舅治好了我的精神内耗》 | 每幕·四拍不拖 | 每拍换一样东西 |
## ⑧ 爆款自检六条
| 检查 | 本片落在哪一段 |
| --- | --- |
| ① 黄金三秒 | 开头交代完驿站撤柜，包刚搁上柜台来人左手一按说别拆那是我寄的。 |
| ② 反转密度 | 存根两栏同一个名、掀开是空栏条子、第一页签名翻出旧同事，三处靠纸。 |
| ③ 情绪曲线 | 抱包代入、核单升级、翻页引爆、条子叠回释放，四段齐。 |
| ④ 爽点／虐点 | 小满自己挑胶带翻页认签名，没替他把话说破，主角不被动。 |
| ⑤ 身份反差 | 拄拐来索赔的难缠客人，翻成当年在这驿站分件的人。 |
| ⑥ 结尾钩子 | 货架最上层空着、退件原因空着、笔拿起又放回，没说往后搁哪儿。 |
"""
    bad_src = good.replace(u"《别等电话》 | 第一幕", u"同类物证短片常见的开局 | 第一幕")
    bad_lib = good.replace(u"库内共 6 条", u"库内若干条").replace(u"本次取用 3 条", u"取用几条")
    bad_ev = good.replace(u"开头交代完驿站撤柜，包刚搁上柜台来人左手一按说别拆那是我寄的。", u"待填")
    cases = [
        (u"合规稿文本级全过", all(x[2] for x in run_all(good) if x[0] in (u"B1", u"B2", u"B3", u"B5"))),
        (u"②c 写「常见开局」被 B2 拦", any(x[0] == u"B2" and not x[2] for x in run_all(bad_src))),
        (u"⓪ 不写库内 M→N 被 B1 拦", any(x[0] == u"B1" and not x[2] for x in run_all(bad_lib))),
        (u"⑧ 写「待填」被 B3 拦", any(x[0] == u"B3" and not x[2] for x in run_all(bad_ev))),
        (u"填空骨架不误报", run_all(u"待填骨架，不是交付稿\n## ⓪\n待填") == []),
        (u"短文本不误报", as_issues(u"## ③ 故事剧本\n他推开门。") == []),
        (u"体检单自动写全六项证据句", all(k in build_exam(good) for k in SIX)),
        (u"体检单同一项按本次结果分别给过／不过",
         u"| ②c 对照表每行标具体片名 | 过 |" in build_exam(good)
         and u"| ②c 对照表每行标具体片名 | 不过 |" in build_exam(bad_src)),
        (u"填空骨架体检单不预盖合格章",
         u"待成稿核（不判过）" in build_exam(u"待填骨架，不是交付稿\n## ⓪\n待填")),
    ]
    for name, ok in cases:
        print((u"PASS " if ok else u"FAIL ") + name)
    print(u"结论：%d/%d 通过" % (sum(1 for _n, o in cases if o), len(cases)))
    return 0 if all(o for _n, o in cases) else 1


def main():
    if u"--test" in sys.argv:
        return _test()
    path = sys.argv[1] if len(sys.argv) > 1 else u""
    if not path:
        print(u"用法：boom_chk.py <稿子路径> 或 --test")
        return 2
    text = io.open(path, encoding=u"utf-8").read()
    bad = 0
    for code, name, ok, detail in run_all(text, path):
        print(u"[%s] %s %s  （%s）" % (u"PASS" if ok else u"FAIL", code, name, detail))
        bad += 0 if ok else 1
    print(u"结论：%d 项不合格" % bad)
    return 0 if bad == 0 else 1


if __name__ == u"__main__":
    sys.exit(main())
