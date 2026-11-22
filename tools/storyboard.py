# -*- coding: utf-8 -*-
"""通用题材一句话分镜脚本系统 · 本地可跑原型（M1）

用法：
  python storyboard.py doctor
  python storyboard.py lint
  python storyboard.py stage1 --idea "一句话" [--duration 180] [--shots 16] [--platform 抖音]
                                  [--ratio 9:16] [--real] [--ref "作品链接或名称"] [--llm]
  python storyboard.py confirm A --run output\20261112-112000-xxxx
  python storyboard.py sync --run output\20261112-112000-xxxx  # 成稿落盘后自动同步配套文件
  python storyboard.py stage2 --run output\20261112-112000-xxxx
  python storyboard.py stage3 --run output\20261112-112000-xxxx

纪律（代码里强制）：
  * 只写 E 盘；非 E 盘直接拒绝。
  * stage2 / stage3 必须先有 confirm A，否则拒绝执行。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sb_core as core  # noqa: E402
import series_note as srs  # noqa: E402
import boom_chk  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MIN_PER_SECTION = 3
STALE_DAYS = 60


# ------------------------------------------------------------------ doctor

def cmd_doctor(args):
    lines = []
    ok = True

    lines.append("== 通用题材一句话分镜脚本系统 · doctor ==")
    lines.append("版本：%s" % core.VERSION)
    lines.append("Python：%s" % sys.version.split()[0])
    lines.append("技能根：%s" % core.PROJECT)
    lines.append("")

    if core.PROJECT.exists():
        lines.append("[OK] 技能根目录存在")
    else:
        lines.append("[FAIL] 技能根目录不存在")
        ok = False

    if core.SKILL_FILE.exists():
        lines.append("[OK] SKILL.md 存在（%d 字节）" % core.SKILL_FILE.stat().st_size)
    else:
        lines.append("[FAIL] SKILL.md 缺失")
        ok = False

    try:
        entries = core.parse_library()
        lines.append("[OK] 爆款储备库可解析：%d 条案例" % len(entries))
        stats = core.library_stats(entries)
        for gid in sorted(stats):
            n = stats[gid]["count"]
            flag = "OK" if n >= MIN_PER_SECTION else "不足"
            lines.append("     §%-4s %2d 条  latest=%s  %s" % (gid, n, stats[gid]["latest"] or "-", flag))
            if n < MIN_PER_SECTION:
                ok = False
    except Exception as e:
        lines.append("[FAIL] 爆款储备库解析失败：%s" % e)
        ok = False

    lines.append("[OK] 结构禁词表 %d 个；禁写类别 %d 类；模糊动作 %d 个" % (
        len(core.BANNED_STRUCT), len(core.BANNED_PATTERNS), len(core.VAGUE_ACTIONS)))

    try:
        core.assert_e_drive(core.OUTPUT_ROOT)
        probe = core.OUTPUT_ROOT / "_doctor"
        probe.mkdir(parents=True, exist_ok=True)
        f = probe / "probe.txt"
        core.write(f, "ok %s\n" % datetime.now().isoformat(timespec="seconds"))
        lines.append("[OK] E 盘可写：%s" % f)
    except Exception as e:
        lines.append("[FAIL] E 盘写入失败：%s" % e)
        ok = False

    lines.append("")
    lines.append("结论：%s" % ("通过（可进 M2 前的联调）" if ok else "存在未通过项，先修再跑"))
    text = "\n".join(lines)
    print(text)
    core.write(core.OUTPUT_ROOT / "_doctor" / "doctor_report.txt", text + "\n")
    return 0 if ok else 1


# ------------------------------------------------------------------ lint

def cmd_lint(args):
    entries = core.parse_library()
    stats = core.library_stats(entries)
    today = date.today()
    rows, bad = [], 0
    for g in core.GENRES:
        s = stats.get(g["section"], {"count": 0, "latest": ""})
        n, latest = s["count"], s["latest"]
        stale = ""
        if latest:
            try:
                days = (today - datetime.strptime(latest, "%Y-%m-%d").date()).days
                if days > STALE_DAYS:
                    stale = "过期 %d 天" % days
            except Exception:
                pass
        status = "OK"
        if n < MIN_PER_SECTION:
            status = "补足（缺 %d 条）" % (MIN_PER_SECTION - n)
        elif stale:
            status = "联网刷新"
        if status != "OK":
            bad += 1
        rows.append("§%-4s %-28s %2d 条  %-10s %s" % (
            g["section"], g["name"], n, latest or "-", status))
    print("== 爆款储备库体检（阈值：每子类 >= %d 条，%d 天内）==" % (MIN_PER_SECTION, STALE_DAYS))
    print("\n".join(rows))

    prof = core.parse_profile()
    prof_rows, prof_bad = [], 0
    for g in core.GENRES:
        p = prof.get(g["id"])
        n = stats.get(g["section"], {"count": 0})["count"]
        if not p:
            prof_rows.append("§%-4s 六维画像缺失  ← 需在爆款储备库 P.0 补一行" % g["section"])
            prof_bad += 1
            continue
        ok = (p["n"] == n)
        if not ok:
            prof_bad += 1
        prof_rows.append("§%-4s 画像依据条数 %2d / 库内实有 %2d  %s" % (
            g["section"], p["n"], n, "OK" if ok else "不一致（改 P.0 的「依据条数」）"))
    print("\n== 六维画像与库内条数一致性 ==")
    print("\n".join(prof_rows))
    print("")
    print("需要动作的子类：%d 个；画像不一致：%d 个" % (bad, prof_bad))

    single = core.parse_single()
    sc_rows, sc_n = [], 0
    for g in core.GENRES:
        rows_ = single.get(g["id"], [])
        sc_n += len(rows_)
        sc_rows.append("§%-4s 单条口径 %d 条（库内 %d 条）%s" % (
            g["section"], len(rows_), stats.get(g["section"], {"count": 0})["count"],
            "" if rows_ else "  ← 暂无单条数据，按子类画像计算（运行时按 §7.3 自采补入）"))
    print("\n== 单条案例实测覆盖（P.1）==")
    print("\n".join(sc_rows))
    print("")
    print("单条实测合计 %d 条 / 全库 %d 条" % (sc_n, sum(v["count"] for v in stats.values())))

    core.write(core.OUTPUT_ROOT / "_doctor" / "library_lint.txt",
               "== lint ==\n" + "\n".join(rows) +
               "\n\n== 六维画像一致性 ==\n" + "\n".join(prof_rows) +
               "\n\n== 单条实测覆盖 P.1 ==\n" + "\n".join(sc_rows) +
               "\n需要动作：%d；画像不一致：%d；单条实测 %d 条\n" % (bad, prof_bad, sc_n))
    return 0


# ------------------------------------------------------------------ LLM（可选）

def call_llm(prompt: str) -> str:
    base = os.environ.get("SB_LLM_BASE")
    key = os.environ.get("SB_LLM_KEY")
    model = os.environ.get("SB_LLM_MODEL")
    if not (base and key and model):
        raise RuntimeError(
            "未配置模型：请先设 SB_LLM_BASE / SB_LLM_KEY / SB_LLM_MODEL 三个环境变量"
            "（OpenAI 兼容接口，自带 Key，密钥不出本机）；不加 --llm 则只出离线骨架。")
    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    })
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


# ------------------------------------------------------------------ stage1

def cmd_stage1(args):
    idea = (args.idea or "").strip()
    if not idea:
        print("[拒绝] 缺 --idea（一句话主题）")
        return 2

    # 连续剧：指定 --run（整季目录）+ --ep，则本集写入 该季目录/EPnn/，三阶段流程完全复用
    season_dir = Path(args.run) if getattr(args, "run", None) else None
    ep_no = int(getattr(args, "ep", 0) or 0)
    ep_row = None
    if season_dir:
        if ep_no <= 0:
            print("[拒绝] 指定 --run 时必须给 --ep（第几集）")
            return 2
        meta_season = core.read_run(season_dir) if (season_dir / "run.json").exists() else {}
        for r in (meta_season.get("series") or {}).get("rows", []):
            if r["ep"] == ep_no:
                ep_row = r
        if not ep_row:
            print("[拒绝] 该季分集表里没有 EP%02d" % ep_no)
            return 2
        if ep_no >= 2 and not meta_season.get("series_confirmed_a"):
            print("[拒绝] 整季分集表还没确认（series_confirmed_a=false）。先 `confirm A --run <整季目录>`，再写第 2 集以后。")
            return 2

    cls = core.classify(idea)
    genre = cls["primary"]
    entries = core.parse_library()
    matched = core.match_works(genre, entries, limit=3, idea=idea)
    matched["note"] = cls["note"]

    opts = {
        "platform": args.platform, "ratio": args.ratio,
        "real": bool(args.real), "ref": args.ref or "",
    }
    profile = core.merge_profile(core.parse_profile(), core.parse_single())
    scale = core.suggest_scale(genre, matched=matched, duration=args.duration,
                               shots=args.shots, profile=profile)
    if ep_row:
        scale["total_seconds"] = ep_row["seconds"]
        scale["shots"] = ep_row["shots"]
        scale["source"] = "整季分集表（EP%02d，单集 %d 秒 / %d 镜）" % (ep_row["ep"], ep_row["seconds"], ep_row["shots"])
        scale["basis"] = "%s；单集规格取自整季分集表：%s" % (scale.get("basis", ""), ep_row["function"])

    prompt = core.build_stage1_prompt(idea, genre, matched, scale, opts, profile=profile)
    skeleton = core.build_script_skeleton(idea, genre, matched, scale, opts)

    if args.llm:
        try:
            draft = call_llm(prompt)
        except Exception as e:
            print("[失败] 模型调用失败：%s" % e)
            return 3
        mode = "llm"
    else:
        draft = skeleton
        mode = "offline-skeleton"

    issues = core.scan_text(draft, stage="script")
    check_txt = core.format_issues(issues)

    run = (season_dir / ("EP%02d" % ep_no)) if season_dir else core.new_run_dir(idea)
    run.mkdir(parents=True, exist_ok=True)
    core.write(run / "01_prompt.md", prompt)
    core.write(run / "02_剧本草稿.md", draft)
    core.write(run / "selfcheck.txt", check_txt)
    # 爆款体检单随稿出，不许留给人补：从 ⑧ 六条抽本次实际证据句，逐条给判定
    exam = boom_chk.build_exam(draft, src=u"02_剧本草稿.md", meta={
        "genre": genre["name"],
        "lib": matched.get("own_count", 0), "used": len(matched["items"]),
        "dur": u"%s 秒（依据：%s）" % (scale.get("total_seconds") or u"待定",
                                      scale.get("basis") or u"无"),
        "rhythm": scale.get("rhythm", u""),
        "light": profile.get(genre["id"], {}).get("light") or u"全片一处主光、一个色温",
    })
    core.write(run / "08_爆款体检.md", exam)

    p = profile.get(genre["id"], {})
    style_light = p.get("light") or "库内该维无数据（阶段二按案例原文现场定，注明推定）"
    line_density = p.get("line") or "库内该维无数据（按台词铁律执行）"
    hit_words = "、".join([w for w in genre["keys"] if w in idea][:4]) or "（未命中具体词，按语义归类）"

    confirm_md = "\n".join([
        "# 确认节点 A · 剧本确认清单",
        "",
        "- run：`%s`" % run,
        "- 一句话主题：%s" % idea,
        "- 识别题材：%s（%s）｜命中判据词：%s" % (genre["name"], genre["id"], hit_words),
    ] + ([
        "- 形态：连续剧第 %02d 集｜本集功能：%s" % (ep_row["ep"], ep_row["function"]),
        "- 本集尾钩类型：%s（尾钩只给一半信息，不给答案）" % ep_row["hook"],
        "- 整季分集表：`%s`（改集数 / 改某集功能都在那份上改，改完回到本集重跑）" % (season_dir / "02_分集表.md"),
    ] if ep_row else []) + [
        "- 生成方式：%s" % ("对话模型生成" if mode == "llm" else "离线骨架（供验证链路，非成品）"),
        "",
        "## 一、本次自适应参数（全部由本次输入 + 本次匹配现算，非技能默认值）",
        "- 库内检索：§%s 该子类共 %d 条 → 本次取用 %d 条%s" % (
            genre["section"], matched["own_count"], len(matched["items"]),
            "" if matched["enough"] else "  ← 不足 3，已走最近邻，需联网补足"),
        "- 本次取用（真实片名 + 平台）：",
    ] + ["  %d. 《%s》· %s%s" % (i + 1, e["title"], e["platform"] or "未标注",
                                 "（跨类 §%s）" % e["cross_from"] if e.get("cross") else "")
         for i, e in enumerate(matched["items"])] + [
        "- 六维共性 → 推导：",
        "  - 时长：%s 秒（依据：%s）" % (scale.get("total_seconds") or "待定", scale.get("basis") or "无"),
        "  - 镜数：不预设（剧本切几段就是几镜；单镜内容超 15 秒才拆）",
        "  - 节奏：%s" % scale["rhythm"],
        "  - 氛围与光影（供阶段二）：%s" % style_light,
        "  - 台词密度：%s" % line_density,
        "",
        "## 一之二、爆款对照表（M1 固定项 · 每行必须落到具体幕与段落名，空行即不合格）",
        "| 学的招式 | 出自哪条爆款 | 本片落在哪一段（幕·段落名） | 怎么落的 |",
        "| --- | --- | --- | --- |",
    ] + ["| %s | 《%s》 | 见 `02_剧本草稿.md` ②c 表第 %d 行 | 同 ②c 表该行，写死到具体幕与动作 |" % (
             m, matched["items"][i % max(1, len(matched["items"]))]["title"], i + 1)
         for i, m in enumerate(["钩子", "困境", "揭晓反转", "题眼道具贯穿", "反差人设", "节奏密度"])] + [
        "",
        "> 六类招式各一行；题眼道具要写它在开头/中段/结尾各出现一次且状态不同；密度写本次案例的节奏（如每 20 秒一处萌点或反转）。",
        "",
        "## 二、拍板（确认节点 A · 按已立规矩自定，不反问；每项都用本次实际值写死）",
        "1. 人物设定：本次剧本里出场的人物全部本次生成、未套用预设，见 `02_剧本草稿.md` 首现标注；要改直接在稿上改，改完我重跑自检。",
        "2. 故事线：要动哪一幕或哪一段，在 `02_剧本草稿.md` 上指明幕名或段落，改完我重跑自检。",
        "3. 结构与时长：本次按剧本的幕结构推进 / %s 秒；秒数由画面与台词内容现算，不按字数反推，要改在稿内登记值上改。" % (
            scale.get("total_seconds") or "待定"),
        "4. 爆款参照：本次 %d 条（见上，均登记在 ⓪），要与本稿同口径；换片名须同步 ⓪、②c、体检单与三份过程件。" % len(matched["items"]),
        "",
        "## 三、M2 会按什么做（预告，见 `02_剧本草稿.md` 的 ⑥）",
        "- 底本：本份剧本锁稿后即唯一底本，不另起故事、不加戏。",
        "- 拆分：按幕分场、按段落切镜，靠换人/换地/换动作/换信息定切点。",
        "- 秒数：先定每镜演什么，再由这一镜的画面与台词内容现算秒数，不按字数反推；单镜 ≤15 秒、无下限；镜数由切段得出，不预设；合计与总时长的偏差 ≤10% 只做 ±1 秒取整，>10% 回改剧本加戏或删戏。",
        "- 五件套：场景卡 / 道具卡 / 角色卡 / 风格锁定 / 音频层。",
        "- 未确认前不生成任何一镜分镜。",
        "",
        "## 怎么改",
        "- 直接在 `02_剧本草稿.md` 上改，另存为 `02_剧本草稿.edited.md`，再执行 `confirm A`。",
        "- 或者把要改的点回给我，我改完再请你确认。",
        "",
        "## 确认命令",
        "```",
        "python tools\\storyboard.py confirm A --user-ok --run %s" % run,
        "```",
        "",
        "> 未执行确认前，阶段二 / 阶段三一律拒绝执行。",
        "",
        "## 自检结果",
        "```",
        check_txt.strip(),
        "```",
        "",
        "## 爆款体检",
        "- `08_爆款体检.md`：本工具随稿生成，六项硬检逐条给「过／不过 ＋ 证据句」，另核爆款骨、反转铁律、双源全库检索、②c 逐行片名、⑧ 逐条证据、风格三条手法、过程件一致、六维共性现算。",
        "- 体检单缺失或任一项不合格，剧本门当场退回重出，不把没写全的稿子交出去。",
        "",
    ])
    core.write(run / "03_确认A.md", confirm_md)

    meta = {
        "idea": idea, "genre": genre["id"], "genre_name": genre["name"],
        "platform": opts["platform"] or genre["platform"],
        "ratio": opts["ratio"] or genre["ratio"],
        "real": opts["real"], "ref": opts["ref"],
        "scale": scale,
        "matched": [{"title": e["title"], "platform": e["platform"],
                     "section": e["section"], "cross": bool(e.get("cross"))}
                    for e in matched["items"]],
        "mode": mode,
        "issues": len(issues),
        "confirmed_a": False,
        "confirmed_b": False,
        "confirmed_c": False,
        "stage": "script_draft",
        "form": "series" if ep_row else "single",
        "ep": ep_row["ep"] if ep_row else None,
        "season_dir": str(season_dir) if season_dir else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    core.save_run(run, meta)
    # 同目录若已有成稿（改稿另存的那份），配套文件自动按成稿重出，不留骨架口气
    try:
        boom_chk.sync_run(str(run / "02_剧本草稿.md"))
    except Exception:
        pass

    print("[OK] run: %s" % run)
    print("     题材 %s / 爆款 %d 条 / 方式 %s / 自检问题 %d 处" % (
        genre["id"], len(matched["items"]), mode, len(issues)))
    print("     下一步：打开 03_确认A.md，改完执行 confirm A")
    if not matched["enough"]:
        print("     [注意] 本子类不足 3 条，已跨类借基因，交付里需明示")
    return 0


def cmd_sync(args):
    """成稿落盘后，一键把体检单／确认清单／自检结果按成稿重出；
    --all 则把盘上全部写稿单子按当前工具版本重出一次。"""
    if getattr(args, "all", False):
        return cmd_sync_all()
    run = Path(args.run) if getattr(args, "run", None) else None
    if run is None:
        print("[拒绝] 请给 --run <目录>，或用 --all 收口全盘写稿单子")
        return 2
    p = run / "02_剧本草稿.edited.md"
    if not p.exists():
        p = run / "02_剧本草稿.md"
    if not p.exists():
        print("[拒绝] 该目录没有剧本稿：%s" % run)
        return 2
    done = boom_chk.sync_run(str(p))
    print("[OK] 已按成稿同步：%s" % (u"、".join(done) if done else u"该目录没有成稿，无需同步"))
    return 0


def cmd_sync_all():
    """工具升版后一次收口：盘上所有写稿单子按当前工具重出，旧口径零残留。"""
    changed = []
    for rj in sorted(core.OUTPUT_ROOT.glob("*/run.json")):
        if core.rebuild_prompt(rj.parent):
            changed.append(rj.parent.name)
    print("[OK] 写稿单子按 v%s 重出 %d 份（共扫 %d 个留档目录）" % (
        core.VERSION, len(changed),
        len(list(core.OUTPUT_ROOT.glob("*/run.json")))))
    for n in changed:
        print("  - %s" % n)
    return 0


# ------------------------------------------------------------------ series（连续剧）

def cmd_series(args):
    """连续剧（多集）：先出整季分集表 + 第 1 集剧本草稿，确认后再逐集生成。"""
    from types import SimpleNamespace

    idea = (args.idea or "").strip()
    if not idea:
        print("[拒绝] 缺 --idea（一句话主题）")
        return 2

    cls = core.classify(idea)
    genre = cls["primary"]
    entries = core.parse_library()
    matched = core.match_works(genre, entries, limit=3, idea=idea)
    matched["note"] = cls["note"]
    profile = core.merge_profile(core.parse_profile(), core.parse_single())

    plan = srs.plan_series(genre, matched, profile, episodes=args.episodes,
                           per_ep_duration=args.duration, shots=args.shots,
                           platform=args.platform)
    outline = srs.build_series_outline(idea, genre, plan, matched=matched)
    issues = core.scan_text(outline, stage="script")

    season = core.new_run_dir(idea)
    core.write(season / "02_分集表.md", outline)

    confirm_md = "\n".join([
        "# 确认节点 A · 整季分集表确认",
        "",
        "- 整季目录：`%s`" % season,
        "- 一句话主题：%s" % idea,
        "- 形态：连续剧 %d 集 × 单集 %d 秒（单集 %d 镜）" % (
            plan["episodes"], plan["per_ep_seconds"], plan["per_ep_shots"]),
        "- 集数依据：%s" % plan["ep_basis"],
        "- 单集规格依据：%s" % plan["ep_scale"].get("basis", ""),
        "- 参考爆款：%s（%s 类取用 %d 条）" % (
            "、".join("《%s》" % e["title"] for e in matched["items"]),
            genre["name"], len(matched["items"])),
        "",
        "## 你需要拍板的三件事",
        "1. 集数：%d 集，按这个走还是改成你要的集数？" % plan["episodes"],
        "2. 单集时长 / 镜数：%d 秒 / %d 镜（每镜 ≤15 秒），按这个走还是改？" % (
            plan["per_ep_seconds"], plan["per_ep_shots"]),
        "3. 每集功能与尾钩：见 `02_分集表.md` 的表，哪一集的功能或尾钩要换？",
        "",
        "## 确认后的顺序",
        "- 先锁整季分集表（本确认单），再逐集走 A/B/C；每集是一个独立 run 目录，三阶段照旧。",
        "- `python tools\\storyboard.py confirm A --run %s` 确认整季分集表。" % season,
        "- 生成第 2 集：`python tools\\storyboard.py stage1 --idea \"%s\" --run %s --ep 2`" % (idea, season),
        "",
        "## 自检结果",
        "```", core.format_issues(issues).strip(), "```", "",
    ])
    core.write(season / "03_确认A.md", confirm_md)

    meta = {
        "idea": idea, "genre": genre["id"], "genre_name": genre["name"],
        "form": "series", "stage": "series_outline",
        "episodes": plan["episodes"], "per_ep_seconds": plan["per_ep_seconds"],
        "per_ep_shots": plan["per_ep_shots"],
        "series": {"rows": plan["rows"], "rules": plan["rules"], "ep_basis": plan["ep_basis"]},
        "matched": [{"title": e["title"], "platform": e["platform"], "section": e["section"]}
                    for e in matched["items"]],
        "confirmed_a": False, "confirmed_b": False, "confirmed_c": False,
        "issues": len(issues),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    core.save_run(season, meta)

    print("[OK] 整季目录：%s" % season)
    print("     %d 集 × %d 秒（单集 %d 镜）/ 分集表已出 / 自检问题 %d 处" % (
        plan["episodes"], plan["per_ep_seconds"], plan["per_ep_shots"], len(issues)))
    print("     下一步：看 03_确认A.md 改集数与每集功能，再 confirm A")

    # 同时生成第 1 集（写进 整季目录/EP01/，三阶段完全复用单集流程）
    ns = SimpleNamespace(idea=idea, duration=None, shots=None, platform=args.platform,
                         ratio=args.ratio, real=bool(args.real), ref=args.ref,
                         llm=bool(args.llm), run=str(season), ep=1)
    return cmd_stage1(ns)


# ------------------------------------------------------------------ confirm

def resolve_run(arg) -> Path:
    s = str(arg).strip().strip('"')
    p = Path(s)
    if p.is_absolute():
        return p
    if s.startswith("output"):
        return core.PROJECT / s
    return core.OUTPUT_ROOT / s


def _check_shots(text, total):
    """阶段二自检：单镜是否超 15 秒；各镜按内容合计与目标总时长的偏差是否超 10%。"""
    issues = core.scan_shots(text, total)
    hit = [float(m) for m in re.findall(
        r"镜\s*\d+\s*（\s*(\d+(?:\.\d+)?)\s*秒\s*）", text)]
    if hit and total and abs(sum(hit) - total) > max(3.0, total * core.TOTAL_TOL):
        if not any(x["kind"] == "总时长偏差" for x in issues):
            issues.append({"line": 0, "kind": "总时长偏差",
                           "detail": "各镜按内容合计 %.0f 秒，目标 %d 秒，偏差超 10%%；"
                                     "回改剧本加戏或删戏，不压秒凑数" % (sum(hit), total)})
    return issues


def cmd_confirm(args):
    run = resolve_run(args.run)
    meta = core.read_run(run)
    stage = args.stage

    if not getattr(args, "user_ok", False):
        print("[拒绝] 确认节点不许程序自己走：必须等用户点头。")
        print("     先把 %s 打开给用户看，用户明确说「确认／点头」之后，再加 --user-ok 重跑本命令；"
              "同一轮里禁止 A→B→C 连跑。" % ("03_确认A.md" if stage == "A" else
                                          ("05_确认B.md" if stage == "B" else "07_确认C.md")))
        return 3

    if stage == "A":
        if (run / "02_分集表.md").exists() and not (run / "02_剧本草稿.md").exists():
            # 整季分集表确认：锁定分集表本身，不锁某一集剧本
            text = (run / "02_分集表.md").read_text(encoding="utf-8")
            issues = core.scan_text(text)
            core.write(run / "02_分集表.locked.md", text)
            core.write(run / "selfcheck_a.txt", core.format_issues(issues))
            meta["series_confirmed_a"] = True
            meta["stage"] = "series_confirmed_a"
            core.save_run(run, meta)
            print("[OK] 整季分集表已锁：%s" % (run / "02_分集表.locked.md"))
            print("     自检问题 %d 处；下一步逐集生成：stage1 --run <整季目录> --ep 2" % len(issues))
            return 0
        need, src_names, lock_name, sheet = (
            None, ["02_剧本草稿.edited.md", "02_剧本草稿.md"],
            "02_剧本草稿.locked.md", "03_确认A.md")
    elif stage == "B":
        need, src_names, lock_name, sheet = (
            "confirmed_a", ["04_分镜.edited.md", "04_分镜.md"],
            "04_分镜.locked.md", "05_确认B.md")
    else:
        need, src_names, lock_name, sheet = (
            "confirmed_b", ["06_提示词.edited.md", "06_提示词.md"],
            "06_提示词.locked.md", "07_确认C.md")

    if need and not meta.get(need):
        print("[拒绝] 未通过上一确认节点（%s=false）。请先执行确认，再往下走。" % need)
        return 2

    src = None
    for nm in src_names:
        if (run / nm).exists():
            src = run / nm
            break
    if src is None:
        print("[拒绝] 找不到待确认稿：%s" % " / ".join(src_names))
        return 2

    text = src.read_text(encoding="utf-8")
    if stage == "A":
        # M1 收尾硬规：必须带「⑥ 分镜脚本将按什么要求制作」，且不能出现任何一镜分镜
        if "⑥" not in text or "分镜脚本将按什么要求制作" not in text:
            # ⑥ 是交付口径，允许写在 03_确认A.md（用户明确要求剧本正文不塞参数）
            alt = src.parent / "03_确认A.md"
            if alt.exists():
                alt_text = alt.read_text(encoding="utf-8")
                idx6 = alt_text.find("## ⑥")
                if idx6 >= 0 and "分镜脚本将按什么要求制作" in alt_text:
                    tail = alt_text[idx6:]
                    nxt = tail.find("\n## ", 4)
                    text = text + "\n\n" + (tail[:nxt] if nxt > 0 else tail)
        if "⑥" not in text or "分镜脚本将按什么要求制作" not in text:
            print("[拒绝] 剧本缺「⑥ 分镜脚本将按什么要求制作」预告；M1 末尾必须先写清下游怎么拍再停。")
            return 2
        if re.search(r"\*\*镜\s*\d+\s*（\s*\d+\s*秒", text):
            print("[拒绝] M1 剧本里出现了分镜镜号与秒数，属于抢跑阶段二，删掉再确认。")
            return 2
        issues = core.scan_text(text, stage="script")
    elif stage == "B":
        issues = core.scan_text(text, stage="storyboard")
        total = int((meta.get("scale") or {}).get("total_seconds") or 0)
        issues = issues + _check_shots(text, total)
    else:
        issues = core.scan_text(text)
    core.write(run / lock_name, text)
    core.write(run / ("selfcheck_%s.txt" % stage.lower()), core.format_issues(issues))

    if stage == "A":
        meta["confirmed_a"] = True
        meta["stage"] = "confirmed_a"
        meta["locked_from"] = src.name
    elif stage == "B":
        meta["confirmed_b"] = True
        meta["stage"] = "confirmed_b"
        meta["locked_b_from"] = src.name
    else:
        meta["confirmed_c"] = True
        meta["stage"] = "confirmed_c"
        meta["locked_c_from"] = src.name
    meta["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
    meta["issues_at_lock"] = len(issues)
    core.save_run(run, meta)

    if (run / sheet).exists():
        note = "\n---\n\n## 确认记录\n\n- 确认时间：%s\n- 锁定来源：`%s`\n- 锁定自检：%d 处\n" % (
            meta["confirmed_at"], src.name, len(issues))
        core.write(run / sheet, (run / sheet).read_text(encoding="utf-8").rstrip() + "\n" + note)

    print("[OK] 已确认并锁定（节点 %s）：%s" % (stage, run / lock_name))
    print("     锁定自检问题：%d 处%s" % (len(issues), "" if issues == 0 else "（建议先改再锁）"))
    if stage == "A":
        print("     下一步可执行：stage2（按 §8 框架出分镜）")
    elif stage == "B":
        print("     下一步可执行：stage3（按 §9 模板出 ⑦a/⑦b/⑦c 提示词）")
    else:
        print("     交付终点：到此为止，画面生成/剪辑/发布不在本技能范围")
    return 0


# ------------------------------------------------------------------ stage2 / stage3

def _guard(run_arg, need):
    run = resolve_run(run_arg)
    meta = core.read_run(run)
    if not meta.get(need):
        print("[拒绝] 未通过上一确认节点（%s=false）。请先执行确认，再往下走。" % need)
        print("     原因：三阶段确认流是硬纪律，未确认不许自动推进。")
        return None
    return meta


def _matched_objects(meta):
    entries = core.parse_library()
    titles = {m["title"] for m in (meta.get("matched") or [])}
    items = [e for e in entries if e["title"] in titles]
    if not items:
        items = core.match_works(core.GENRE_BY_ID[meta["genre"]], entries)["items"]
    return {"items": items, "own_count": len([e for e in entries
                                             if e["section"] == meta["genre"]]),
            "enough": len(items) >= 3, "note": "取自阶段一确认过的爆款"}


def cmd_stage2(args):
    meta = _guard(args.run, "confirmed_a")
    if meta is None:
        return 2
    run = resolve_run(args.run)
    locked = run / "02_剧本草稿.locked.md"
    if not locked.exists():
        print("[拒绝] 缺锁稿剧本：%s（请先 confirm A）" % locked)
        return 2
    script = locked.read_text(encoding="utf-8")
    genre = core.GENRE_BY_ID[meta["genre"]]
    matched = _matched_objects(meta)
    profile = core.merge_profile(core.parse_profile(), core.parse_single())
    scale = dict(meta.get("scale") or {})

    prompt = core.build_stage2_prompt(meta["idea"], genre, matched, scale, script, profile=profile)
    core.write(run / "04_prompt.md", prompt)
    if args.llm:
        try:
            board = call_llm(prompt)
        except Exception as e:
            print("[失败] 模型调用失败：%s" % e)
            return 3
        mode = "llm"
    else:
        try:
            board = core.build_storyboard_offline(meta["idea"], genre, matched, scale, script,
                                                 profile=profile)
        except ValueError as e:
            print("[拒绝] %s" % e)
            return 2
        mode = "offline-skeleton"
    core.write(run / "04_分镜.md", board)
    issues = core.scan_text(board, stage="storyboard", m1_text=script) + _check_shots(board, int(scale.get("total_seconds") or 0))
    core.write(run / "04_selfcheck.txt", core.format_issues(issues))

    shots = core.parse_script(script)["shots"]
    total = int(scale.get("total_seconds") or 0)
    secs, tinfo = core.plan_shot_seconds(shots, total, allow_scale=False)
    sheet = "\n".join([
        "# 确认节点 B · 分镜确认清单", "",
        "- run：`%s`" % run,
        "- 剧本来源：`02_剧本草稿.locked.md`（%d 镜）" % len(shots),
        "- 生成方式：%s" % ("对话模型生成" if mode == "llm" else "离线工程骨架（镜数＝剧本段落数、秒数按内容推，措辞待润）"),
        "",
        "## 一、本次时长分配（每镜秒数由该镜画面与台词量推出；单镜 ≤15 秒，不设下限）",
        "| 镜号 | 秒数 | 段数 |", "| --- | --- | --- |",
    ] + ["| 镜 %d | %d | %d |" % (s["no"], secs[i], core.segment_count(s["picture"], secs[i]))
         for i, s in enumerate(shots)] + [
        "", "- 合计：%d 秒 / 目标 %d 秒 / 差额 %+d 秒" % (sum(secs), total, sum(secs) - total),
        "- 偏差口径：≤10%% 只做 ±1 秒取整；>10%% 回改剧本加戏或删戏，不压秒凑数。%s" % (
            tinfo.get("advice") or tinfo.get("note") or ""),
        "",
        "## 二、你可以改的 3 件事",
        "1. 改哪镜？（给镜号，我改完重跑自检：镜长/禁词/衔接）",
        "2. 台词要不要换？全片 %d 句，其中 %s 的口吻我最不确定" % (
            sum(len(s["lines"]) for s in shots),
            "、".join(sorted({ln["speaker"] for s in shots for ln in s["lines"]})[:2]) or "[角色]"),
        "3. 时长要不要调？现在按内容合计 %d 秒 / %d 镜" % (sum(secs), len(shots)),
        "",
        "## 怎么改",
        "- 在 `04_分镜.md` 上改，另存 `04_分镜.edited.md`，再执行 confirm B。",
        "",
        "## 确认命令",
        "```", "python tools\\storyboard.py confirm B --user-ok --run %s" % run, "```",
        "", "> 未执行 confirm B，阶段三一律拒绝执行。",
        "", "## 自检结果", "```", core.format_issues(issues).strip(), "```", "",
    ])
    core.write(run / "05_确认B.md", sheet)
    meta["stage"] = "storyboard_draft"
    meta["board_shots"] = len(shots)
    meta["board_mode"] = mode
    core.save_run(run, meta)

    print("[OK] 分镜已生成：%s" % (run / "04_分镜.md"))
    print("     %d 镜 / %d 秒 / 方式 %s / 自检问题 %d 处" % (len(shots), sum(secs), mode, len(issues)))
    print("     下一步：看 05_确认B.md，改完执行 confirm B")
    return 0


def cmd_stage3(args):
    meta = _guard(args.run, "confirmed_b")
    if meta is None:
        print("     说明：阶段三要求 confirmed_b=true（分镜已确认）。")
        return 2
    run = resolve_run(args.run)
    board_file = run / "04_分镜.locked.md"
    if not board_file.exists():
        print("[拒绝] 缺锁稿分镜：%s（请先 confirm B）" % board_file)
        return 2
    board = board_file.read_text(encoding="utf-8")
    script_file = run / "02_剧本草稿.locked.md"
    script = script_file.read_text(encoding="utf-8") if script_file.exists() else ""
    genre = core.GENRE_BY_ID[meta["genre"]]
    cards = core.parse_storyboard_cards(board, script)

    prompt = core.build_stage3_prompt(meta["idea"], genre, board, cards)
    core.write(run / "06_prompt.md", prompt)
    if args.llm:
        try:
            out = call_llm(prompt)
        except Exception as e:
            print("[失败] 模型调用失败：%s" % e)
            return 3
        mode = "llm"
    else:
        out = core.build_prompts_offline(meta["idea"], genre, board, script, cards)
        mode = "offline-skeleton"
    core.write(run / "06_提示词.md", out)
    issues = core.scan_text(out)
    core.write(run / "06_selfcheck.txt", core.format_issues(issues))

    sheet = "\n".join([
        "# 确认节点 C · 文生图提示词确认清单", "",
        "- run：`%s`" % run,
        "- 分镜来源：`04_分镜.locked.md`",
        "- 生成方式：%s" % ("对话模型生成" if mode == "llm" else "离线工程骨架（条数/⭐/负向已算好，属性待补）"),
        "",
        "## 交付清单",
        "- ⑦a 角色 %d 条｜⑦b 场景 %d 条｜⑦c 道具 %d 条" % (
            len(cards["chars"]), len(cards["scenes"]), len(cards["props"])),
        "- 每条都带负向清单；题眼道具标 ⭐",
        "",
        "## 待拍板三问（带本次实际值）",
        "1. 形象：%s 这 %d 个角色，按这份走还是换？" % (
            "、".join(c[0] for c in cards["chars"][:3]) or "[角色]", len(cards["chars"])),
        "2. 场景/道具：%s 共 %d 个场景、%s 共 %d 个道具，保留还是加？" % (
            "、".join((s["name"] if isinstance(s, dict) else s) for s in cards["scenes"][:3])
            or "[场景]", len(cards["scenes"]),
            "、".join(p[0] for p in cards["props"][:3]) or "[道具]", len(cards["props"])),
        "3. 改哪条？（给条号，我改完重跑自检）",
        "",
        "## 确认命令",
        "```", "python tools\\storyboard.py confirm C --user-ok --run %s" % run, "```",
        "", "> 确认即交付终点：画面生成、剪辑、发布不在本技能范围。",
        "", "## 自检结果", "```", core.format_issues(issues).strip(), "```", "",
    ])
    core.write(run / "07_确认C.md", sheet)
    meta["stage"] = "prompts_draft"
    meta["prompt_mode"] = mode
    core.save_run(run, meta)

    print("[OK] 提示词已生成：%s" % (run / "06_提示词.md"))
    print("     ⑦a %d / ⑦b %d / ⑦c %d / 方式 %s / 自检问题 %d 处" % (
        len(cards["chars"]), len(cards["scenes"]), len(cards["props"]), mode, len(issues)))
    print("     下一步：看 07_确认C.md，改完执行 confirm C")
    return 0


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(prog="storyboard", description="通用题材一句话分镜脚本系统 · M1 原型")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("doctor", help="环境与依赖自检")
    sub.add_parser("lint", help="爆款储备库体检")

    s1 = sub.add_parser("stage1", help="一句话 -> 剧本草稿")
    s1.add_argument("--idea", required=True)
    s1.add_argument("--duration", type=int, default=None, help="总秒数（用户指定则 100%% 服从）")
    s1.add_argument("--shots", type=int, default=None)
    s1.add_argument("--platform", default=None)
    s1.add_argument("--ratio", default=None)
    s1.add_argument("--real", action="store_true", help="现实/真人真事，启用真实底本流程")
    s1.add_argument("--ref", default=None, help="参照爆款作品（链接/名称/描述）")
    s1.add_argument("--llm", action="store_true", help="走 BYOK 模型生成正文（否则只出骨架）")
    s1.add_argument("--run", default=None, help="连续剧：整季目录，本集写进 该目录/EPnn/")
    s1.add_argument("--ep", type=int, default=0, help="连续剧：第几集（配合 --run）")

    sr = sub.add_parser("series", help="连续剧：一句话 -> 整季分集表 + 第 1 集剧本草稿")
    sr.add_argument("--idea", required=True)
    sr.add_argument("--episodes", type=int, default=None, help="集数（不给则按平台追更节奏推）")
    sr.add_argument("--duration", type=int, default=None, help="单集秒数（用户指定则 100%% 服从）")
    sr.add_argument("--shots", type=int, default=None, help="单集镜数")
    sr.add_argument("--platform", default=None)
    sr.add_argument("--ratio", default=None)
    sr.add_argument("--real", action="store_true")
    sr.add_argument("--ref", default=None)
    sr.add_argument("--llm", action="store_true")

    cf = sub.add_parser("confirm", help="确认节点")
    cf.add_argument("stage", choices=["A", "B", "C"])
    cf.add_argument("--run", required=True)
    cf.add_argument("--user-ok", action="store_true", help="用户已明确点头确认（缺此项直接拒绝）")

    sy = sub.add_parser("sync", help="成稿落盘后自动同步体检单／确认清单／自检结果；--all 收口全盘写稿单子")
    sy.add_argument("--run")
    sy.add_argument("--all", action="store_true", help="把盘上所有写稿单子按当前工具版本重出")

    s2 = sub.add_parser("stage2", help="剧本 -> 分镜（§8 框架）")
    s2.add_argument("--run", required=True)
    s2.add_argument("--llm", action="store_true", help="走 BYOK 模型出稿（否则出合规骨架）")
    s3 = sub.add_parser("stage3", help="分镜 -> 文生图提示词（§9 模板）")
    s3.add_argument("--run", required=True)
    s3.add_argument("--llm", action="store_true", help="走 BYOK 模型出稿（否则出合规骨架）")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    return {
        "doctor": cmd_doctor, "lint": cmd_lint, "stage1": cmd_stage1,
        "series": cmd_series,
        "confirm": cmd_confirm, "sync": cmd_sync,
        "stage2": cmd_stage2, "stage3": cmd_stage3,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
