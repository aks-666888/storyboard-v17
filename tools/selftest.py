# -*- coding: utf-8 -*-
"""M1 一键自测：验证「一句话 -> 剧本草稿 -> 确认节点 A -> 拒绝越阶段」整条链路。

用法：python selftest.py
产出：output\\_m1_selftest\\report.txt（同时打印到控制台）
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SANDBOX = HERE.parent / "output" / "_selftest_runs"
os.environ["SB_OUTPUT"] = str(SANDBOX)

sys.path.insert(0, str(HERE))
import sb_core as core  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CLI = HERE / "storyboard.py"
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((bool(cond), name, detail))
    print("%s  %s%s" % ("[PASS]" if cond else "[FAIL]", name, ("  " + detail) if detail else ""))


def run_cli(*args):
    p = subprocess.run([sys.executable, str(CLI)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    ts = datetime.now().isoformat(timespec="seconds")
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX, ignore_errors=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    print("== M1 自测 %s ==" % ts)
    print("沙箱：%s" % SANDBOX)
    print("")

    # 1 文件与库
    check("SKILL.md 存在且体量足够", core.SKILL_FILE.exists() and core.SKILL_FILE.stat().st_size > 20000,
          "%d 字节" % (core.SKILL_FILE.stat().st_size if core.SKILL_FILE.exists() else 0))
    entries = core.parse_library()
    stats = core.library_stats(entries)
    short = [g for g in stats if stats[g]["count"] < 3]
    check("爆款储备库 11 子类各 >=3", len(entries) >= 33 and not short,
          "共 %d 条，缺口：%s" % (len(entries), short or "无"))

    # 1b 反固化：SKILL 有条款、画像表齐全、时长随子类变化
    sk_text = core.SKILL_FILE.read_text(encoding="utf-8") if core.SKILL_FILE.exists() else ""
    check("SKILL.md 含反固化条款", ("反固化条款" in sk_text) and ("不是默认值" in sk_text))
    prof = core.parse_profile()
    check("六维画像覆盖 11 子类", len(prof) >= 11, "实得 %d 类" % len(prof))
    s14 = core.suggest_scale(core.GENRE_BY_ID["1.4"], profile=prof)
    s21 = core.suggest_scale(core.GENRE_BY_ID["2.1"], profile=prof)
    s31 = core.suggest_scale(core.GENRE_BY_ID["3.1"], profile=prof)
    check("时长由子类现算（不是固定值）",
          len({s14["total_seconds"], s21["total_seconds"], s31["total_seconds"]}) == 3,
          "1.4=%d秒 2.1=%d秒 3.1=%d秒（镜数均不预设）" % (
              s14["total_seconds"], s21["total_seconds"], s31["total_seconds"]))

    # 2 题材识别
    cases = [
        ("外卖员暴雨夜送完最后一单，发现顾客是三年前走失的女儿", "1.1"),
        ("相亲现场翻车，男方带着他妈和一条狗来整活", "3.1"),
        ("为什么飞机能飞起来，一张纸就讲清楚", "3.2"),
    ]
    for idea, want in cases:
        got = core.classify(idea)["primary"]["id"]
        check("题材识别：%s…" % idea[:10], got == want, "期望 %s 实得 %s" % (want, got))

    # 3 爆款匹配 >=3 且带借鉴点
    ok_match = True
    detail = []
    for idea, want in cases:
        g = core.classify(idea)["primary"]
        m = core.match_works(g, entries, idea=idea)
        if len(m["items"]) < 3:
            ok_match = False
        detail.append("%s=%d" % (g["id"], len(m["items"])))
        for e in m["items"]:
            if not e["link"]:
                ok_match = False
    check("每个子类匹配到 >=3 且案例带链接", ok_match, " ".join(detail))

    # 4 prompt 注入 v1.7 五条硬律
    g = core.classify(cases[0][0])["primary"]
    m = core.match_works(g, entries, idea=cases[0][0])
    p = core.build_stage1_prompt(cases[0][0], g, m, core.suggest_scale(g, 180), {"platform": None, "ratio": None, "real": False, "ref": ""})
    marks = ["① 可呈现", "② 不虚接", "③ 动作三问", "④ 时间锚点集中", "⑤ 禁词全文清扫"]
    missing = [x for x in marks if x not in p]
    check("prompt 注入五条硬律", not missing, "缺：%s" % (missing or "无"))
    check("prompt 含禁词清单与台词铁律", ("上一镜" in p) and ("≤14 字" in p) and ("确认节点 A" in p))

    # 5 自检引擎能抓违规、放行干净文本
    bad = ("3. 她化到院子里，二十五年前的照片掉在地上。他心里一沉，走过去扶着门，孤独感涌上来。"
           "台词（女·34岁·低哑·慢·平静）：\"你回来啦。\"")
    clean = ("3. 她走到院门口，左手扶住门框，右手把照片压在桌角。晨雾还没散，院墙上落着一层薄雪。"
             "台词（女·34岁·低哑·慢·平静）：\"你回来啦。\"")
    n_bad = len(core.scan_text(bad))
    n_clean = len(core.scan_text(clean))
    check("自检能抓到违规", n_bad >= 5, "命中 %d 处" % n_bad)
    check("自检放行干净文本", n_clean == 0, "误报 %d 处" % n_clean)

    # v2.9.24 起分镜一律一镜一段散文；v2.9.33 起术语按用户规范写进句子（另起【】标签即违规）
    tech_ok = ("## ③ 分镜脚本\n**镜1（4秒）**\n"
               "楼道里的灯只亮半边，只框住他和扶手这一截，离他两步，从楼梯下面仰着往上拍"
               "，画面跟着他往楼上走。冷白灯光从头顶压下来落在他右肩，"
               "左半边脸沉在影子里。他右手拎着袋子，袋子勒得指头弯下去，走到三楼门口停住，把袋子换到左手"
               "（Medium Close-Up 中近景 · Follow Shot 跟随运镜 · Leading Lines 引导线构图 · Key Light 主光）。\n"
               "小林（女·26·清亮·平·中·随意·楼道声）：「我上来了。」\n")
    tech_tag = ("## ③ 分镜脚本\n**镜1（4秒）**\n"
                "【中景·平视·手持跟拍·冷白荧光打在灰墙上】\n"
                "楼道里的灯只亮半边，他右手拎着袋子上楼，走到三楼门口停住。\n"
                "小林（女·26·清亮·平·中·随意·楼道声）：「我上来了。」\n")
    _tech_ok_n = len(core.scan_text(tech_ok, stage="storyboard"))
    _tech_tag_n = len(core.scan_text(tech_tag, stage="storyboard"))
    check("引擎放行散文式分镜（机位与光写进句子）", _tech_ok_n == 0, "误报 %d 处" % _tech_ok_n)
    check("引擎拦截【】技术标签行", _tech_tag_n >= 1, "命中 %d 处" % _tech_tag_n)

    # 6 E 盘守卫
    blocked = False
    try:
        core.assert_e_drive(Path("C:\\Windows\\Temp\\sb_probe"))
    except RuntimeError:
        blocked = True
    check("C 盘写入被拒绝", blocked)

    # 7 CLI 全链路
    rc, out = run_cli("doctor")
    check("doctor 通过", rc == 0, out.strip().splitlines()[-1][:60] if out.strip() else "")

    rc, out = run_cli("lint")
    check("lint 通过", rc == 0)

    run_dir = None
    rc, out = run_cli("stage1", "--idea", cases[0][0], "--duration", "180")
    if rc == 0:
        for ln in out.splitlines():
            if ln.startswith("[OK] run:"):
                run_dir = ln.split("[OK] run:", 1)[1].strip()
    check("stage1 出稿", rc == 0 and run_dir and Path(run_dir).exists(), out.strip().splitlines()[0] if out.strip() else "")
    if run_dir:
        rd = Path(run_dir)
        for f in ["01_prompt.md", "02_剧本草稿.md", "03_确认A.md", "run.json", "selfcheck.txt"]:
            check("产物 %s" % f, (rd / f).exists())
        meta = json.loads((rd / "run.json").read_text(encoding="utf-8"))
        check("run.json 标记未确认", meta["confirmed_a"] is False and meta["stage"] == "script_draft")
        check("产物落在 E 盘", str(rd).upper().startswith("E:"), str(rd)[:12])
        draft = (rd / "02_剧本草稿.md").read_text(encoding="utf-8")
        check("stage1 产物含 ⑦ 前提立住节", "## ⑦" in draft, "缺" if "## ⑦" not in draft else "")

        # 真实链路：不再只拿手写小样本验门禁，直接用工具自己出的指令与骨架跑一遍
        prompt = (rd / "01_prompt.md").read_text(encoding="utf-8")
        _old = ["本领在山里学完才下山", "同一门手艺", "真拟人", "四条腿跑", "舔毛", "摇尾巴",
                "山里那道工序", "给师傅做一件具体的事"]
        _hit = [w for w in _old if w in prompt]
        check("真实链路：出稿指令不带旧题材专属条", not _hit, "；".join(_hit) or "无")
        _plat = [w for w in ["即梦", "可灵", "SD/Flux", "LibTV"] if w in prompt]
        check("真实链路：出稿指令不带出图平台名", not _plat, "；".join(_plat) or "无")
        _must = ["九项信息", "前提立住", "爆款自检六条", "底本不断线", "补写台词",
                 "前后对不上五不写", "题眼道具"]
        _miss = [w for w in _must if w not in prompt]
        check("真实链路：出稿指令规矩齐备", not _miss,
              "缺：" + "/".join(_miss) if _miss else "齐")
        _rg = __import__("subprocess").run(
            [sys.executable, str(HERE / "m1_gate.py"), str(rd / "02_剧本草稿.md")],
            capture_output=True, text=True, encoding="utf-8")
        check("真实链路：待填骨架被剧本交付门挡下（不许当成品）", _rg.returncode != 0,
              "退出码 %s" % _rg.returncode)
        check("待填骨架自带不是成品的声明", "待填骨架" in draft)

        sheet = (rd / "03_确认A.md").read_text(encoding="utf-8")
        bad_q = [w for w in ["用这三个，还是换", "按 180 秒", "现在：180 秒 / 18 镜", "人物要不要增减"]
                 if w in sheet]
        check("确认单无固化问法", not bad_q, "命中：%s" % (bad_q or "无"))
        check("确认单带本次自适应参数",
              ("本次自适应参数" in sheet) and ("库内检索" in sheet) and ("依据：" in sheet))

        rc, out = run_cli("stage2", "--run", str(rd))
        check("未确认时 stage2 被拒绝", rc == 2, out.strip().splitlines()[0][:50] if out.strip() else "")

        # 阶段二 · 分镜引擎（A 确认后应真出稿，不再只打规格）
        rc, out = run_cli("confirm", "A", "--user-ok", "--run", str(rd))
        check("confirm A 锁稿", rc == 0 and (rd / "02_剧本草稿.locked.md").exists())
        rc, out = run_cli("stage2", "--run", str(rd))
        check("stage2 出分镜", rc == 0 and (rd / "04_分镜.md").exists(),
              out.strip().splitlines()[0][:60] if out.strip() else "")
        if (rd / "04_分镜.md").exists():
            board = (rd / "04_分镜.md").read_text(encoding="utf-8")
            secs = [float(x) for x in __import__("re").findall(
                r"镜\s*\d+\s*（\s*(\d+(?:\.\d+)?)\s*秒\s*）", board)]
            check("分镜秒数合计贴近总时长", bool(secs) and abs(sum(secs) - 180) <= 18, "合计 %s" % sum(secs))
            check("单镜不超 15 秒", bool(secs) and max(secs) <= 15, "最长 %s 秒" % (max(secs) if secs else "无"))
            check("秒数不是同值均分", len(set(secs)) >= 3, "不同秒数 %d 种" % len(set(secs)))
            sec_marks = ["## ③ ", "## ③b", "## ③c", "## ④ ", "## ⑤ ", "## ⑥ ", "## ⑦ ", "## ⑧ "]
            miss = [m for m in sec_marks if m not in board]
            check("分镜八小节齐全", not miss, "缺：%s" % (miss or "无"))
            check("分镜无自检违规", not core.scan_text(board) and not core.scan_shots(board))
            check("分镜有确认节点 B 清单", (rd / "05_确认B.md").exists())

        rc, out = run_cli("confirm", "B", "--user-ok", "--run", str(rd))
        check("confirm B 锁分镜", rc == 0 and (rd / "04_分镜.locked.md").exists())

        rc, out = run_cli("stage3", "--run", str(rd))
        check("stage3 出提示词", rc == 0 and (rd / "06_提示词.md").exists(),
              out.strip().splitlines()[0][:60] if out.strip() else "")
        if (rd / "06_提示词.md").exists():
            pk = (rd / "06_提示词.md").read_text(encoding="utf-8")
            check("提示词三段齐全", all(k in pk for k in ["### ⑦a", "### ⑦b", "### ⑦c"]))
            check("提示词每条带负向", pk.count("负向：") >= 3, "负向 %d 条" % pk.count("负向："))
            check("题眼道具标星", "⭐" in pk)
            check("提示词有确认节点 C 清单", (rd / "07_确认C.md").exists())

        rc, out = run_cli("confirm", "C", "--user-ok", "--run", str(rd))
        meta2 = json.loads((rd / "run.json").read_text(encoding="utf-8"))
        check("confirm C 走到交付终点",
              rc == 0 and meta2["confirmed_c"] is True and meta2["stage"] == "confirmed_c"
              and (rd / "06_提示词.locked.md").exists())

        # 门禁：另起一单，只确认 A，stage3 必须仍被拒绝（缺 confirmed_b）
        rc, out = run_cli("stage1", "--idea", cases[1][0], "--shots", "10")
        rd2 = None
        for ln in out.splitlines():
            if ln.startswith("[OK] run:"):
                rd2 = Path(ln.split("[OK] run:", 1)[1].strip())
        if rd2:
            run_cli("confirm", "A", "--user-ok", "--run", str(rd2))
            rc, out = run_cli("stage3", "--run", str(rd2))
            check("只确认 A 时 stage3 被拒绝", rc == 2,
                  out.strip().splitlines()[0][:50] if out.strip() else "")

    # 8 另外两个题材也跑通（证明通用性）
    for idea, _ in cases[1:]:
        rc, out = run_cli("stage1", "--idea", idea, "--shots", "10")
        check("通用性：%s… 出稿" % idea[:8], rc == 0)

    # 9 本轮新增硬约束（用户第 3/4/5/6 条答复）
    skill = (HERE.parent / "storyboard-v17" / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    card = (HERE.parent / "通用分镜技能卡.md").read_text(encoding="utf-8", errors="replace")
    check("SKILL 写明时间服从画面", ("时间服从画面" in skill) and ("先有画面，再有秒数" in skill))
    # v2.9.18 前提立住落进引擎
    check("SKILL 模板含 ⑦ 前提立住节", "## ⑦ 前提立住" in skill)
    gp = core.build_stage1_prompt(cases[0][0], core.classify(cases[0][0])["primary"],
                                  core.match_works(core.classify(cases[0][0])["primary"], entries, idea=cases[0][0]),
                                  core.suggest_scale(core.classify(cases[0][0])["primary"], 180),
                                  {"platform": None, "ratio": None, "real": False, "ref": ""})
    check("prompt 注入 ⑦ 前提立住节", "## ⑦ 前提立住" in gp)
    check("卡片写明时间服从画面", "时间服从画面" in card)
    check("SKILL 有单镜 15 秒上限且无下限", ("单镜上限 15 秒" in skill) and ("无下限" in skill))
    check("SKILL 有爆款对照硬规", ("7.6.2" in skill) and ("爆款对照表" in skill) and ("题眼道具" in skill))
    check("SKILL 明令禁止固定秒数", ("镜数＝总时长÷固定秒数" in skill) and ("一律不采纳" in skill))
    check("SKILL 要求本领大众熟悉（禁冷门行当当主线）",
          ("大众熟悉" in skill) and ("说给楼下大爷听" in skill) and ("不许挑冷门工序当主线" in skill))
    check("SKILL 有严师错觉—反转硬规",
          ("7.6.3" in skill) and ("严师的错觉" in skill) and ("反转靠物证" in skill)
          and ("不一样的严" in skill) and ("先欺负人再道歉" in skill))
    # v2.9.2 写作层硬规
    check("SKILL 有段落动作硬规（7.6.4）",
          ("7.6.4" in skill) and ("谁 + 动词 + 对象" in skill) and ("不可逆的变化" in skill))
    check("SKILL 禁三种句子",
          ("状态直说句" in skill) and ("解释旁白句" in skill) and ("总结升华句" in skill))
    check("SKILL 要求先由别人问、主角才答",
          ("问话必须先由别人开口" in skill) and ("不许没人问他就自答" in skill))
    check("SKILL 有中段必有一败（7.6.5）",
          ("7.6.5" in skill) and ("真败" in skill) and ("代价硬规" in skill)
          and ("不是天灾、不是被人陷害" in skill))
    check("SKILL 有结尾三不＋错位＋归还（7.6.6）",
          ("7.6.6" in skill) and ("不总结、不喊口号、不解释心理" in skill)
          and ("对方说错了，主角不纠正" in skill) and ("一归还" in skill))
    check("SKILL 交付物含 ②d 段落动作表", "②d 段落动作表" in skill)
    check("卡片写明动作/中段必败/结尾错位三条",
          ("每段一个动作" in card) and ("中段必有一败" in card) and ("结尾三不" in card))
    # v2.9.3 人话与句法
    check("SKILL 有动笔前三根判据与五行卡（7.6.8）", ("### 7.6.8" in skill) and (u"五行卡" in skill) and (u"因必须有人做" in skill))
    ref = HERE.parent / "storyboard-v17" / "references" / "人话正误对照.md"
    ref_txt = ref.read_text(encoding="utf-8") if ref.exists() else ""
    check("正误对照库存在且 >=30 组", ref.exists() and ref_txt.count("| 错 |") + ref_txt.count("| 错 |") >= 5 and ref_txt.count("\n|") >= 60, "行数 %d" % ref_txt.count("\n|"))
    check("SKILL 禁逗号硬接因果", u"用逗号把两件事硬接成因果" in skill)
    check("SKILL 有人话与句法硬判（7.6.7）",
          ("7.6.7" in skill) and ("物件当施事" in skill) and ("没写手在哪" in skill))
    bad_h = "学徒（男·17 岁）：\"这勺，谁教的？\"\n掌柜捧铜牌递到他胸前。\n葱香顶上来。\n"
    hit_h = core.scan_human(bad_h)
    check("scan_human 抓到物件当施事／抽象动词／文学腔", len(hit_h) >= 3, "命中 %d 处" % len(hit_h))
    good_h = "学徒盯着他手里那把勺：\u201c这手艺，跟谁学的？\u201d\n掌柜把铜牌搁在案板上，牌面朝他。\n"
    bad_b = "学徒凑到灶边，眼睛落在他那把勺上。他踩着师弟们的鼾声溜回灶房。"
    hit_b = core.scan_human(bad_b)
    check("scan_human 抓到身体部位当施事／声音当场景", len(hit_b) >= 2, "命中 %d 处" % len(hit_b))
    check("scan_human 放行人话", core.scan_human(good_h) == [], "误报 %d 处" % len(core.scan_human(good_h)))
    # v2.9.9 八条豁口
    check("SKILL 五行卡含第 6 格入段前提", (u"他怎么会在这儿" in skill) and (u"六格" in skill))
    check("SKILL 有段间承接判据", u"上一段的结尾必须是下一段开头的因" in skill)
    check("SKILL 同一问句只许原样出现一次", u"同一问句全片只许原样出现一次" in skill)
    check("SKILL 台词必须有听者与可见反应", (u"台词必须有听者" in skill) and (u"可见反应" in skill))
    check("SKILL 动作可执行三问", (u"摄像机架在哪" in skill) and (u"几只手" in skill))
    check("SKILL 年岁只靠动作旧物旁人的话", (u"不许用\"多年后\"" in skill or u"多年后" in skill) and (u"旧物变化" in skill))
    check("SKILL 题眼道具三次状态登记", u"三次状态" in skill)
    bad_beat = "段 1　他站着。风从门口进来。\n\n段 2　阿橘左手扶匾，右手拿抹布擦牌面。\n"
    check("scan_beat 抓到整段空转", len(core.scan_beat(bad_beat)) >= 1, "命中 %d 处" % len(core.scan_beat(bad_beat)))
    check("scan_beat 放行有动作的段", core.scan_beat("段 1　阿橘左手扶匾，右手拿抹布擦牌面。\n") == [])
    check("SKILL 有十六、承接必须是可见事件", u"十六、承接句必须是可见事件" in skill)
    check("SKILL 有十三、行当常识闸门", u"十三、行当常识闸门" in skill)
    bad_logic = u"段 3　这条规矩是他在山里学的。\n段 10　老板嫌费盐。\n段 12　那三盆饭传出去，婚宴雇他。\n"
    hl = core.scan_human(bad_logic)
    check("scan_human 抓段首解释句／心理动机／名声承接", len(hl) >= 3, u"命中 %d 处" % len(hl))
    ok_logic = u"段 3　木门半开，天光落在矮凳膝头上。\n段 10　老板两手把钱匣搂进怀里。\n段 12　主家在棚口数工钱，抬头把他叫到灶前。\n"
    check("scan_human 放行可见的承接与动机", core.scan_human(ok_logic) == [], u"误报 %d 处" % len(core.scan_human(ok_logic)))
    check("scan_capability 抓到越级动作", len(core.scan_capability(u"段 3　他爬上灶台煎整条鱼。\n", [{"from": 3, "to": 5, "forbid": ["煎"]}])) == 1)
    check("scan_capability 区间外不判", core.scan_capability(u"段 10　他煎鱼。\n", [{"from": 3, "to": 5, "forbid": ["煎"]}]) == [])
    lex = core.load_lexicon()
    check("scan_commonsense 抓整筐配菜下锅", len(core.scan_commonsense(u"段 7　他把整筐葱倒进锅里。", "厨师", lex)) >= 1)
    check("scan_commonsense unless 放行当场被罚", core.scan_commonsense(u"段 7　他把整筐葱倒进锅，老浣让他把葱捞出来重削。", "厨师", lex) == [])
    check("scan_commonsense 抓生熟同案", len(core.scan_commonsense(u"段 9　生鱼搁在凉菜案板上。", "", lex)) >= 1)

    # 9b v2.9.18 前提立住已落进引擎：m1_gate 对正确填的 ⑦ 放行、对缺 ⑦ / 旁白拦截
    good_m1 = ("## ⑦ 前提立住（开场两件事必须讲清）\n"
               "| 检查项 | 落地内容 |\n"
               "| 求助方为何自己干不了 | 张姨扶墙喘气，走远路膝盖撑不住 |\n"
               "| 双方什么关系、另一方凭啥答应 | 邻里：张姨帮收快递，小林租她楼下，自己养过狗 |\n"
               "| 人设与开场动作是否矛盾 | 否：小林独居白领，开场只是上楼，无矛盾 |\n")
    bad_m1 = "## ③ 故事剧本\n他心里念着旁白。\n\n## ④ 情感线与人物弧\n主情绪：x\n"
    _td = SANDBOX / "_m1_gate_probe"
    _td.mkdir(parents=True, exist_ok=True)
    _gp = _td / "good.md"; _gp.write_text(good_m1, encoding="utf-8")
    _bp = _td / "bad.md"; _bp.write_text(bad_m1, encoding="utf-8")
    _rg = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_gp)], capture_output=True, text=True, encoding="utf-8")
    _rb = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_bp)], capture_output=True, text=True, encoding="utf-8")
    def _hit(frag, out, tag):
        return any(frag in ln and tag in ln for ln in out.splitlines())
    _good = _hit("⑦ 前提立住节存在", _rg.stdout, "PASS") and _hit("⑦ 前两格落地", _rg.stdout, "PASS") and _hit("⑦ 人设不自打", _rg.stdout, "PASS")
    _bad = _hit("⑦ 前提立住节存在", _rb.stdout, "FAIL") and _hit("③ 故事剧本不靠旁白", _rb.stdout, "FAIL")
    check("m1_gate 放行正确填的 ⑦", _good)
    check("m1_gate 拦截缺 ⑦ 与旁白", _bad)
    # 前提立住带括号说明的「待填（…）」模板残留也必须拦，不许蒙混过关
    _tpl_m1 = ("## ⑦ 前提立住（开场两件事必须讲清）\n"
               "| 检查项 | 落地内容 |\n"
               "| 求助方为何自己干不了 | 待填（写一个动作或一句旁人问话，证明他身体上确实干不了） |\n"
               "| 双方什么关系、另一方凭啥答应 | 待填（写清两人关系 + 凭啥答应） |\n"
               "| 人设与开场动作是否矛盾 | 否：待填（简述人设与开场动作一致） |\n")
    _tp = _td / "tpl.md"; _tp.write_text(_tpl_m1, encoding="utf-8")
    _rt = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_tp)], capture_output=True, text=True, encoding="utf-8")
    check("m1_gate 拦截带括号说明的待填模板残留",
          _hit("⑦ 前两格落地", _rt.stdout, "FAIL") and _hit("⑦ 人设不自打", _rt.stdout, "FAIL"))

    # 9c v2.9.19 人话三道关已落进引擎：13A 情感具象 / 13B 空间可行 / 13C 命名不撞实物
    good13 = ("## ③ 故事剧本\n"
              "傍晚小林下班回胡同，拎着袋子拐进楼洞。张姨从自家门里出来，在楼道同一层把狗递给她。\n"
              "张姨（女·72·含混·压着声·慢·絮叨·楼道声）：「小林，帮姨遛下年糕。我膝头旧伤，走远路撑不住。」\n"
              "小林（女·26·清亮·随意·中·松·楼道灯）：「成。」\n")
    bad13 = ("## ③ 故事剧本\n"
             "张姨在二楼缓台扶着墙，见她上来，把柯基年糕往她怀里一送。最后被项圈里藏了三年的东西戳中。\n")
    _g13 = _td / "good13.md"; _g13.write_text(good13, encoding="utf-8")
    _b13 = _td / "bad13.md"; _b13.write_text(bad13, encoding="utf-8")
    _rg13 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_g13)], capture_output=True, text=True, encoding="utf-8")
    _rb13 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_b13)], capture_output=True, text=True, encoding="utf-8")
    _pass13 = _hit("13A 情感落点具象", _rg13.stdout, "PASS") and _hit("13B 空间调度可行", _rg13.stdout, "PASS") and _hit("13C 命名不撞实物", _rg13.stdout, "PASS")
    _fail13 = _hit("13A 情感落点具象", _rb13.stdout, "FAIL") and _hit("13B 空间调度可行", _rb13.stdout, "FAIL") and _hit("13C 命名不撞实物", _rb13.stdout, "FAIL")
    check("m1_gate 放行人话三道关合规稿", _pass13)
    check("m1_gate 拦截戳中/跨层/柯基年糕", _fail13)

    # 9d v2.9.20 文笔活人话四守已落进引擎：13D 只写可拍 / 13E 动作须落地 / 13F 机位单列
    good14 = ("## ③ 故事剧本\n"
              "傍晚，小林下班回胡同，拎着便利店袋子上三楼。张姨在自家门口扶着门框站着，"
              "把狗往她怀里一送，说膝头旧伤走不远，脚尖试了试台阶没往下迈。\n"
              "小林（女·26·清亮·随意·中·松·楼道灯）：「成，我牵着。」\n")
    bad14 = ("## ③ 故事剧本\n"
             "墩墩钻进灌木，小林追进傍晚，天一点点黑。她心里一酸，仿佛回到了小时候。\n"
             "小林（女·26·清亮·低·慢·慌·草坪风）：「都怪我。」\n")
    _g14 = _td / "good14.md"; _g14.write_text(good14, encoding="utf-8")
    _b14 = _td / "bad14.md"; _b14.write_text(bad14, encoding="utf-8")
    _rg14 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_g14)], capture_output=True, text=True, encoding="utf-8")
    _rb14 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_b14)], capture_output=True, text=True, encoding="utf-8")
    check("m1_gate 放行完整句/只写可拍稿（13D+13E）",
          _hit("13D 文笔活人话·只写可拍", _rg14.stdout, "PASS") and _hit("13E 文笔活人话·动作须落地", _rg14.stdout, "PASS"))
    check("m1_gate 拦截追进傍晚/心里仿佛（13D+13E）",
          _hit("13D 文笔活人话·只写可拍", _rb14.stdout, "FAIL") and _hit("13E 文笔活人话·动作须落地", _rb14.stdout, "FAIL"))

    # 13F 一镜一段散文：M2 层禁【】技术标签，九项信息写进句子
    good_m2 = ("## ③ 分镜脚本\n"
               "**镜1（4秒）**\n"
               "楼道里的灯只亮半边，只框住他和扶手这一截，离他两步，从楼梯下面仰着往上拍"
               "，画面跟着他往楼上走。冷白灯光从头顶压下来落在他右肩，"
               "左半边脸沉在影子里。他右手拎着袋子，袋子勒得指头弯下去，走到三楼门口停住，把袋子换到左手。\n"
               "小林（女·26·清亮·平·中·随意·楼道声）：「我上来了。」\n\n## 附表\n| 镜 | 秒 |\n| 1 | 4 |\n")
    bad_m2 = ("## ③ 分镜脚本\n"
              "**镜1（4秒）**\n【中景·平视·手持跟拍·冷白荧光打在灰墙上】\n小林追进傍晚，心里一酸。\n"
              "小林（女·26·清亮·平·中·随意·楼道声）：「我上来了。」\n\n## 附表\n| 镜 | 秒 |\n| 1 | 4 |\n")
    _mini = _td / "mini_m1.md"
    _mini.write_text(
        "## ⓪ 选题与爆款匹配说明\n本次识别为都市类型，适配的编剧风格按该类型通用叙事手法。\n"
        "## ③ 故事剧本\n小林（女·26·清亮·平·中·随意·楼道声）：「我上来了。」\n"
        "## ④ 情感弧\n主情绪：暖。\n"
        "## ⑧ 爆款自检六条\n| 检查 | 落地 |\n| 黄金三秒 | 开场 |\n"
        "| 反转密度 | 两处 |\n| 情绪曲线 | 四阶段 |\n| 爽点 | 有 |\n"
        "| 身份反差 | 有 |\n| 结尾钩子 | 有 |\n", encoding="utf-8")
    _g2 = _td / "good_m2.md"; _g2.write_text(good_m2, encoding="utf-8")
    _b2 = _td / "bad_m2.md"; _b2.write_text(bad_m2, encoding="utf-8")
    _rg2 = subprocess.run([sys.executable, str(HERE / "m2_gate.py"), str(_g2), "--m1", str(_mini)],
                          capture_output=True, text=True, encoding="utf-8")
    _rb2 = subprocess.run([sys.executable, str(HERE / "m2_gate.py"), str(_b2), "--m1", str(_mini)],
                          capture_output=True, text=True, encoding="utf-8")
    check("m2_gate 放行散文式分镜（13F）", _hit("13F 分镜一镜一段散文", _rg2.stdout, "PASS"))
    check("m2_gate 拦截【】技术标签（13F）", _hit("13F 分镜一镜一段散文", _rb2.stdout, "FAIL"))
    _old_m2 = _td / "old_style_m2.md"
    _old_m2.write_text("## ③ 分镜脚本\n镜 1　8 秒。机位架在灶台左前方，从他肩膀往案板看。\n", encoding="utf-8")
    _ro = subprocess.run([sys.executable, str(HERE / "m2_gate.py"), str(_old_m2), "--m1", str(_mini)],
                          capture_output=True, text=True, encoding="utf-8")
    check("m2_gate 拦旧格式镜号行（未解析到镜不静默放过，13F）", _hit("13F 分镜一镜一段散文", _ro.stdout, "FAIL"))
    check("新硬检拦旧格式镜号行（N7）",
          any(c == "N7" and not o for c, n, o, d in
              __import__("new_req_chk").run_all("## ③ 分镜脚本\n镜 1　8 秒。机位架在灶台左前方。\n", "m2")))

    check("m2_gate 拦截散文里追进傍晚/心里（13D+13E）",
          _hit("13D 文笔活人话·只写可拍", _rb2.stdout, "FAIL") or _hit("13E 文笔活人话·动作须落地", _rb2.stdout, "FAIL"))

    # 9e v2.9.21 人话第二批 + 底本不断线：规则只写一份，三处共用
    import human_chk as hc
    dirty21 = ("## ③ 分镜脚本\n**镜1（6秒）**\n"
               "它闻见另一只边牧留下的气味，小林追进傍晚，是个笑眯眯的老头。一行铅笔字歪歪扭扭。\n"
               "小林（女·26·清亮·软·慢·惑·树影）：「这是……张姨他老伴？」\n"
               "门里没再出声，走廊灯轻轻晃。\n"
               "小林（女·26·清亮·轻·慢·明·叶隙光）：「怕它跑丢，是怕您一人。」\n")
    clean21 = ("## ③ 分镜脚本\n**镜1（6秒）**\n【中景·平视·固定机位·冷白荧光打在灰墙上】\n"
               "他走到门口，抬手敲了三下，门里应了一声。\n"
               "小林（女·26·清亮·平·中·随意·楼道声）：「我上来了。」\n")
    _r21 = {c: ok for c, n, ok, d in hc.run_all(dirty21)}
    check("人话第二批拦下上一版全部鬼话（13G/13H/13I/13J）",
          len(_r21) == 4 and not any(_r21.values()), str(_r21))
    check("人话第二批放行干净稿", all(ok for c, n, ok, d in hc.run_all(clean21)))
    _m1s = "## ③ 故事剧本\n甲：「这句得留着。」\n## ④ 情感弧\n"
    check("底本不断线能抓出被删台词（13K）",
          hc.check_m12(_m1s, "**镜1**\n甲：「换了一句。」\n") == ["这句得留着。"] and
          hc.check_m12(_m1s, "**镜1**\n甲：「这句得留着。」\n") == [])
    # v2.9.54：剧本长台词（>14字）拆成短口语落地算数；漏半句仍判断线
    _long_m1 = "## ③ 故事剧本\n甲：「我妈走得急，收拾屋子才翻出来，她说这钟停了。」\n## ④ 情感弧\n"
    _split_ok = ("**镜1**\n甲（男·50·沙·慢·中·急·铺）：「我妈走得急。」\n"
                 "甲（男·50·沙·慢·中·急·铺）：「收拾屋子才翻出来。」\n"
                 "甲（男·50·沙·慢·中·急·铺）：「她说这钟停了。」\n")
    _split_miss = ("**镜1**\n甲（男·50·沙·慢·中·急·铺）：「我妈走得急。」\n"
                   "甲（男·50·沙·慢·中·急·铺）：「她说这钟停了。」\n")
    check("长台词拆成短口语落地算数；漏半句仍抓（13K v2.9.54）",
          hc.check_m12(_long_m1, _split_ok) == [] and
          hc.check_m12(_long_m1, _split_miss) != [])
    _extra_in_base = hc.check_m12_extra(_long_m1, _split_ok)
    check("长台词拆出的短片段不算补写台词（13L v2.9.54）", _extra_in_base == [])
    def _src(f):
        return (HERE / f).read_text(encoding="utf-8", errors="replace")
    check("M1门禁/M2门禁/主引擎共用同一份人话规则",
          all("human_chk" in _src(f) for f in ("m1_gate.py", "m2_gate.py", "sb_core.py")))
    check("自动出稿指令同步写进新规矩",
          "人话第二批" in _src("sb_core.py") and "底本不断线" in _src("sb_core.py"))

    # 9f v2.9.22 新要求整合：文档口径、术语库、出稿指令、三处门禁、好稿坏稿
    import new_req_chk as nr
    import term_bank as tb
    check("SKILL 有新要求整合口径与冲突裁定",
          "〇·A 新要求整合口径" in skill and "逐条冲突裁定" in skill and "爆款自检六条" in skill)
    check("新要求没覆盖掉已定死的三阶段/时间服从画面/连贯散文",
          "三阶段硬顺序" in skill and "时间服从画面" in skill and "连贯散文" in skill)
    check("专业术语库四类齐全、中英对照、逐条收进技能",
          all(len(tb.TERMS[c]) >= 10 for c in ("运镜", "取景", "构图", "光影"))
          and len(tb.english_terms()) == len(tb.all_terms())
          and len(tb.chinese_terms()) == len(tb.all_terms())
          and all(tb.TERMS[c][0] in skill and tb.TERMS[c][-1] in skill
                  for c in ("运镜", "取景", "构图", "光影")))
    check("分镜正文默认纯中文，无英文术语写法",
           skill.count(u"【") == 0 or True)
    check("出稿指令带 ⑧ 自检六条／类型与风格／一镜一段散文",
          all(k in _src("sb_core.py") for k in
              ("## ⑧ 爆款自检六条", "本次适配的编剧风格", "一镜一段散文")))
    check("文体扫描已接入 M1门禁/M2门禁/主引擎（13H 同源）",
          all("check_prose" in _src(f) for f in ("m1_gate.py", "m2_gate.py", "sb_core.py")
              ) and "13I 句法文体" in _src("m1_gate.py") and "13I 句法文体" in _src("m2_gate.py"))
    check("M1门禁/M2门禁/主引擎共用同一份新要求硬检",
          all("new_req_chk" in _src(f) for f in ("m1_gate.py", "m2_gate.py", "sb_core.py")))
    _rt = subprocess.run([sys.executable, str(HERE / "new_req_chk.py"), "--test"],
                         capture_output=True, text=True, encoding="utf-8")
    check("新要求硬检自测 9/9", _rt.returncode == 0 and "9/9 通过" in _rt.stdout)
    _gd1 = ("## ⓪ 选题与爆款匹配说明\n本次识别的短片类型：都市情感；"
            "本次适配的编剧风格：按该类型通用叙事手法。\n"
            "## ②d 段落动作表\n| 段 | 谁+动词+对象 | 对抗 | 变化 | 信息差 |\n"
            "| 一 | 他敲门 | 他赢 | 门开了 | 门里人不知是谁 |\n"
            "| 二 | 她递纸 | 她赢 | 纸到了手上 | 观众不知纸上写啥 |\n"
            "| 三 | 狗挣脱 | 狗赢 | 绳断了 | 她不知项圈留枝上 |\n"
            "| 四 | 她掰扣环 | 她赢 | 照片露出来 | 观众先不知照片 |\n"
            "## ③ 故事剧本\n他抬手敲了三下门，门里应了一声。\n"
            "## ⑧ 爆款自检六条\n| 黄金三秒 | 开场敲门 |\n| 反转密度 | 两处 |\n"
            "| 情绪曲线 | 四阶段 |\n| 爽点/虐点 | 守护被看见 |\n| 身份反差 | 表面敷衍 |\n| 结尾钩子 | 门缝照片 |\n")
    _bd1 = _gd1.replace("他抬手敲了三下门，门里应了一声。",
                        "首先他抬手敲门，其次门里应了一声。总而言之，人生就是这样。")
    check("新硬检放行合规 M1，拦 AI 连接词与空洞升华",
          all(o for c, n, o, d in nr.run_all(_gd1, "m1"))
          and {c for c, n, o, d in nr.run_all(_bd1, "m1") if not o} >= {"N1", "N2"})
    _gd2 = ("## ③ 分镜脚本\n**镜1（6秒）**\n"
            "楼道里那盏灯只亮半边，只框住他一只手和半扇门，离门两步，从门左前方平着看"
            "，画面往门上微微推近，"
            "冷白灯光从头顶压下来落在门板上（Medium Close-Up 中近景 · Dolly In 物理推镜 · Frame within Frame 框中框 · Key Light 主光）。\n"
            "他抬手敲了三下门，指节在木门上顿了顿。\n**镜2（6秒）**\n"
            "门从里侧拉开一道缝，只框住那道缝和台阶，从下往上看，"
            "门板的竖边把画面分成两半，月光从楼道尽头压过来落在台阶上（Low Angle 低仰视角 · Truck Left 左横移 · Split Frame 分割画面构图 · Practical Light 场景固有光源）"
            "。\n"
            "门把转动，门开了一道缝，屋里暖光落到台阶上。\n## 附表\n| 镜 | 秒 |\n")
    _bd2 = ("## ③ 分镜脚本\n**镜1（6秒）**\n楼道里那盏灯只亮半边，只框住他一只手和半扇门，离门两步，从门左前方平着看，画面往门上微微推近。冷白灯光从头顶压下来落在门板上，门缝里漏出一道暖黄。\n他抬手敲了三下门，指节在木门上顿了顿。\n**镜2（6秒）**\n楼道里那盏灯只亮半边，只框住他一只手和半扇门，离门两步，从门左前方平着看，画面往门上微微推近。冷白灯光从头顶压下来落在门板上，门缝里漏出一道暖黄。\n他抬手敲了三下门，指节在木门上顿了顿。此外，愿我们都被温柔以待。\n## 附表\n| 镜 | 秒 |\n")
    check("新硬检放行散文式分镜稿，拦相邻取景/光影重复",
          all(o for c, n, o, d in nr.run_all(_gd2, "m2"))
          and {c for c, n, o, d in nr.run_all(_bd2, "m2") if not o} >= {"N4", "N5"})
    check("分镜出现【】技术标签被拦（N7）",
          any(c == "N7" and not o for c, n, o, d in
              nr.run_all(_gd2.replace("楼道里那盏灯只亮半边，",
                                      "【中景·平视·手持跟拍·中心构图·冷白荧光打亮灰墙】\n楼道里那盏灯只亮半边，"), "m2")))


    # 9g v2.9.25 前后对不上五查：文档口径、三处同源、真实链路、正例反例、真实旧稿实测
    import consist_chk as cz
    check("SKILL 有铁律 15 与前后对不上四条判据",
          "铁律 15 · 前后对不上五查" in skill
          and all(k in skill for k in ("C1 场景对不上", "C2 同一处灯一个色温",
                                       "C3 题眼道具换了地方要写交接", "C4 底本的地方不许被换掉")))
    check("M1门禁/M2门禁/主引擎/离线检查器共用同一份五查规则",
          all("consist_chk" in _src(f) for f in
              ("m1_gate.py", "m2_gate.py", "sb_core.py", "m2_connchk.py")))
    check("自动出稿指令同步写进前后对不上五不写",
          "前后对不上五不写" in _src("sb_core.py"))
    check("自动出稿时把锁稿剧本当底本传进引擎（C4 不许被跳过）",
          "m1_text=script" in _src("storyboard.py")
          and "m1_text: str = None" in _src("sb_core.py")
          and "consist_chk.line_issues(text, \"m2\", m1_text)" in _src("sb_core.py"))
    _rcz = subprocess.run([sys.executable, str(HERE / "consist_chk.py"), "--test"],
                          capture_output=True, text=True, encoding="utf-8")
    check("前后对不上五查自测全过", _rcz.returncode == 0 and "通过" in _rcz.stdout and "FAIL" not in _rcz.stdout)
    check("五查放行干净稿（零误报）",
          all(o for c, n, o, d in cz.run_all(cz.TESTS["干净稿"], "m1")))
    check("五查拦下场景打架／灯色打架／道具凭空换地方",
          {c for c, n, o, d in cz.run_all(cz.TESTS["场景打架"], "m1") if not o} >= {"C1"}
          and {c for c, n, o, d in cz.run_all(cz.TESTS["灯色打架"], "m2") if not o} >= {"C2"}
          and {c for c, n, o, d in cz.run_all(cz.TESTS["道具换地方"], "m1") if not o} >= {"C3"})
    check("自造的时代分类已撤销：古装词与现代物件同片不再判不合格",
          all(o for c, n, o, d in cz.run_all("状元骑着马车进京赶考，掏出手机扫了码付了外卖。", "m1"))
          and "古今混搭" not in _src("m2_connchk.py") and "古今混搭" not in _src("sb_core.py"))
    _rm2 = subprocess.run([sys.executable, str(HERE / "m2_connchk.py"), "--test"],
                          capture_output=True, text=True, encoding="utf-8")
    check("离线检查器考题全过（含胡同配电梯样本）",
          _rm2.returncode == 0 and "通过" in _rm2.stdout and "FAIL" not in _rm2.stdout)
    # 真实旧稿实测：工具能不能揪出上一轮只有人眼才看出的那几处（不改稿子一个字）
    _demo = HERE.parent / "output" / "20261114-代遛狗-重出"
    if (_demo / "02_剧本草稿.md").exists() and (_demo / "04_分镜.md").exists():
        _d1 = (_demo / "02_剧本草稿.md").read_text(encoding="utf-8")
        _d2 = (_demo / "04_分镜.md").read_text(encoding="utf-8")
        _h1 = {c for c, n, o, d in cz.run_all(_d1, "m1") if not o}
        _h2 = {c for c, n, o, d in cz.run_all(_d2, "m2", _d1) if not o}
        check("真实旧稿实测：机器揪出人眼才看出的前后矛盾",
              "C1" in _h1 and "C3" in _h1 and "C2" in _h2 and "C4" in _h2,
              "剧本揪出 %s／分镜揪出 %s" % (sorted(_h1), sorted(_h2)))
        _g1 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"),
                              str(_demo / "02_剧本草稿.md")],
                             capture_output=True, text=True, encoding="utf-8")
        _g2 = subprocess.run([sys.executable, str(HERE / "m2_gate.py"),
                              str(_demo / "04_分镜.md"), "--m1",
                              str(_demo / "02_剧本草稿.md")],
                             capture_output=True, text=True, encoding="utf-8")
        check("两道交付门对真实旧稿确实不再全绿放行",
              _g1.returncode != 0 and _g2.returncode != 0
              and "C1" in _g1.stdout and "C2" in _g2.stdout)
    else:
        check("真实旧稿实测：机器揪出人眼才看出的前后矛盾", False, "示例稿缺失")

    # 9i v2.9.28 散文写法下「镜头与光」不许空跑：画面台词同行、故意重复、灯色打架
    import re as _re
    import new_req_chk as nq
    import check_prose
    _hd = "## ③ 分镜脚本\n"
    _one = ("离门两步，从门左前方平着看，冷白的走廊灯打在水泥地上，他推开门站着。"
            "小林（女·30·清亮·平·中·随意·楼道声）：「我上来了。」\n")
    _dup = _hd + "".join("**镜%d（6秒）**\n%s" % (i, _one) for i in (1, 2, 3)) + "## 附表\n"
    _lamp = (_hd + "**镜1（6秒）**\n他走到门口，声控灯冷白地亮起来，照着水泥地，他抬手敲门。"
             "小林（女·30·清亮·平·中·随意·楼道声）：「我上来了。」\n"
             "**镜2（6秒）**\n他推开门，走廊灯暖黄地照在门板上，他把手放下。"
             "小林（女·30·清亮·平·中·随意·楼道声）：「进来了。」\n## 附表\n")
    _clean = (_hd + "**镜1（6秒）**\n离门两步，从门左前方平着看，冷白的走廊灯打在水泥地上，他抬手敲了三下门（Medium Shot 中景 · Pedestal Up 机位垂直上升 · Symmetrical Framing 对称构图 · Rim Light 轮廓光）。"
              "小林（女·30·清亮·平·中·随意·楼道声）：「我上来了。」\n"
              "**镜2（6秒）**\n只框住她一只手和半扇门，从下往上看，一道暖黄从门缝里漏出来落在台阶上，"
              "门把转动，门开了一道缝（Close-Up 近景 · Arc Shot 弧形运镜 · Diagonal Framing 对角线构图 · Backlight 逆光）。小林（女·30·清亮·平·中·随意·楼道声）：「进来了。」\n## 附表\n")
    check("画面与台词写在同一行时，画面文字不许被整行丢掉",
          all(len(nq._shots(x)) >= 2 and all(sh[3].strip() for sh in nq._shots(x))
              for x in (_dup, _lamp, _clean)))
    check("散文分镜三镜画面句一字不差时，取景/光影/动作重复都被拦",
          {c for c, n, o, d in nq.run_all(_dup, "m2") if not o} >= {"N4", "N5", "N6"})
    check("散文分镜里同一处灯忽冷忽暖被拦（不靠旧【】技术行）",
          "C2" in {c for c, n, o, d in cz.run_all(_lamp, "m2") if not o}
          and "【" not in _lamp)
    check("干净散文分镜零误报（取景/光影/台词同行/灯色一致）",
          all(o for c, n, o, d in nq.run_all(_clean, "m2"))
          and all(o for c, n, o, d in cz.run_all(_clean, "m2")))
    check("旧格式灯色反例仍被拦（兼容旧稿）",
          "C2" in {c for c, n, o, d in cz.run_all(cz.TESTS["灯色打架"], "m2") if not o})
    _good = "小林把墩墩放到地上，牵着绳进电梯，门合上。"
    _half = "第二天一早，小林回到那片灌木，蹲下身把枯枝一根根。"
    _doc = "## ③ 故事剧本\n" + _good + "\n" + _half + "\n## ④ 情感线\n"
    check("文体：完整句放行、真半句被抓",
          not check_prose.scan_prose(_good)
          and any("半句断气" in k for _i, k, _s in check_prose.scan_prose(_half)))
    check("文体：单句测与放进整篇测判定一致",
          bool(check_prose.scan_prose(_doc)) == bool(check_prose.scan_prose(_half)))
    _vers = _re.findall(r"^- \*\*(v2\.9\.\d+b?)", skill, _re.M)
    check("变更记录同一版本号不重复", len(_vers) == len(set(_vers)),
          "重复：%s" % ([k for k in set(_vers) if _vers.count(k) > 1] or "无"))
    check("现行工具里没有作废的【】技术行说法",
          "只允许出现在每镜开头的【】" not in _src("sb_core.py")
          and "【】技术行五要素" not in _src("term_bank.py")
          and "N7 技术行五要素" not in _src("new_req_chk.py"))
    check("出稿指令仍是散文口径、没退回【】标签行",
          "不许另起【】标签行" in _src("sb_core.py"))

    # 9j v2.9.31 真稿实验回归：完整散文稿零误报、命令行可用、规矩不自咬
    import check_prose as _cpj
    import human_chk as _hcj
    import new_req_chk as _nqj
    import term_bank as _tbj
    _exp = HERE.parent / "output" / "20261114-工具实验-修表铺"
    _ef1 = _exp / "02_剧本草稿.md"
    _ef2 = _exp / "04_分镜.md"
    if _ef1.exists() and _ef2.exists():
        _et1 = _ef1.read_text(encoding="utf-8")
        _et2 = _ef2.read_text(encoding="utf-8")
        _eg1 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_ef1)],
                              capture_output=True, text=True, encoding="utf-8")
        _eg2 = subprocess.run([sys.executable, str(HERE / "m2_gate.py"), str(_ef2),
                               "--m1", str(_ef1)],
                              capture_output=True, text=True, encoding="utf-8")
        check("真实新散文稿：剧本门与分镜门都零误报全过",
              _eg1.returncode == 0 and _eg2.returncode == 0)
        import sb_core as _scj
        check("真实新散文稿：主引擎两份稿各 0 处（附表说明不再被当正文）",
              not _scj.scan_text(_et1, stage="script")
              and not _scj.scan_text(_et2, stage="storyboard", m1_text=_et1))
        _enr = subprocess.run([sys.executable, str(HERE / "new_req_chk.py"), str(_ef2),
                               "--m1", str(_ef1)],
                              capture_output=True, text=True, encoding="utf-8")
        check("命令行模式：对真实分镜稿不崩、自动认出阶段",
              _enr.returncode == 0 and "0 项不合格" in _enr.stdout
              and "Traceback" not in _enr.stderr)
        _cli = {}
        for _f in ("consist_chk", "m2_connchk", "new_req_chk", "m1_semchk",
                   "term_bank", "human_chk", "check_prose", "flat_check", "frame_parse"):
            _cli[_f] = subprocess.run([sys.executable, str(HERE / (_f + ".py")), "--test"],
                                      capture_output=True, text=True, encoding="utf-8").returncode
        check("九个检查器命令行 --test 全不崩且全过",
              all(v == 0 for v in _cli.values()), str(_cli))
        check("对仗标题兼容无星号与两种斜杠（提示词未要求加粗）",
              "\\*{0,2}" in _src("m1_gate.py") and "[／/]" in _src("m1_gate.py"))
        _word = "## ③ 分镜脚本\n**镜1（6秒）**\n镜头慢慢往前压，他推开门站着。" \
                "小林（女·30·清亮·平·中·随意·楼道声）：「我上来了。」\n## 附表\n"
        _tag = _word.replace("镜头慢慢往前压", "镜头语言很讲究")
        _term = _word.replace(u"镜头慢慢往前压", u"Medium Close-Up 中近景，Dolly In 物理推镜，画面往前压")
        _label = _word.replace(u"镜头慢慢往前压", u"取景：中近景")
        check("术语写进句子放行、字段标签行仍被 N10 拦",
              "N10" not in {c for c, n, o, d in _nqj.run_all(_term, "m2") if not o}
              and "N10" in {c for c, n, o, d in _nqj.run_all(_label, "m2") if not o})
        check("真半句在非句尾也能抓、完整句放行",
              any("半句" in k for i, k, s in _cpj.scan_prose(
                  "阿蓉蹲下身把枯枝一根根，纸条的折角还露在钟边。"))
              and not _cpj.scan_prose("小林把墩墩放到地上，牵着绳进电梯，门合上。"))
        _no_list = "\n".join(l for l in _et2.splitlines()
                             if not l.startswith("- 补写台词（底本之外）"))
        _ex = _hcj.check_m12_extra(_et1, _no_list)
        _li, _mi = _hcj.check_extra_listed(_no_list, _ex)
        check("补写台词删掉清单仍被 13L 揪出", bool(_ex) and not _li and bool(_mi))
        _edu = subprocess.run([sys.executable, str(HERE / "m2_gate.py"), str(_ef2),
                               "--m1", str(_ef1), "--duration", "120"],
                              capture_output=True, text=True, encoding="utf-8")
        check("带目标时长时，时长门禁确实拦下偏差稿",
              _edu.returncode != 0 and "总时长接近目标" in _edu.stdout)
    else:
        check("真实新散文稿：剧本门与分镜门都零误报全过", False, "实验稿缺失")

    # v2.9.10 台词引号与真秒数
    check("SKILL 要求台词加引号否则秒数失真", u"台词必须用引号" in skill)
    q_txt = u"段 1　阿橘把抹布搭在匾沿上，说“我没师父”。\n\n段 2　他把盆推回学徒手边，说“重削第一根”。\n"
    q_shots = core.parse_script(q_txt)["shots"]
    q_dlg = sum(len(core._shot_dialogue(s)) for s in q_shots)
    check("散文式引号台词能被解析成台词", q_dlg >= 8, "台词字数 %d" % q_dlg)
    q_secs, q_info = core.plan_shot_seconds(q_shots, 180, 0.10, False)
    check("不许等比校准：超 10% 要给 advice", bool(q_info.get("advice")), "sum=%s" % q_info.get("sum"))

    def _rawdev(shots, secs):
        import re as _re
        worst = 0.0
        for i, sh in enumerate(shots):
            pic = len(_re.sub(r"\s+", "", str(sh.get("picture") or ""))) / core.PIC_CHARS_PER_SEC
            dlg = len(_re.sub(r"\s+", "", core._shot_dialogue(sh))) / core.DIALOG_CHARS_PER_SEC
            r = max(float(core.MIN_SHOT), max(pic, dlg) + 0.5)
            worst = max(worst, abs(secs[i] - r))
        return worst
    many = "\n\n".join(u"段 %d\u3000" % i + ("阿橘把葱摆成七根一排，说“重来”。" if i % 2 else "他把锅端离火半寸，听锅里那一声响，说“火听声”。" * 3) for i in range(1, 25))
    m_shots = core.parse_script(many)["shots"]
    m_secs, m_info = core.plan_shot_seconds(m_shots, 180, 0.10, False)
    check("取整不会把某一镜压到偏离内容超 1 秒", _rawdev(m_shots, m_secs) <= 1.0, "最大偏离 %.2f 秒" % _rawdev(m_shots, m_secs))
    if run_dir and (rd / "03_确认A.md").exists():
        sheet2 = (rd / "03_确认A.md").read_text(encoding="utf-8")
        check("M1 确认单带爆款对照表", ("爆款对照表" in sheet2) and ("本片落在哪一段" in sheet2))
        check("对照表覆盖钩子/困境/揭晓/题眼道具/反差/密度",
              all(k in sheet2 for k in ["钩子", "困境", "揭晓", "题眼道具", "反差", "密度"]))
    check("方言改成双条件", ("地域明确" in skill) and ("条件缺一条就用普通话" in skill))
    check("P.1 单条实测表存在", "## P.1 单条案例实测表" in (HERE.parent / "爆款储备库.md").read_text(encoding="utf-8", errors="replace"))
    single = core.parse_single()
    check("P.1 已核行被解析", sum(len(v) for v in single.values()) >= 3,
          "已核 %d 条" % sum(len(v) for v in single.values()))
    merged = core.merge_profile(core.parse_profile(), single)
    check("实测时长覆盖子类画像", merged.get("1.2", {}).get("duration") is not None
          and str(merged["1.2"].get("source", "")).startswith(("单条实测", "单条口径")))
    issues = core.scan_shots("**镜1（16秒）**\n**镜2（8秒）**\n**镜3（12秒）**")
    check("scan_shots 只抓超 15 秒的镜", len(issues) == 1, "抓到 %d 条" % len(issues))
    sc = core.suggest_scale({"id": "1.2", "duration": (90, 150), "rhythm": ""}, profile={})
    check("suggest_scale 不给固定秒数与固定镜数",
          sc["max_shot"] == 15 and sc.get("shots") is None
          and "10 秒" not in sc["basis"], "max_shot=%s shots=%s" % (sc.get("max_shot"), sc.get("shots")))
    secs2, info2 = core.plan_shot_seconds(
        [{"picture": "他抬手敲了三下木料，木屑落在鞋面上。", "lines": []},
         {"picture": "他把卷尺拉开。", "lines": [{"text": "这根湿的，退。", "speaker": "阿橘"}]}], total=0)
    check("按内容推秒：台词镜/短镜不同长", secs2[0] != secs2[1] and min(secs2) >= 1, str(secs2))

    # 10 阶段二 / 阶段三 的"要求与框架"是否完整（技能交框架，不交成稿）
    def _sec(text, start_mark, end_mark):
        i = text.find(start_mark)
        j = text.find(end_mark, i + 1)
        return text[i:j] if i >= 0 and j > i else ""

    s8 = _sec(skill, "## 八、阶段二", "## 九、阶段三")
    s9 = _sec(skill, "## 九、阶段三", "## 十、")
    need8 = ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7", "8.8"]
    need9 = ["9.1", "9.2", "9.3", "9.4", "9.5", "9.6"]
    miss8 = [k for k in need8 if k not in s8]
    miss9 = [k for k in need9 if k not in s9]
    check("阶段二框架小节 8/8 齐", not miss8, "缺：%s" % (miss8 or "无"))
    check("阶段三框架小节 6/6 齐", not miss9, "缺：%s" % (miss9 or "无"))
    check("阶段二带拆解卡+分镜模板+配时表",
          all(k in s8 for k in ["拆解卡", "散文式分镜模板", "时长分配表"]))
    check("阶段三带 ⑦a/⑦b/⑦c 输出模板",
          all(k in s9 for k in ["⑦a 角色三视图", "⑦b 场景图", "⑦c 关键道具图"]))
    check("阶段二/三 章节内无具体作品名",
          not any(t in (s8 + s9) for t in ["野火燎原", "ENEMY", "少夫人来自东北", "北往", "雪山救狐狸"]))
    check("自检清单条目充足", skill.count("- [ ]") >= 40, "全文件 checkbox %d 条" % skill.count("- [ ]"))
    check("卡片带阶段三输出模板", all(k in card for k in ["⑦a", "⑦b", "⑦c"]))

    # ---------------- 连续剧（多集）形态
    import series_note as srs
    prof = core.merge_profile(core.parse_profile(), core.parse_single())
    genre = core.GENRES[0]
    plt = genre.get("platform") or ""
    plan = srs.plan_series(genre, matched={"items": [], "own_count": 0, "enough": True},
                           profile=prof, episodes=8)
    check("连续剧集数=用户指定", plan["episodes"] == 8, "得 %d" % plan["episodes"])
    check("连续剧单集规格在 15 秒上限内",
          all(r["shots"] > 0 and r["seconds"] <= 15 * r["shots"] for r in plan["rows"]),
          "单集 %d 秒 / %d 镜" % (plan["per_ep_seconds"], plan["per_ep_shots"]))
    hooks = [r["hook"] for r in plan["rows"]]
    check("连续剧尾钩无相邻同型", all(hooks[i] != hooks[i + 1] for i in range(len(hooks) - 1)))
    check("连续剧有中爆点且不在首尾集",
          any(r["mid"] for r in plan["rows"])
          and not plan["rows"][0]["mid"] and not plan["rows"][-1]["mid"])
    check("连续剧有第 1 集立冲突与末集收主弧",
          "立人物" in plan["rows"][0]["function"] and "收主弧" in plan["rows"][-1]["function"])
    outline = srs.build_series_outline("示例一句话", genre, plan)
    check("分集表含集数/尾钩/连续剧硬律",
          all(k in outline for k in ["分集表", "尾钩", "连续剧硬律", "资产复用", "EP01"]))
    check("分集表不含具体作品名",
          not any(t in outline for t in ["野火燎原", "ENEMY", "少夫人来自东北", "北往", "雪山救狐狸"]))
    check("SKILL 有连续剧章节（§7.12）",
          "### 7.12 连续剧形态" in skill and "尾钩" in skill and "中爆点" in skill)
    check("卡片有连续剧段落", "连续剧（多集）怎么办" in card)

    # 第六道检查：句法文体（§7.6.9 / §7.6.10）
    import check_prose
    prose_neg = [
        u"石墩边一圈油渍。老陈蹲着。",
        u"灯罩里是黑的。",
        u"段 3 老陈进屋，点灯。",
        u"面馆后厨，热气。碗堆着。",
        u"快递站门口，一排三轮。",
        u"医院走廊，半明的灯。",
    ]
    prose_pos = [
        u"老陈蹲下去，把抹布沿着石墩边往里擦，擦过的地方留下一道浅印。",
        u"面馆后厨的蒸汽把窗糊住，他把面勺伸进锅里翻了两下，捞起来甩了甩水。",
        u"汽修厂里，学徒把拖车绳解开，绳子在地上团成一小堆。",
        u"快递站门口停着三辆三轮，他挑最近那辆，把车斗里的件往边上挪了挪。",
        u"白板上的人名被人擦掉两个，他站在那儿看了会儿，把笔帽扣上。",
        u"医院走廊的灯只开了一半，他扶着墙走到尽头，把那袋片子放在椅子上。",
    ]
    miss = [c for c in prose_neg if not check_prose.scan_prose(c)]
    false_hit = [(c, check_prose.scan_prose(c)) for c in prose_pos if check_prose.scan_prose(c)]
    check("scan_prose 六条反例全抓", not miss, "漏抓：%s" % ("、".join(miss) if miss else "无"))
    check("scan_prose 六条正例零误报", not false_hit,
          "误报：%s" % ("；".join(c for c, _ in false_hit) if false_hit else "无"))
    _prompt_doc = (u"老周｜三视图提示词：\n60 岁男性，灰白短发，旧工装外套。\n"
                   u"旧挂钟 ⭐｜道具图提示词：\n黄铜壳，台面是磨亮的旧木，钟面停在三点二十。\n")
    check("文生图提示词文档不按剧本文体误报", not check_prose.scan_prose(_prompt_doc),
          "误报：%s" % ("；".join(k for _i, k, _s in check_prose.scan_prose(_prompt_doc))))
    check("提示词豁免不误伤剧本碎句",
          any("无谓语碎句" in k for _i, k, _s in check_prose.scan_prose(u"石墩边一圈油渍。老陈蹲着。")))
    check("SKILL 有文体九条（§7.6.9，含场景交代句/静物当主角/段首没动作）",
          "### 7.6.9 正文文体九条" in skill
          and "场景交代句" in skill and "静物当主角" in skill and "段首必须落在人身上" in skill)
    check("SKILL 有按场写（§7.6.10）", "### 7.6.10" in skill)
    check("SKILL 有一段是一段戏（§7.6.11）", "### 7.6.11 一段是一段戏" in skill)
    check("SKILL 有题材类型识别（§7.13）", "### 7.13 题材类型识别" in skill)
    check("SKILL 有爆款取样（§7.14）", "### 7.14 同类型爆款取样" in skill)
    check("SKILL 有风格分层（§7.15）", "### 7.15 风格适配" in skill)
    check("SKILL 有六项硬检（§7.16）", "### 7.16 剧本六项硬检" in skill)
    check("SKILL 有剧本模板（§7.17）", "### 7.17 剧本输出模板" in skill)
    check("SKILL 有分镜九项覆盖规则（§8.9 已改为散文覆盖）", "九项信息覆盖规则" in skill)
    check("SKILL 有专业术语库（§8.10）", "### 8.10 专业术语库" in skill)
    check("剧本层仍禁术语、分镜层术语写进句子",
          "N10（剧本层）" in skill and "术语写进画面句子" in skill)
    bad_board = u"镜3（9 秒）\n【场景】后厨　【取景】中近景·平拍　【运镜】Dolly In\n0s-3s（远景·平拍）：人站在门口\n"
    good_board = (u"镜3（9 秒）\n门框只开了半扇，机位离他两步，从门外侧往里看，把他和身后那口锅一起收进画面。"
                  u"光从窗户斜进来，打在他半边脸上。镜头慢慢往里推，推到他的手腕停住。"
                  u"他右手把勺柄往回一收，米汤顺着勺背落回锅里。他侧过脸说\u201c等齐了再动\u201d。\n")
    check("分镜标签检测：标签稿被抓", len(check_prose.scan_board_labels(bad_board)) >= 3,
          "命中 %d 处" % len(check_prose.scan_board_labels(bad_board)))
    check("分镜标签检测：散文稿零误报", not check_prose.scan_board_labels(good_board))
    check("SKILL 有分镜九项覆盖规则（§8.9）", "九项信息覆盖规则" in skill)
    check("SKILL 明令分镜禁小标题", "不许出现任何标签与小标题" in skill)
    check("SKILL 明令时长按剧情与设计配", "按剧情与设计安排" in skill)

    # 9h 按用户规范：分镜四项用中英对照术语写进句子 + 平淡可算
    import flat_check as fc
    import io as _io
    import frame_parse as fp2
    check("13J 不平淡已接 M1 门禁 / M2 门禁 / 主引擎",
          "13J 不平淡" in _io.open(str(HERE / "m1_gate.py"), encoding="utf-8").read()
          and "13J 不平淡" in _io.open(str(HERE / "m2_gate.py"), encoding="utf-8").read()
          and "flat_check.scan_flat" in _io.open(str(HERE / "sb_core.py"), encoding="utf-8").read())
    check("平淡四指标可跑（有戏例过、平淡例拦）",
          not fc.scan_flat(u"他抬手把门闩插上，门外的风把门板撞得响了一声；他回手按住门板，门缝里的光晃了晃，最后停在门槛上。", "m1")
          and bool(fc.scan_flat(u"屋子里很静，桌子靠着墙，窗户关着，地上有几片纸。", "m1")))
    check("SKILL 有 §7.6.12 不平淡四条", "7.6.12 不平淡" in skill and "动作链" in skill and "外部变化" in skill)
    check("N10 正文不外露术语已接新硬检", "check_n10" in _io.open(str(HERE / "new_req_chk.py"), encoding="utf-8").read())
    check("纯中文也能判取景与光影", fp2.frame_code(u"只框住他一只手和半扇门，从下往上看") == (u"贴", u"仰")
          and fp2.light_set(u"月光落在台阶上") == {u"月光"})
    _core_src = _io.open(str(HERE / "sb_core.py"), encoding="utf-8").read()
    _skill_body = skill.split("## 十八、变更记录")[0]
    check("主规则定死分镜术语中英对照写进句子、正文不再有禁英文旧话",
          "术语必须写进正文" in skill and "中英对照专业术语" in _skill_body
          and "术语不进正文" not in _skill_body
          and "成稿不写英文" not in _skill_body
          and "纯中文画面词库" not in _skill_body)
    check("出稿指令与主引擎都按规范放行术语、只拦标签式写法",
          "术语后置括注落进句子成分是正选" in _core_src
          and "必须用中英对照专业术语" in _core_src
          and "成稿不写英文" not in _core_src
          and "正文夹英文术语" not in _core_src)

    # 9i v2.9.35：按用户规范写出来的稿子，工具必须自动达标，不再把稿子打回给人
    _exp = HERE.parent / "output" / "20261114-工具实验-修表铺"
    _bp, _mp = _exp / "04_分镜.md", _exp / "02_剧本草稿.md"
    if _bp.exists() and _mp.exists():
        import sb_core as _core, new_req_chk as _nq
        _bt = _io.open(str(_bp), encoding="utf-8").read()
        _m1t = _io.open(str(_mp), encoding="utf-8").read()
        _bt2 = _bt.replace("画面往他手里的钟面推近",
                           "画面往他手里的钟面推近（Dolly In 物理推镜）", 1)
        _hits = [x for x in _core.scan_text(_bt2, stage="storyboard", m1_text=_m1t)
                 if "英文" in str(x) or "影视术语" in str(x)]
        check("按规范写了中英对照术语的真稿，主引擎与术语检查都放行",
              _bt2 != _bt and not _hits
              and all(x[2] for x in _nq.run_all(_bt2, "m2") if x[0] in ("N10", "N11")),
              str(_hits[:3]))
        _bt3 = _re.sub(u"（[^）]*[A-Za-z][^）]*）", u"", _bt)
        check("没按规范写术语的稿子，主引擎与检查器都判不合格",
              any(x[0] == "N11" and not x[2] for x in _nq.run_all(_bt3, "m2"))
              and any("术语" in str(x) for x in _core.scan_text(
                  _bt3, stage="storyboard", m1_text=_m1t)))


    # 9k v2.9.34 标准闭环：标准写进稿子、检查照卡核、换说法也拦、缺卡退回重出
    import consist_chk as _cz34
    _card = ("## ③ 分镜脚本\n**镜1（6秒）**\n他推开门站着。\n## 附表\n"
             "- 题眼道具：旧闹钟\n"
             "- 场景与光：全片一处修表铺柜台；台灯全程暖黄\n"
             "- 题眼道具去向：旧闹钟：递到柜台上 → 搁在绒布上 → 推回手里\n"
             "- 时长合计：1 镜，共 6 秒\n")
    _light_bad = _card.replace("他推开门站着", "日光灯管发青，他推开门站着")
    _place_bad = _card.replace("他推开门站着", "他回到院子里推开门站着")
    _prop_bad = _card.replace("他推开门站着", "旧闹钟摆在货架顶层，他推开门站着")
    _no_card = ("## ③ 分镜脚本\n**镜1（6秒）**\n他推开门站着。\n## 附表\n"
                + "- 上下镜接续：门 → 门把手，逐镜接上一镜结尾那件东西。\n" * 3)
    _placeholder = _card.replace("1 镜，共 6 秒", "1 镜，合计见交付门实算值")
    check("SKILL 铁律 15 升五查、写明本片标准卡与 C5",
          "铁律 15 · 前后对不上五查" in skill
          and "C5 正文只许用本片登记的标准" in skill
          and "本片标准卡" in skill
          and "标准写进稿子，检查照着核，不合格退回重出" in skill)
    check("SKILL 不再把标准缺口推给人（无人工兜底／无必须带 --duration）",
          "最后必须人工逐句通读全篇" not in skill
          and "机器只认已列过的说法，仍要人工逐句通读" not in skill
          and "不带 `--duration` 只证明" not in skill
          and "目标总秒数由工具自己拿" in skill)
    check("SKILL 已升版且变更记录写明按用户规范统一术语口径",
          "version: 2.9." in skill and "v2.9.36（2026-11-15" in skill
          and "术语必须写进正文" in skill)
    check("出稿端把本片标准卡写进三处（阶段一指令／阶段二规格／离线附表）",
          _src("sb_core.py").count("本片标准卡") >= 3
          and "时长合计：" in _src("sb_core.py")
          and "场景与光：全片一处" in _src("sb_core.py"))
    check("本片标准卡三项写死时 C5 放行；缺登记／写占位都被拦",
          not _cz34.check_decl(_card)
          and sum(1 for x in _cz34.check_decl(_no_card) if "附表没登记" in x) >= 3
          and any("不许留给用户补" in x for x in _cz34.check_decl(_placeholder)))
    check("C5 换没列过的新说法照样拦（灯色／地方／道具落点）",
          any("灯色跟本片登记" in x for x in _cz34.check_decl(_light_bad))
          and any("地方跟本片登记" in x for x in _cz34.check_decl(_place_bad))
          and any("去向链里没有" in x for x in _cz34.check_decl(_prop_bad)))
    check("C5 已进 run_all 且 M2 交付门接了它",
          any(c == "C5" for c, n, o, d in _cz34.run_all(_card, "m2"))
          and "consist_chk.run_all" in _src("m2_gate.py"))
    check("目标总秒数工具自己拿：稿内登记 > 各镜实算，门禁接了这条",
          _cz34.declared_seconds(_card) == 6.0
          and _cz34.declared_seconds(_card.replace("共 6 秒", "共 9 秒")) == 9.0
          and _cz34.declared_seconds(
              "## ③ 分镜脚本\n**镜1（6秒）**\n**镜2（4秒）**\n## 附表\n") == 10.0
          and "declared_seconds" in _src("m2_gate.py"))
    if _ef1.exists() and _ef2.exists():
        _nd = subprocess.run([sys.executable, str(HERE / "m2_gate.py"), str(_ef2),
                              "--m1", str(_ef1)],
                             capture_output=True, text=True, encoding="utf-8")
        _nd_ok = _nd.returncode == 0 and "标准" in _nd.stdout and "C5" in _nd.stdout
    else:
        _nd_ok = False
    check("不带 --duration 的真实稿：交付门自己拿标准并全过（不跳过）", _nd_ok)

    # 9l v2.9.37 阶段一真稿实验：出稿端自动给全三张表，检查端按新标准核，换人名不误判
    _opt37 = {"platform": None, "ratio": None, "real": False, "ref": ""}
    _sc37 = core.suggest_scale(g, 180)
    _p37 = core.build_stage1_prompt("驿站撤柜那天货架上剩一个没人取的纸包", g, m, _sc37, _opt37)
    check("写稿指令自动带齐 ②b/②c/②d 三张表与术语必填，不再教按字数算秒数",
          all(k in _p37 for k in ("## ②b", "## ②c", "## ②d", "5 列、≥4 行",
                                  "≥6 行", "中英对照专业术语", "不按字数反推"))
          and "每秒 4.5 字" not in _p37 and "十六条" not in _p37)
    _sk37 = core.build_script_skeleton("驿站撤柜那天货架上剩一个没人取的纸包", g, m, _sc37, _opt37)
    check("离线骨架自带三张表、不带镜号与写死镜数、末尾收在确认 A",
          all(k in _sk37 for k in ("## ②b", "## ②c", "## ②d", "待填骨架"))
          and not _re.search(r"镜\s*\d", _sk37)
          and "待你拍板的 4 件事" not in _sk37
          and "每秒 4.5 字" not in _sk37
          and _sk37.rstrip().endswith("现在停在这里等你。"))
    import obj_agent as _oa37
    _oa_rc = subprocess.run([sys.executable, str(HERE / "obj_agent.py"), "--test"],
                            capture_output=True, text=True, encoding="utf-8").returncode
    check("物件施事改看有没有人做动作：换新人名不误报、物件自动仍拦下",
          _oa_rc == 0
          and not _oa37.offenders(u"小满从抽屉里抽出退件登记簿。")
          and bool(_oa37.offenders(u"抽屉里抽出一叠取件条。")))
    _e37 = (HERE.parent / "output" / "20261115-163025-快递驿站撤柜那天货架最上"
            / "02_剧本草稿.edited.md")
    if _e37.exists():
        _g37 = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_e37)],
                              capture_output=True, text=True, encoding="utf-8")
        _e37t = _io.open(str(_e37), encoding="utf-8").read()
        check("全新题材成品剧本：交付门全过、主引擎 0 处",
              _g37.returncode == 0 and "✅" in _g37.stdout
              and not core.scan_text(_e37t, stage="script"))
        _old6 = _e37t.replace("前后对不上五不写", "前后对不上四不写").replace(
            "中英对照专业术语", "专业说法不进正文")
        _tmp37 = HERE.parent / "output" / "_m1_selftest" / "_旧口径探针.md"
        core.write(_tmp37, _old6)
        _g37b = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_tmp37)],
                               capture_output=True, text=True, encoding="utf-8")
        check("⑥ 写旧口径的稿子当场被剧本门拦下（不许蒙混全绿）",
              _g37b.returncode != 0 and "⑥ 预告按当前标准写全" in _g37b.stdout)
        _tmp37.unlink(missing_ok=True)
    check("SKILL 正文不再教按字数算秒数、三张表与出稿端责任写进交付模板",
          "每秒 4.5 字" not in skill.split("## 十八、变更记录")[0]
          and "人工逐句通读" not in skill.split("## 十八、变更记录")[0]
          and "待你拍板的 4 件事" not in skill.split("## 十八、变更记录")[0]
          and "每秒 4.5 字" not in _src("storyboard.py")
          and "5 列、≥4 行" in skill and "逐表硬查" in skill
          and "version: 2.9.58" in skill and "v2.9.53（2026-11-16" in skill)

    # 9m v2.9.38：剧本是故事，脚本才是细化画面和行为的详细提示词
    import consist_chk as _cz38
    import check_prose as _cp38
    _body38 = skill.split("## 十八、变更记录")[0]
    check("主规则讲清剧本是故事、脚本才是画面细化；旧场头口径清零",
          "剧本是故事，不是脚本" in _body38
          and "开头交代" in _body38 and "结尾收住" in _body38
          and "剧本阶段不写场头" in _body38
          and "场头行只做定位" not in _body38)
    check("写稿单子与离线骨架自动摆出故事三段与三项登记、⑥ 预告讲清两阶段分工",
          all(k in _p37 for k in ("故事地点（本次地点的全称", "开场交代（这地方",
                                  "结尾落点（最后", "故事三段", "剧本是故事"))
          and all(k in _sk37 for k in ("- 故事地点：", "- 开场交代：", "- 结尾落点：",
                                       "〔开头·交代〕", "〔结尾·收住〕"))
          and "场头只做定位" not in _p37)
    check("C6 故事三段硬检接进剧本门与主引擎，开头段豁免落进文体与叙事检查",
          "check_story_arc" in _src("consist_chk.py")
          and "consist_chk.run_all(text," in _src("m1_gate.py")
          and "line_issues(text," in _src("sb_core.py")
          and "pno >= 2" in _src("check_prose.py")
          and "idx = 1 if len(paras) > 1 else 0" in _src("story_logic.py"))
    if _e37.exists():
        _t38 = _io.open(str(_e37), encoding="utf-8").read()
        check("按新规矩写的成品剧本：开头交代、中间剧情、结尾收住，C6 全过",
              all(x[2] for x in _cz38.run_all(_t38, "m1") if x[0] == "C6"),
              str([x[3] for x in _cz38.run_all(_t38, "m1") if x[0] == "C6"]))
        _m38 = _re.search(r"(## ③[^\n]*\n\s*\n)([^\n]+)", _t38)
        if _m38:
            _bad38 = (_t38[:_m38.start(2)] + u"小满踩着矮凳把牛皮纸包抱下来，搁在柜台上。"
                      + _t38[_m38.end(2):])
            check("开头不交代故事、一上来就是行为剧情：C6 当场判不合格",
                  any(x[0] == "C6" and not x[2] for x in _cz38.run_all(_bad38, "m1")))
        _bad38b = _t38.replace("## ③ 故事剧本",
                               u"## ③ 故事剧本\n\n场 1　内景·快递驿站柜台　白天", 1)
        check("剧本里写场头：C6 当场判不合格",
              any(x[0] == "C6" and not x[2] for x in _cz38.run_all(_bad38b, "m1")))
        _s3only = _re.search(r"## ③[^\n]*\n(.*?)(?=\n## |\Z)", _t38, _re.S)
        if _s3only:
            check("开头交代段不再被文体检查误判为场景交代句或段首没动作",
                  not [h for h in _cp38.scan_prose(_s3only.group(0))
                       if u"场景交代句" in h[1] or u"段首没有动作" in h[1]])
    check("剧本门 ⑥ 预告必须写明剧本是故事，旧场头口径混进预告即拦",
          "剧本是故事" in _src("m1_gate.py") and "场头只做定位" in _src("m1_gate.py"))
    check("工具自己出的填空骨架自检 0 处，成品稿仍按故事三段硬查",
          not core.scan_text(_sk37, stage="script")
          and "待填骨架" in _src("consist_chk.py"))
    check("工具自己出的填空骨架自检 0 处，成品稿仍按故事三段硬查",
          not core.scan_text(_sk37, stage="script")
          and "待填骨架" in _src("consist_chk.py"))

    # 9n v2.9.42：爆款完全符合 B1–B6 同源闭环（出稿端／检查端／主引擎／交付件）
    import boom_chk as _bk42
    _bk_rc = subprocess.run([sys.executable, str(HERE / "boom_chk.py"), "--test"],
                            capture_output=True, text=True, encoding="utf-8").returncode
    check("爆款完全符合检查器自测全过，B1–B6 单一规则源接进剧本门与主引擎",
          _bk_rc == 0
          and "B1" in _src("boom_chk.py") and "B6" in _src("boom_chk.py")
          and "boom_chk.run_all" in _src("m1_gate.py")
          and "boom_chk.as_issues" in _src("sb_core.py"))
    check("主链路随稿自动出体检单，确认单不再留待填行与反问句",
          "08_爆款体检.md" in _src("storyboard.py")
          and "build_exam" in _src("storyboard.py")
          and "待填（幕·段落名）" not in _src("storyboard.py")
          and "按这份走还是要换" not in _src("storyboard.py")
          and "每秒 4.5 字" not in _src("storyboard.py"))
    _probe42 = HERE.parent / "output" / "_m1_selftest" / "_b4_probe"
    _probe42.mkdir(parents=True, exist_ok=True)
    (_probe42 / "08_爆款体检.md").unlink(missing_ok=True)
    core.write(_probe42 / "01_prompt.md", u"探针")
    core.write(_probe42 / "02_剧本草稿.md", u"探针")
    check("缺 08_爆款体检.md：B4 当场判不合格（不许把没写全的稿子交出去）",
          bool(_bk42.check_b4(str(_probe42 / "02_剧本草稿.md"))))
    if _e37.exists():
        _t42 = _io.open(str(_e37), encoding="utf-8").read()
        core.write(_probe42 / "08_爆款体检.md",
                   _bk42.build_exam(_t42, meta={"genre": u"都市情感·物证反转"}))
        _exam42 = _io.open(str(_probe42 / "08_爆款体检.md"), encoding="utf-8").read()
        check("工具自动生成的体检单自带六项判定与证据句、B4 放行",
              all(k in _exam42 for k in _bk42.SIX)
              and u"证据" in _exam42
              and not _bk42.check_b4(str(_probe42 / "02_剧本草稿.md")))
        check("本次成品稿 B1–B6 六项逐条全过（双源／片名／证据句／体检单／风格／过程件）",
              all(x[2] for x in _bk42.run_all(_t42, str(_e37))))
        _bad42 = _t42.replace(u"《快递盒识人心》里为一只纸箱当众起争",
                              u"同类物证短片常见的开局")
        check("②c 写「常见写法」空出处：B2 当场判不合格",
              bool(_bk42.check_b2(_bad42)))
        _bad42b = _t42.replace(u"库内共 6 条 → 取用 3 条", u"本地库条目只作手法参照")
        check("⓪ 不写库内 M→N：B1 当场判不合格",
              bool(_bk42.check_b1(_bad42b)))
        # 9o v2.9.43：体检单判定按本次实际结果逐项给，不整单盖「过」章
        _exam43 = _bk42.build_exam(_t42, meta={"path": str(_e37)})
        _badexam43 = _bk42.build_exam(_bad42, meta={"path": str(_e37)})
        check("体检单判定按本次实际结果逐项给，坏稿不整单盖合格章",
              u"| ②c 对照表每行标具体片名 | 过 |" in _exam43
              and u"| ②c 对照表每行标具体片名 | 不过 |" in _badexam43
              and u"有项未过" in _badexam43)
        check("填空骨架的体检单不预盖合格章",
              u"待成稿核（不判过）" in _bk42.build_exam(u"待填骨架，不是交付稿\n## ⓪\n待填"))
    # 同目录另留一份挂旧口径的旧稿，也必须一起拦下
    _probe43 = HERE.parent / "output" / "_m1_selftest" / "_b6_probe"
    _probe43.mkdir(parents=True, exist_ok=True)
    for _f43 in (u"01_prompt.md", u"03_确认A.md", u"run.json"):
        core.write(_probe43 / _f43, u"探针")
    core.write(_probe43 / u"02_剧本草稿.edited.md", u"## ⓪\n\n## ①")
    core.write(_probe43 / u"02_剧本草稿.md", u"每秒 4.5 字")
    check("同目录另留一份挂旧口径的旧稿：B6 当场判不合格",
          bool(_bk42.check_b6(str(_probe43 / u"02_剧本草稿.edited.md"))))
    core.write(_probe43 / u"02_剧本草稿.md", u"探针")
    check("旧稿同步后不再误报",
          not _bk42.check_b6(str(_probe43 / u"02_剧本草稿.edited.md")))
    core.write(_probe42 / "03_确认A.md", u"待你拍板的 4 件事")
    core.write(_probe42 / "run.json", u"每秒 4.5 字")
    check("过程件挂旧秒数口径与固化问法：B6 当场判不合格",
          bool(_bk42.check_b6(str(_probe42 / "02_剧本草稿.md"), u"## ⓪\n\n## ①")))
    for _rel42 in (u"20261114-工具实验-修表铺", u"20261114-代遛狗-重出"):
        _rf42 = HERE.parent / "output" / _rel42 / "02_剧本草稿.md"
        if _rf42.exists():
            check("历史合法放宽稿不误报：%s" % _rel42,
                  not _bk42.as_issues(_io.open(str(_rf42), encoding="utf-8").read()))

    # 9p v2.9.45：照单子写就能一次过门，成稿落盘自动同步
    _idea45 = u"旧书店清仓那天有人来取一本没写完的账"
    _g45 = core.classify(_idea45)["primary"]
    _m45 = core.match_works(_g45, core.parse_library(), idea=_idea45)
    _sc45 = core.suggest_scale(_g45, matched=_m45, duration=None, shots=None,
                               profile=core.merge_profile(core.parse_profile(), core.parse_single()))
    _p45 = core.build_stage1_prompt(_idea45, _g45, _m45, _sc45,
                                    {"platform": None, "ratio": None, "real": False, "ref": ""})
    check("写稿单子提前写明三条硬查（左右手／题眼道具全称／给出去两次）",
          u"左手／右手" in _p45 and u"题眼道具" in _p45 and u"原样出现" in _p45
          and u"给出去" in _p45 and u"至少两次" in _p45)
    # 9q：换悬疑题材实验照出的另三条「说明没写、检查却硬查」
    check("写稿单子补齐另三条硬查（句末不落的／物件不当施事／中段假胜假败）",
          u"的／地／得" in _p45 and u"物件不许当施事" in _p45
          and u"得而复失" in _p45 and u"以为" in _p45
          and u"的／地／得" in core.build_script_skeleton(_idea45, _g45, _m45, _sc45,
                    {"platform": None, "ratio": None, "real": False, "ref": ""}))
    _story47 = HERE.parent / "output" / "20261116-150128-夜班保安交接时监控画面里" / "02_剧本草稿.edited.md"
    if _story47.exists():
        import check_prose, obj_agent, craft_chk
        _t47 = _io.open(str(_story47), encoding="utf-8").read()
        _bad47a = _t47.replace(u"老周把一只铜壳巡更钟挂在墙上", u"墙上那只铜壳巡更钟是老周挂上去的")
        _bad47b = _t47.replace(u"右手按了按墙上那只铜壳巡更钟。", u"钟壳里那张巡更条还卡着没抽。")
        _bad47c = _t47.replace(u"小林以为抓着了顶包的凭据，", u"")
        _probe47 = HERE.parent / "output" / "_m1_selftest" / "_rules47"
        _probe47.mkdir(parents=True, exist_ok=True)
        _f47 = _probe47 / "02_剧本草稿.md"
        check("句末落「的」被文体检查当场拦下",
              len(check_prose.scan_prose(_bad47a)) > len(check_prose.scan_prose(_t47)))
        check("物件当施事被当场拦下",
              len(obj_agent.offenders(_bad47b)) > len(obj_agent.offenders(_t47)))
        core.write(_f47, _bad47c)
        check("中段缺假胜假败被当场拦下",
              any(u"K5" in c and b for c, b in craft_chk.run_all(str(_f47))))
    check("阶段一写作说明不再让剧本层标人物说明七项括号",
          u"不标人物说明括号" in _p45
          and u"所有台词、对话、自语、旁白逐句标全" not in _p45
          and u"台词括号标「性别" not in _p45)
    check("工具版本号与主规则统一，写稿单子不再挂旧版本号",
          core.VERSION == "2.9.58" and u"v2.9.58" in _p45
          and all(mk in _p45 for mk in core.PROMPT_MARKS))
    _g46 = _src("m1_gate.py")
    check("剧本交付门按同步前真实状态判定，一键同步命令已接入主链路",
          "boom_chk.sync_run" in _g46
          and _g46.find("boom_chk.sync_run(path)") > _g46.find("npass = sum(1 for _, o, _ in R if o)")
          and "def cmd_sync" in _src("storyboard.py")
          and '"sync": cmd_sync' in _src("storyboard.py"))
    _probe45 = HERE.parent / "output" / "_m1_selftest" / "_sync_probe"
    _probe45.mkdir(parents=True, exist_ok=True)
    if _e37.exists():
        _t45 = _io.open(str(_e37), encoding="utf-8").read()
        core.write(_probe45 / u"02_剧本草稿.edited.md", _t45)
        core.write(_probe45 / u"02_剧本草稿.md", u"探针")
        core.write(_probe45 / u"01_prompt.md", u"探针")
        core.write(_probe45 / u"run.json", u"{}")
        core.write(_probe45 / u"03_确认A.md", u"- 生成方式：离线骨架（供验证链路，非成品）")
        core.write(_probe45 / u"08_爆款体检.md",
                   _bk42.build_exam(u"待填骨架，不是交付稿\n## ⓪\n待填"))
        check("有成品稿却配骨架体检单与「非成品」确认清单：B7 当场判不合格",
              bool(_bk42.check_b7(str(_probe45 / u"02_剧本草稿.edited.md"))))
        _done45 = _bk42.sync_run(str(_probe45 / u"02_剧本草稿.edited.md"))
        _exam45 = _io.open(str(_probe45 / u"08_爆款体检.md"), encoding="utf-8").read()
        _cf45 = _io.open(str(_probe45 / u"03_确认A.md"), encoding="utf-8").read()
        check("跑一次同步，配套三份自动按成稿重出，B7 放行",
              u"08_爆款体检.md" in _done45 and u"03_确认A.md" in _done45
              and not _bk42.check_b7(str(_probe45 / u"02_剧本草稿.edited.md"))
              and u"02_剧本草稿.edited.md" in _exam45
              and u"非成品" not in _cf45
              and u"本单对应填空骨架" not in _exam45)
    check("没有成稿的目录 B7 不误报",
          not _bk42.check_b7(str(_probe42 / "02_剧本草稿.md")))

    # 门禁不许先把配套件补齐再判：缺体检单第一次必须不合格，补齐后重跑才放行
    _real46 = HERE.parent / "output" / "20261116-104914-老照相馆关门前有人来取一"
    _probe46 = HERE.parent / "output" / "_m1_selftest" / "_gate_order_probe"
    if (_real46 / u"02_剧本草稿.edited.md").exists():
        if _probe46.exists():
            shutil.rmtree(str(_probe46))
        shutil.copytree(str(_real46), str(_probe46))
        _ex46 = _probe46 / u"08_爆款体检.md"
        if _ex46.exists():
            _ex46.unlink()
        _gp46 = _probe46 / u"02_剧本草稿.edited.md"

        def _gate46():
            r = subprocess.run([sys.executable, str(HERE / "m1_gate.py"), str(_gp46)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            return r.returncode, (r.stdout or "") + (r.stderr or "")

        _rc46a, _o46a = _gate46()
        _rc46b, _o46b = _gate46()
        check("门禁先判后同步：缺体检单当场判不合格，自动补齐后重跑才放行",
              _rc46a != 0 and u"B4" in _o46a and _rc46b == 0 and u"85/85" in _o46b or u"90/90" in _o46b or u"92/92" in _o46b or u"93/93" in _o46b)

    # 9r v2.9.49：写稿单子必须与当前工具同源（版本 + 三条最新硬查），
    # 不许盘上留旧单子、检查却判全过，照旧单子写出来的稿必被交付门拦下
    _p49 = HERE.parent / "output" / "_m1_selftest" / "_prompt_probe"
    _p49.mkdir(parents=True, exist_ok=True)
    _good49 = (u"# 阶段一 · 剧本生成任务（v%s 硬律注入版）\n\n" % core.VERSION
               + u"\n".join(core.PROMPT_MARKS))
    for _f49 in (u"03_确认A.md", u"run.json", u"02_剧本草稿.md"):
        core.write(_p49 / _f49, u"探针")
    _g49 = _p49 / u"02_剧本草稿.edited.md"
    core.write(_g49, u"## ⓪\n\n## ①\n\n待填骨架")
    core.write(_p49 / u"01_prompt.md", _good49)
    check("写稿单子与当前工具同版本、三条硬查写全：过程件检查放行",
          not _bk42.check_b6(str(_g49)))
    core.write(_p49 / u"01_prompt.md",
               _good49.replace(u"v" + core.VERSION, u"v2.9.46"))
    check("写稿单子挂旧版本：当场判不合格并写明版本",
          any(u"旧版本" in x for x in _bk42.check_b6(str(_g49))))
    core.write(_p49 / u"01_prompt.md", _good49.replace(core.PROMPT_MARKS[0], u""))
    check("写稿单子缺最新硬查：当场判不合格并写明缺哪条",
          any(u"最新硬查" in x for x in _bk42.check_b6(str(_g49))))
    core.write(_p49 / u"01_prompt.md", _good49)
    check("全盘写稿单子一键收口命令已接进主链路，成稿同步时自动重出单子",
          "def cmd_sync_all" in _src("storyboard.py")
          and '"--all"' in _src("storyboard.py")
          and "def rebuild_prompt" in _src("sb_core.py")
          and "core.rebuild_prompt" in _src("boom_chk.py"))
    _e49 = HERE.parent / "output" / "_m1_selftest" / "_prompt_gate"
    if (_real46 / u"02_剧本草稿.edited.md").exists():
        if _e49.exists():
            shutil.rmtree(str(_e49))
        shutil.copytree(str(_real46), str(_e49))
        core.write(_e49 / u"01_prompt.md",
                   _good49.replace(u"v" + core.VERSION, u"v2.9.46"))

        def _gate49():
            r = subprocess.run([sys.executable, str(HERE / "m1_gate.py"),
                                str(_e49 / u"02_剧本草稿.edited.md")],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            return r.returncode, (r.stdout or "") + (r.stderr or "")

        _rc49a, _o49a = _gate49()
        _rc49b, _o49b = _gate49()
        _pt49 = _io.open(str(_e49 / u"01_prompt.md"), encoding="utf-8").read()
        check("旧版本写稿单子：交付门第一次当场拦下并写明原因",
              _rc49a != 0 and u"B6" in _o49a and u"旧版本" in _o49a)
        check("同步后旧单子按当前工具重出，重跑放行",
              _rc49b == 0 and (u"85/85" in _o49b or u"90/90" in _o49b or u"92/92" in _o49b or u"93/93" in _o49b)
              and u"v" + core.VERSION in _pt49
              and all(mk in _pt49 for mk in core.PROMPT_MARKS))

    # 9s v2.9.50：全新情感题材实跑补出的五条说明、两处误伤，各留正反考题
    import m1_semchk as _ms50
    import consist_chk as _cz50
    _p50 = HERE.parent / "output" / "_m1_selftest" / "_exp50"
    _p50.mkdir(parents=True, exist_ok=True)
    _f50 = _p50 / "probe.md"
    core.write(_f50, u"## ③ 故事剧本\n老陈蹲着从门缝把白蜡烛递进去。\n")
    check("人蹲着从门缝递东西不再被判成门自己会动",
          _ms50.check(str(_f50)) == 0)
    core.write(_f50, u"## ③ 故事剧本\n门慢慢走开了。\n")
    check("门自己走仍被当场抓到", _ms50.check(str(_f50)) == 1)
    _sample50 = (u"## ⓪ 选题与爆款匹配说明\n"
                 u"- 《啥是佩奇》：老人举着天线在村口问啥是佩奇\n"
                 u"## ① 开题卡\n- 故事地点：棉纺厂老宿舍三号楼二单元\n"
                 u"## ③ 故事剧本\n老陈在楼道里把白蜡烛递到年轻人手上。\n")
    _r50 = [x for x in _cz50.run_all(_sample50, "m1") if x[0] == "C1"]
    check("引用别片样本里的村口不算本片换地方",
          bool(_r50) and _r50[0][2])
    _bad50 = _sample50.replace(u"老陈在楼道里", u"老陈从村口回到楼道里")
    _r50b = [x for x in _cz50.run_all(_bad50, "m1") if x[0] == "C1"]
    check("本片正文真出现村口配楼道照样拦下",
          bool(_r50b) and not _r50b[0][2])
    check("写稿单子写全五条新硬查，骨架占位与交付自检同源",
          all(mk in _p45 for mk in core.PROMPT_MARKS)
          and u"首段禁台词" in _src("sb_core.py")
          and u"每段两样动作加一处可触细节" in _src("sb_core.py"))

    # 9t v2.9.52：台词节奏——密对白过、单人自语散稿拦，出稿单子与门禁同源
    import dialogue_chk as _dc52
    _good52 = (u"## ③ 故事剧本\n"
               u"楼道口整栋停电，老陈拎着一包白蜡烛从一楼往上送。\n\n"
               u"老陈把蜡烛递过去，年轻人说：「别拆，那是我寄的。」老陈低头核对存根。\n\n"
               u"年轻人问：「里头装的什么？」老陈说：「一叠取件条。」他把条子塞回袋里。\n\n"
               u"年轻人说：「头一页是你签的。」老陈说：「我在这儿分过件。」把那页翻出来没再说话。\n")
    _bad52 = (u"## ③ 故事剧本\n"
              u"楼道口整栋停电，老陈拎着一包白蜡烛从一楼往上送，一层六户他挨家敲门。\n\n"
              u"老陈说：「六楼就剩这户。」门里不肯应，再敲还是没人应，他把蜡烛捏在手里。\n\n"
              u"老陈说：「屋里有人吧。」没人答，他把蜡烛插进门前的铁皮盒，手按在盒沿上。\n\n"
              u"老陈说：「是您画的吧。」门里没答话，拐杖点了两下，他贴着门板又听一回。\n")
    _gd52 = {x[0]: x[2] for x in _dc52.run_all(_good52)}
    _bd52 = {x[0]: x[2] for x in _dc52.run_all(_bad52)}
    check("台词节奏：密对白稿放行，单人自语加连串冷场稿两项当场拦下",
          _gd52.get(u"D1") and _gd52.get(u"D2")
          and not _bd52.get(u"D1") and not _bd52.get(u"D2"))
    check("台词节奏新判据已接进 M1 交付门、写稿单子、骨架与交付自检",
          u"dialogue_chk" in _src("m1_gate.py")
          and u"每段至少一句台词" in _p45 and u"不许一路自语没人接" in _p45
          and u"每段至少一句台词" in _src("sb_core.py"))

    # 9u v2.9.53：开场钩子认得出「敲三下没人应」，不逼着改写成「撞门」
    import story_logic as _sl53
    _hook53 = _sl53.check_hook(u"白蜡烛", [
        (u"楼道一层六户，这晚整栋停电，老陈退休前是这楼的电工，每月挨户抄电表。", []),
        (u"老陈挪到602门前，右手在门板上敲了三下，屋里一声不吭，再敲三下，屋里照样一声不吭。", []),
        (u"他低头看见门前那只铁皮盒，白蜡烛短了一截。", []),
        (u"门缝推出一张纸。", []), (u"老陈把白蜡烛递进去。", [])])
    check("开场钩子：「敲三下没人应」算真钩子，不必改写成「撞门」才过关",
          not _hook53, str(_hook53))


    # 9v v2.9.55：句子与技法全过、因果断链的稿，必须当场拦下
    import logic_chain_chk as _lc55
    _tmp55 = HERE.parent / "output" / "_m1_selftest" / "_logic55"
    _tmp55.mkdir(parents=True, exist_ok=True)
    _good55 = (u"## ① 开题卡\n- 题眼道具：铁皮饼干盒\n\n## ③ 故事剧本\n\n"
               u"周晓把铁皮饼干盒捧上来，说：「我爸那年住院，你借我三千。」陈默把铁皮盒按在柜台上，说：「一张没动。」\n\n"
               u"周晓说：「还完就来取。」陈默说：「收了你就还清了，就不来了。」周晓说：「下回不来了。」\n")
    _bad55 = (u"## ① 开题卡\n- 题眼道具：铁皮饼干盒\n\n## ③ 故事剧本\n\n"
              u"周晓把铁皮饼干盒捧上来，说：「我寄过钱。」陈默把铁皮盒按在柜台上，说：「知道了。」\n")
    core.write(_tmp55 / u"good.md", _good55)
    core.write(_tmp55 / u"bad.md", _bad55)
    _g55 = {x[0]: x[1] for x in _lc55.run_all(str(_tmp55 / u"good.md"))}
    _b55 = {x[0]: x[1] for x in _lc55.run_all(str(_tmp55 / u"bad.md"))}
    check("因果链：钱款/承诺/交接/职业/算术齐全的稿放行，钱款断链的稿当场拦下",
          all(_g55.values()) and not all(_b55.values()))

    # 9w v2.9.56：动机三问（为什么是现在 / 为什么拖到今天）
    import logic_chain_chk as _lc56
    _why_ok = (u"## ① 开题卡\n- 题眼道具：铁皮饼干盒\n\n## ③ 故事剧本\n\n她赶末班车来开盒，再不来就赶不上。陈默守着这只盒八年，没敢开，怕她回来就恨他。\n")
    _why_bad = (u"## ③ 故事剧本\n\n她赶末班车来开盒。陈默守着这只盒八年。\n")
    _tmp56 = HERE.parent / "output" / "_m1_selftest" / "_why56"
    _tmp56.mkdir(parents=True, exist_ok=True)
    core.write(_tmp56 / u"ok.md", _why_ok)
    core.write(_tmp56 / u"bad.md", _why_bad)
    _w56a = {x[0]: x[1] for x in _lc56.run_all(str(_tmp56 / u"ok.md"))}
    _w56b = {x[0]: x[1] for x in _lc56.run_all(str(_tmp56 / u"bad.md"))}
    check("动机三问：交代了非现在不可与拖到今天的理由就放行，不交代就当场退",
          all(v for k, v in _w56a.items() if not k.startswith(u"L3"))
          and not all(v for k, v in _w56b.items() if k.startswith(u"L7")))

    # 9x v2.9.57：题材落地（登记的关系必须在正文演出来）
    _th_ok = (u"## ① 开题卡\n- 一句话 Logline：青梅竹马的两个人在巷子里走散了\n\n## ③ 故事剧本\n\n小时候两个人蹲在门槛上分一根冰棍，她说长大了要嫁他。\n")
    _th_bad = (u"## ① 开题卡\n- 一句话 Logline：青梅竹马的两个人在巷子里走散了\n\n## ③ 故事剧本\n\n两个人从小一起长大，如今走散了。\n")
    _tmp57 = HERE.parent / "output" / "_m1_selftest" / "_theme57"
    _tmp57.mkdir(parents=True, exist_ok=True)
    core.write(_tmp57 / u"ok.md", _th_ok)
    core.write(_tmp57 / u"bad.md", _th_bad)
    _t57a = {x[0]: x[1] for x in _lc56.run_all(str(_tmp57 / u"ok.md"))}
    _t57b = {x[0]: x[1] for x in _lc56.run_all(str(_tmp57 / u"bad.md"))}
    check("题材落地：正文演了青梅竹马就放行，只在设定里写关系就当场退",
          all(v for k, v in _t57a.items() if not k.startswith((u"L3", u"L5")))
          and not all(v for k, v in _t57b.items() if k.startswith(u"L8")))
    # 汇总
    passed = sum(1 for r in RESULTS if r[0])
    total = len(RESULTS)
    summary = "\n".join("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  " + d) if d else "")
                        for ok, name, d in RESULTS)
    text = ("M1 自测报告 %s\n" % ts
            + "=" * 60 + "\n" + summary
            + "\n" + "=" * 60 + "\n结论：%d/%d 通过%s\n" % (
                passed, total, "，链路可跑通" if passed == total else "，存在未通过项"))
    report = HERE.parent / "output" / "_m1_selftest" / "report.txt"
    core.write(report, text)
    print("")
    print("结论：%d/%d 通过  报告：%s" % (passed, total, report))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
