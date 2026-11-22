# -*- coding: utf-8 -*-
"""连续剧（多集）形态的规格推导：集数 / 单集时长 / 每集功能 / 尾钩类型 / 中爆点位置。

设计原则与单片一致：不写死任何数值，集数与单集时长由「本次输入 + 本次匹配到的同类爆款」
现算；用户给了数就 100% 服从。
"""

SERIES_HOOKS = [
    "身份揭示（观众先知道，角色还不知道）",
    "物件出现（一个不该出现在这里的东西）",
    "一句话反转（上一集被当成真的事被推翻）",
    "危险逼近（下一集必然发生的坏事只露出一角）",
    "决定留白（角色做一个选择，结果不拍）",
]

SERIES_RULES = [
    "单集必须自闭环：本集内起—承—转—爆—收齐全，追更观众只看这一集也能看懂。",
    "集尾必须有一个尾钩，五种类型轮换，不许连续两集同型；尾钩只给一半信息，不给答案。",
    "跨集不用旁白回顾：每集第一个镜头用上集留下的可见物接（伤口/道具/环境变化），且不重复上集的取景与物件组合。",
    "人物状态跨集连续：伤、衣、时间、道具位置都要能对上；上一集丢的东西这一集不能凭空回来。",
    "角色卡 / 场景卡 / 道具卡整季只建一次，跨集复用同一套描述（锁脸、锁场景结构、锁道具外观）。",
    "中爆点每 3–5 集一个，位置由本季总集数现算；不要每集都爆，爆点之间要有加压段。",
    "第 1 集前 15 秒必须同时立住主角与冲突；最后一集收主弧、留副线，不解释全部。",
]


def plan_series(genre, matched, profile, episodes=None, per_ep_duration=None,
                shots=None, platform=None):
    """返回整季规格 + 每集功能表。episodes 缺省时按平台追更节奏推，并写明依据。"""
    from sb_core import suggest_scale

    ep_scale = suggest_scale(genre, matched=matched, duration=per_ep_duration,
                             shots=shots, profile=profile)
    per_ep = int(ep_scale["total_seconds"])
    # 镜数不预设：整季表只给粗估（按每段约 8 秒），真实镜数由该集剧本切段得出
    per_ep_shots = int(ep_scale.get("shots") or max(1, int(round(per_ep / 8.0))))

    if episodes:
        n = int(episodes)
        ep_basis = "用户指定 %d 集" % n
    else:
        plat = platform or genre.get("platform") or ""
        n = 12 if any(k in plat for k in ("红果", "番茄", "短剧")) else (8 if "B站" in plat else 10)
        ep_basis = "平台追更节奏推定 %d 集（%s 类常见整季量级；用户可改）" % (n, plat or "未标注平台")

    rows = []
    for i in range(n):
        ratio = (i + 1) / float(n)
        if i == 0:
            func = "立人物 + 立冲突：本集末必须让观众知道主角要什么、谁挡着"
        elif ratio < 0.5:
            func = "加压一档：阻力升级（每集只升一档，别把牌一次打完）"
        elif ratio < 0.8:
            func = "换阵营 / 真相露一半：把上一集的认知推翻一格"
        elif i < n - 1:
            func = "把最大代价摆上桌：让主角为选择付一次真代价"
        else:
            func = "收主弧 + 留副线：主矛盾了结，留一个可续的缺口，不解释全部"
        mid = (i > 0) and (i % 4 == 0) and (i < n - 1)
        rows.append({
            "ep": i + 1,
            "seconds": per_ep,
            "shots": per_ep_shots,
            "function": func,
            "hook": SERIES_HOOKS[i % len(SERIES_HOOKS)],
            "mid": "中爆点" if mid else "",
        })

    return {
        "episodes": n, "ep_basis": ep_basis,
        "per_ep_seconds": per_ep, "per_ep_shots": per_ep_shots,
        "season_seconds": per_ep * n,
        "ep_scale": ep_scale,
        "rows": rows,
        "hooks": SERIES_HOOKS,
        "rules": SERIES_RULES,
    }


def build_series_outline(idea, genre, plan, matched=None):
    """整季分集表（Markdown）。表格只放可执行信息，不写剧情成稿。"""
    lines = [
        "# 分集表（整季骨架 · 供确认节点 A）",
        "",
        "- 一句话主题：%s" % idea,
        "- 识别题材：%s（%s）" % (genre["name"], genre["id"]),
        "- 形态：连续剧（多集），整季 %d 集 / 单集 %d 秒 / 单集 %d 镜 / 整季 %d 秒" % (
            plan["episodes"], plan["per_ep_seconds"], plan["per_ep_shots"], plan["season_seconds"]),
        "- 集数依据：%s" % plan["ep_basis"],
        "- 单集规格依据：%s" % plan["ep_scale"].get("basis", ""),
        "",
        "## 每集功能与尾钩",
        "",
        "| 集 | 单集秒数 | 镜数 | 本集一句话功能 | 集尾尾钩类型 | 标记 |",
        "|---|---|---|---|---|---|",
    ]
    for r in plan["rows"]:
        lines.append("| EP%02d | %d | %d | %s | %s | %s |" % (
            r["ep"], r["seconds"], r["shots"], r["function"], r["hook"], r["mid"]))
    lines += [
        "",
        "## 整季弧线",
        "- 季弧：起（EP01 立人立冲突）— 承（加压、换阵营）— 转（真相露一半 + 中爆点）— 爆（最大代价）— 收（收主弧留副线）。",
        "- 中爆点位置：%s（按本季 %d 集现算，每 4 集一个，落在中段）。" % (
            "、".join("EP%02d" % r["ep"] for r in plan["rows"] if r["mid"]) or "本季过短，不设中爆点",
            plan["episodes"]),
        "",
        "## 连续剧硬律（逐条过，不过就改）",
    ]
    lines += ["%d. %s" % (i + 1, s) for i, s in enumerate(plan["rules"])]
    lines += [
        "",
        "## 资产复用（整季只建一次，跨集同一套描述）",
        "- 角色卡：整季固定，跨集不加不换；确需新增角色，在该集剧本里标注「新增」并在分集表补一行。",
        "- 场景卡：同一场景跨集复用同一套空间锁定 / 光影基调 / 材质；换季、换时间才换描述。",
        "- 道具卡：题眼道具整季唯一，跨集出现必须是同一件（同缺口、同污渍、同标签）。",
        "",
        "> 本表是骨架：每集的具体剧情、台词、分镜在确认节点 A 通过后逐集生成，不在这里写死。",
    ]
    return "\n".join(lines)
