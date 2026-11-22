# -*- coding: utf-8 -*-
"""平淡检测（flat_check）：不看词藻，只看这场戏有没有"事"。
指标全是可数的：动作数、外部变化数、台词有无、段落信息量、全篇动作密度。
一个段落/一镜里，人做的事少于 2 次、没有任何外部变化、字数还少，就是"没戏"。

v2.9.29 校准：按全量旧稿跑过一轮，剔掉三类误杀——流程结语行、纯台词段、
编号/段号前缀；「连续多段无台词」只在那些段本身也没动作时才判。
"""
import re

# 可拍动作（宽表：只要手在动、身在动、物在动都算）
ACTIONS = u"""拿 抓 端 推 塞 放 递 抹 捡 擦 剁 撒 抬 舀 砸 挡 拨 换 立 挂 蹲 爬 扶 收 扣 扔
摆 掐 添 倒 撑 拽 尝 咬 写 按 翻 拔 插 刷 盖 揭 拧 包 捆 拌 捞 抖 伸 摸 捏 揉 摊 卷 蘸
敲 掀 拎 捧 拍 劈 裹 卡 量 对 摁 抠 划 贴 夹 钩 翘 碾 刮 晃 搁 点 拉 蹭 垂
走 跑 站 坐 躺 靠 望 看 听 笑 哭 说 问 答 喊 叫 骂 咽 咳 喘 睡 醒 起 进 出 回 来 去
穿 脱 系 解 挪 搬 扛 抱 背 顶 塞 抽 掏 甩 抖 晃 踢 踩 跺 扑 追 逃 躲 藏 递 接 抢 夺
探 攥 堵 挣 崩 缩 转 皱 咧 瞪 盯 抿 摇 磕 挥 舔 嘬 吸 吐 蹲 起 回 头 抬 抵 抵住 挠 抄
""".split()

# 外部可见变化（局面/物件状态变了）
CHANGES = u"""掉 断 碎 裂 破 漏 洒 烧 灭 亮 响 停 开 关 翻 倒 塌 湿 干 冷 热 满 空
换 移 挪 递 塞 落 滑 滚 溅 泼 撕 折 压 弯 翘 蹦 飞 散 冒 涌 熄 亮起 挂上 摘 扣上
""".split()

CHANGE_PAT = [
    u"破", u"断", u"碎", u"掉下来", u"倒地", u"摔", u"淌", u"渗", u"溅", u"洒",
    u"灭", u"亮起来", u"响", u"停下来", u"关上", u"推开", u"翻开", u"翻过来",
    u"变成", u"换成", u"挪到", u"递到", u"塞进", u"落在地上", u"滑下去",
]

# 流程/交付结语行，不是戏，不参与判定
META_SKIP = (u"确认后", u"进阶段二", u"到此为止", u"等你", u"待填", u"下一步",
             u"自检", u"自查", u"请确认", u"以上为", u"步骤", u"规格如下")

STATIC = u"坐 站 躺 靠 看 望 听 盯 睡".split()

SPEECH_RE = re.compile(u"[“”「」]|：\\s*[“「]")


def _sentences(text):
    return [s.strip() for s in re.split(u"[。！？\n]", text) if s.strip()]


def count_actions(seg):
    """这一段里有几个动作（按出现次数算，不按不同词算）。"""
    n = 0
    for a in ACTIONS:
        n += seg.count(a)
    return n


def has_change(seg):
    if any(c in seg for c in CHANGES):
        return True
    return any(p in seg for p in CHANGE_PAT)


def has_speech(seg):
    return bool(SPEECH_RE.search(seg)) or (u"：" in seg and u"”" in seg)


def strip_prefix(seg):
    """去掉「段 3　」「3. 」「3、」这类前缀，字数才算得准。"""
    return re.sub(u"^(段\\s*\\d+[　\\s]*|\\d+[.、]\\s*)", u"", seg.strip())


def blocks(text, split_by_shot=False):
    """切段：M1 按空行切段；M2 按「**镜N（X秒）**」切镜。"""
    if split_by_shot:
        body = re.split(r"##\s*(?:③\s*)?附表", text)[0]
        m = re.findall(r"\*\*镜\d+（[\d.]+秒）\*\*\s*\n(.*?)(?=\n\*\*镜\d+|\Z)", body, re.S)
        return [u" ".join(x.strip() for x in b.splitlines() if x.strip()) for b in m]
    out = []
    for blk in re.split(u"\n\\s*\n", text):
        lines = []
        for ln in blk.splitlines():
            s = ln.strip()
            if not s or s.startswith(u"#") or s[0] in u"-*•>|【（(":
                continue
            if re.match(u"^(场|镜|段)\\s*\\d+", s) and (u"外景" in s[:20] or u"内景" in s[:20]):
                continue
            if any(w in s for w in META_SKIP):
                continue
            lines.append(s)
        if lines:
            out.append(u" ".join(lines))
    return out


def scan_flat(text, stage="m1"):
    """返回 [(序号, 类型, 片段)]。stage='m2' 按镜判。"""
    segs = blocks(text, split_by_shot=(stage == "m2"))
    hits = []
    silent_run = 0
    silent_acts = 0
    silent_head = u""
    total_chars = 0
    total_actions = 0
    for i, seg in enumerate(segs, 1):
        seg = strip_prefix(seg)
        n_char = len(re.sub(u"[\\s“”「」]", u"", seg))
        acts = count_actions(seg)
        total_chars += n_char
        total_actions += acts
        head = seg[:36]
        sp = has_speech(seg)

        still = sum(seg.count(x) for x in STATIC)
        eff = max(0, acts - still)          # 只坐着站着看，不算动作链
        if eff <= 1 and not has_change(seg) and n_char >= 18 and not sp:
            hits.append((i, u"没有动作链（只有姿势，没有事）", head))
        elif not has_change(seg) and acts <= 2 and n_char >= 40 and not sp:
            hits.append((i, u"没有外部变化（局面没动）", head))
        if n_char and n_char < 30 and not sp and acts <= 2:
            hits.append((i, u"信息量过低（%d 字，撑不起一镜/一段）" % n_char, head))
        elif n_char and n_char < 22 and not sp and not has_change(seg):
            hits.append((i, u"信息量过低（%d 字，撑不起一镜/一段）" % n_char, head))

        if sp:
            silent_run = 0
            silent_acts = 0
        else:
            if silent_run == 0:
                silent_head = head
            silent_run += 1
            silent_acts += acts
            lim = 3 if stage == u"m2" else 4
            if silent_run == lim and silent_acts <= lim * 2:
                # 连着几段没人说话，而且这几段本身也没动作 = 全靠白描撑
                hits.append((i, u"连续多镜/多段无人说话且无动作（全靠白描撑）", silent_head))

    if total_chars >= 300:
        density = total_actions * 100.0 / total_chars
        if density < 1.5:
            hits.append((0, u"全篇动作密度过低（每百字 %0.1f 个动作，应 ≥1.5）" % density, u"全篇"))
    return hits


if __name__ == "__main__":
    import io, sys, os
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        import subprocess
        _r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "test_flat.py")])
        sys.exit(_r.returncode)
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(u"用法：python flat_check.py <文档.md> [m1|m2] 或 --test")
        sys.exit(1)
    t = io.open(sys.argv[1], encoding="utf-8").read()
    stage = sys.argv[2] if len(sys.argv) > 2 else "m1"
    h = scan_flat(t, stage)
    print(u"scan_flat：%d 处" % len(h))
    for it in h:
        print(u"  L%s [%s] %s" % (it[0], it[1], it[2]))
