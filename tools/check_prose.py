# -*- coding: utf-8 -*-
"""M1 第六道检查：scan_prose —— 抓「小学生句」。
覆盖：抽象判断句 / 无谓语碎句 / 名词堆叠 / 电报体 / 段号编号 /
      场景交代句 / 静物当主角 / 段首没有动作。
只判句子层，不碰引号内台词与规格清单行。判定依据：SKILL §7.6.9 文体六条 + §7.6.10 按场写。
例外：剧本开头第一段是「交代故事」的地方（地方、日子、由头、人），允许用交代句、
      不要求段首就有动作；从第二段进具体行为剧情起，上面两条照旧生效。
"""
import re

VERBS = set(u"""拿 抓 端 推 塞 放 递 抹 捡 擦 剁 撒 抬 舀 砸 挡 拨 换 立 挂 蹲 爬 扶 收 扣 扔
摆 掐 添 倒 撑 拽 尝 咬 写 按 翻 拔 插 刷 盖 揭 拧 包 捆 拌 捞 抖 伸 摸 捏 揉 摊 卷 蘸
敲 掀 拎 捧 拍 劈 裹 卡 量 对 摁 抠 划 贴 夹 钩 翘 碾 刮 晃 搁 点 拉 蹭 垂
走 跑 站 坐 躺 靠 望 看 听 笑 哭 说 问 答 喊 叫 骂 咽 咳 喘 睡 醒 起 进 出 回 来 去
亮 灭 响 停 转 开 关 流 渗 漏 烧 断 碎 沉 飘 落 升 散 变 成 剩 留 空 满 干 湿
合 嗅 照 打 探 凑 缩 颤 映 铺 扫 闻 瞄 扭 顶 挪 顿 拂 盯 攥 拨 掀 舔 蹭 咬 卷 捂
搭 托 踩 掰 抡 掂 掖 撂 捋 接 扶 抱 拎 拴 挽 掸 抠 捻 摁 拧 撕 搓 捂 摸 拍 敲
""".split())

PREDICATE_HINTS = u"是有在没不着了很太都也还又能会要想把被让给从向对为像似如"

PLACE_TAIL = u"边|上|下|里|外|前|后|口|面|头|角|院|屋|房|厅|台|墙|门"
EXIST_PRED = u"有|没有|是|空着|亮着|黑着|堆着|摆着|立着|放着|挂着|靠着"
OBJ_VERB = u"立|摆|放|挂|靠|摊|堆|码|搁|横|竖|倒|躺|翘|贴"

CJK = u"一-龥"


def _has_predicate(s):
    if any(v in s for v in VERBS):
        return True
    if any(h in s for h in PREDICATE_HINTS):
        return True
    return False


def _skip_line(s):
    """非正文行：标题、清单、说明、规格编号、元信息、带七项标注的台词行。"""
    if not s or s.startswith(u"#"):
        return True
    if s[0] in u"-*•>|【（(":
        return True
    # 台词行「小林（女·26·…·楼道声）：「……」」是标注不是散文，
    # 七项括号里的顿号会被当成逗号切碎误判，整行跳过
    if (u"（男·" in s or u"（女·" in s) and \
            any(q in s for q in (u"：「", u"：“", u'："', u':"')):
        return True
    if re.match(u"^(场|镜|段)\\s*\\d+", s) and (u"外景" in s[:20] or u"内景" in s[:20]) \
            and u"。" not in s:
        return True
    if re.match(u"^\\d+[.、]\\s", s):
        return True
    if re.match(u"^[%s]{1,6}：" % CJK, s):
        return True
    if re.match(u"^\\d+\\s*[%s]{1,8}：" % CJK, s):
        return True
    if re.match(u"^\\d+\\s", s):
        return True
    return False


def _strip_scene_head(s):
    """剥掉「场 1　外景·〔地点〕　夜」这类场头前缀。"""
    s = re.sub(u"^(场|镜|段)\\s*\\d+[　\\s]*", u"", s)
    if u"外景" in s[:12] or u"内景" in s[:12]:
        s = re.sub(u"^.*?(外景|内景)[^　]*[　\\s]*", u"", s)
    return s


def _story_body(text):
    """只取叙事正文：M1 取 ## ③ 那一节；分镜稿（无 ③ 节）原样返回。"""
    m = re.search(r"##\s*③[^\n]*\n(.*?)(?=\n##\s|\Z)", text, re.S)
    return m.group(1) if m else text


def scan_prose(text):
    hits = []
    # 附表是清单与对照表，不是叙事正文；整段切掉，别把条目当碎句冤枉
    text = re.split(r"##\s*(?:③\s*)?附表", text)[0]
    # 文生图提示词文档不是剧本正文：「老周｜三视图提示词：」这类标题行、以及
    # 「台面是磨亮的旧木」这类外观属性句，会被剧本句法规则当成碎句／抽象判断句。
    # 剧本与分镜正文不会出现这种标题行，识别到即整篇按提示词处理，不误伤叙事稿。
    if len(re.findall(u"｜\\s*(?:三视图|场景图|道具图)提示词\\s*[：:]", text)) >= 2:
        return []
    # ⓪①②④⑤⑦⑧ 是要求、表格与元信息，不是散文；只判 ③ 那一节，别拿清单当碎句
    text = _story_body(text)
    # 开头第一段是交代故事的地方，允许「是／有／在」这类交代句、也不要求段首有动作；
    # 从第二段（具体行为剧情）起，两条老规矩照旧。
    _paras = re.split(u"\n\\s*\n", text)
    _open = _paras[0].strip() if _paras else u""
    _open_ok = len(_paras) >= 2 and len(_open) >= 40

    def _in_open(s):
        return _open_ok and len(s) >= 6 and s[:6] in _open

    # 1 段号编号：正文应用场，不许「段 N」
    for ln in text.split(u"\n"):
        if re.match(u"^段\\s*\\d+", ln.strip()):
            hits.append((0, u"段号编号（应用场）", ln.strip()[:30]))
            break

    # 2 逐句句法
    lines = []
    for raw in text.split(u"\n"):
        s = raw.strip()
        if _skip_line(s):
            continue
        if s[0] in u"【（(":
            continue
        s = _strip_scene_head(s)
        s = re.sub(u"\\S*（[男女]·[^）]*）\\s*[：:]\\s*[「“][^」”]*[」”]", u"［台词］", s)
        s = re.sub(u"“[^”]*”", u"［台词］", s)
        s = re.sub(u"[一-龥]{1,5}说[：:]「[^」]*」", u"", s)
        s = re.sub(u"「[^」]*」", u"", s)
        s = s.replace(u"，，", u"，").rstrip(u"，、 ")
        for part in re.split(u"[。！？]", s):
            part = part.strip()
            if part:
                lines.append(part)

    for i, s in enumerate(lines, 1):
        n = len(s)
        # 「散了一地／抖了一片」是量词短语，不是「X 是 Y 的」判断句；量词前有数词就放过
        if re.search(u"(?<![一两几半满])(?<![0-9])[的地得]$|"
                     u"是[^。]{0,3}(黑|白|亮|暗|冷|热|静|空|破|旧)", s):
            hits.append((i, u"抽象判断句", s[:40]))
            continue
        if 4 <= n <= 22 and not _has_predicate(s) and u"［台词］" not in s:
            hits.append((i, u"无谓语碎句", s[:40]))
            continue
        if re.match(u"^[%s]{2,8}(%s)(%s)" % (CJK, PLACE_TAIL, EXIST_PRED), s) \
                and not _in_open(s):
            hits.append((i, u"场景交代句（该写成人的动作）", s[:40]))
            continue
        m3 = re.match(u"^(那|这|一|几|两|三)?([%s]{1,6})(%s)(在|着|到|上)"
                      % (CJK, OBJ_VERB), s)
        if m3 and not re.search(u"把|被|让|给", s):
            head3 = m3.group(2)
            if (not any(x in head3 for x in u"他她我你咱")) and \
                    (not any(v in head3 for v in VERBS)):
                hits.append((i, u"静物当主角（应让人来处置它）", s[:40]))
                continue
        m = re.match(u"^([%s]{1,4}(%s)[^，]{0,6})(一圈|一片|一层|一堆|一地)([^，]*)"
                    % (CJK, PLACE_TAIL), s)
        if m and not _has_predicate(m.group(1) + m.group(4)):
            hits.append((i, u"名词堆叠", s[:40]))
            continue
        # 只抓「把/将 某物 一叠词量词」且量词后没写处置结果的半句；
        # 按逗号隔开的小句逐个查（半句后面还接半句时也要抓），
        # 「一根根掰开才取」「天色一点点暗」都写完了，不许冤枉。
        _half_pat = r"[把将拿捡拨拽拆][^，。！？]{0,8}一(根根|条条|片片|层层|点点|下下|口口|截截|颗颗|只只|个个|回回)\s*$"
        _half = any(re.search(_half_pat, cl.strip()) for cl in re.split(u"[，,]", s))
        if _half:
            hits.append((i, u"半句断气（动作没写完）", s[:40]))
            continue
        cls = [c.strip() for c in re.split(u"，|,", s) if c.strip()]
        if len(cls) >= 2:
            tail = cls[-1]
            if len(tail) <= 12 and not _has_predicate(tail) and u"［台词］" not in tail:
                hits.append((i, u"名词堆叠（后半截没谓语）", s[:40]))

    # 3 段首必须有动作：从第二段（具体行为剧情）起，每段第一句要有动作动词，只有是/有/在 不算
    pno = 0
    hitno = 0
    for blk in re.split(u"\n\\s*\n", text):
        pno += 1          # 第一段是交代故事的开头，豁免
        first = None
        for raw in blk.split(u"\n"):
            s = raw.strip()
            if _skip_line(s):
                continue
            if re.match(u"^(场|镜|段)\\s*\\d+", s):
                s = _strip_scene_head(s)
                if len(s.strip()) < 4:
                    continue
            if not s.strip():
                continue
            first = s
            break
        if (not first) or (u"“" in first) or (u"［台词］" in first):
            continue
        head = re.split(u"[。！？]", first)[0].strip()
        if len(head) < 4:
            continue
        if (pno >= 2 or not _open_ok) and not any(v in head for v in VERBS):
            hitno += 1
            hits.append((hitno, u"段首没有动作（该落在人身上）", head[:36]))

    # 4 电报体：连续短句
    run = 0
    for i, s in enumerate(lines, 1):
        if len(s) <= 7:
            run += 1
            if run == 2:
                hits.append((i, u"电报体（连续短句）", lines[i - 2][:30] + u"…"))
        else:
            run = 0
    return hits


def scan_board_labels(text):
    """分镜正文禁用标签：`【取景】`/`取景：`/表格化九项/时间轴条目。"""
    heads = u"分镜编号|镜号|场景|取景|景别|视角|运镜|构图|光影|布光|人物动作|台词|音效|时长"
    pats = [
        (u"方括号标签", re.compile(u"【(%s)" % heads)),
        (u"冒号标签", re.compile(u"^\\s*(%s)\\s*[：:]" % heads, re.M)),
        (u"时间轴条目", re.compile(u"^\\s*\\d+\\s*s?\\s*[-–~]\\s*\\d+\\s*s?\\s*[（(]")),
        (u"九项表格", re.compile(u"\\|\\s*(分镜编号|取景|运镜|构图|光影)\\s*\\|")),
    ]
    hits = []
    for name, pat in pats:
        for m in pat.finditer(text):
            line_no = text.count(u"\n", 0, m.start()) + 1
            hits.append((line_no, name, text[m.start():m.start() + 24].replace(u"\n", u" ")))
    return hits


if __name__ == "__main__":
    import io, sys, os
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        import subprocess
        _r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "test_prose.py")])
        sys.exit(_r.returncode)
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(u"用法：python check_prose.py <文档.md> 或 --test")
        sys.exit(1)
    t = io.open(sys.argv[1], encoding="utf-8").read()
    h = scan_prose(t)
    print(u"scan_prose：%d 处" % len(h))
    for it in h:
        print(u"  L%s [%s] %s" % (it[0], it[1], it[2]))
