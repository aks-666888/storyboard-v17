# -*- coding: utf-8 -*-
"""成稿回归检查：结构禁词 + 人话句法 + 假因果，一次跑完。
用法：python human_regress.py <稿件路径.md> [目标总时长]
退出码 0 = 0 处问题；1 = 有待修。
"""
import sys, io, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sb_core as core
import check_prose


def main():
    if len(sys.argv) < 2:
        print("用法：python human_regress.py <稿件路径.md> [目标总时长]")
        return 2
    path = sys.argv[1]
    target = float(sys.argv[2]) if len(sys.argv) > 2 else None
    text = io.open(path, encoding="utf-8").read()
    bad_advice = 0

    st = core.scan_text(text)
    hu = core.scan_human(text)
    be = core.scan_beat(text)
    cap = []
    man_path = os.path.join(os.path.dirname(os.path.abspath(path)), u"能力清单.json")
    if os.path.exists(man_path):
        man = json.load(io.open(man_path, encoding="utf-8"))
        cap = core.scan_capability(text, man)
    trade = u""
    trade_path = os.path.join(os.path.dirname(os.path.abspath(path)), u"行当.txt")
    if os.path.exists(trade_path):
        trade = io.open(trade_path, encoding="utf-8").read().strip()
    cs = core.scan_commonsense(text, trade)
    print("成稿回归：%s" % os.path.basename(path))
    print("  scan_text 结构禁词：%d 处" % len(st))
    for it in st:
        print("    L%s [%s] %s" % (it[0], it[1], str(it[2])[:40]))
    print("  scan_human 人话句法：%d 处" % len(hu))
    for it in hu:
        print("    L%s [%s] %s" % (it[0], it[1], it[2][:40]))
    print("  scan_capability 能力清单：%d 处" % len(cap))
    for it in cap:
        print("    段%s [%s] %s" % (it[0], it[1], it[2]))
    print("  scan_commonsense 行当常识：%d 处" % len(cs))
    for it in cs:
        print("    第%s 行 [%s] %s" % (it[0], it[1], it[2]))
    print("  scan_beat 整段空转：%d 处" % len(be))
    for it in be:
        print("    段%s [%s] %s ｜ %s" % (it[0], it[1], it[2], it[3]))
    pr = check_prose.scan_prose(text)
    print("  scan_prose 句法文体：%d 处" % len(pr))
    for it in pr:
        print("    L%s [%s] %s" % (it[0], it[1], it[2]))
    groups = {}
    for it in hu:
        groups[it[1]] = groups.get(it[1], 0) + 1
    for k, v in sorted(groups.items()):
        print("    - %s：%d" % (k, v))

    try:
        shots = core.parse_script(text)["shots"]
        print("  段落数：%d" % len(shots))
        if target:
            secs, info = core.plan_shot_seconds(shots, target, 0.10, False)
            print("  配时：合计 %d 秒 / 目标 %d 秒 / 最长 %d 秒" % (sum(secs), int(target), max(secs)))
            print("  说明：%s" % info.get("note", ""))
            if info.get("advice"):
                print("  !! %s" % info["advice"])
                bad_advice = 1

    except Exception as e:
        print("  段落解析跳过：%s" % e)

    bad = len(st) + len(hu) + len(be) + len(cap) + len(cs) + len(pr) + bad_advice
    print("结论：%s" % ("通过（0 处）" if bad == 0 else "待修 %d 处" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
