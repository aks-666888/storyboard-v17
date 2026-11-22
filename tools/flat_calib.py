# -*- coding: utf-8 -*-
"""平淡阈值校准（flat_calib）：把现有全部稿件跑一遍 scan_flat，报命中率与分布。
用途：判断 13J 的阈值是偏严（乱杀）还是偏松（放水），并有据可查地调。
用法：python flat_calib.py [目录]
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flat_check as fc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")


def collect(base):
    items = []
    for dirpath, _dirs, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            if fn.startswith("02_"):
                items.append((os.path.join(dirpath, fn), "m1"))
            elif fn.startswith("04_") and fn.endswith(".md"):
                items.append((os.path.join(dirpath, fn), "m2"))
    return sorted(items)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else OUT
    items = collect(base)
    kinds = {}
    flagged = 0
    total = 0
    for path, stage in items:
        t = io.open(path, encoding="utf-8").read()
        if "待填" in t:
            continue
        total += 1
        hits = fc.scan_flat(t, stage)
        for _i, k, _s in hits:
            kk = k.split(u"（")[0]
            kinds[kk] = kinds.get(kk, 0) + 1
        if hits:
            flagged += 1
            rel = os.path.relpath(path, ROOT)
            print(u"[%d 处] %s  %s" % (len(hits), stage, rel))
            for i, k, s in hits[:3]:
                print(u"     L%s %s：%s" % (i, k, s[:40]))
    print(u"\n共扫 %d 份，命中 %d 份（%.0f%%）" % (total, flagged, (flagged * 100.0 / total) if total else 0))
    for k in sorted(kinds, key=lambda x: -kinds[x]):
        print(u"  %s：%d 处" % (k, kinds[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
