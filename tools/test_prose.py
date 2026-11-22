# -*- coding: utf-8 -*-
import io, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_prose as cp

NEG = [
 u"石墩边一圈油渍。老陈蹲着。",
 u"灯罩里是黑的。",
 u"段 3 老陈进屋，点灯。",
 u"面馆后厨，热气。碗堆着。",
 u"快递站门口，一排三轮。",
 u"医院走廊，半明的灯。",
 u"灯罩里没有一丝光。",
 u"那盏玻璃罩灯立在石墩上。",
 u"村口，夜里。\n\n他蹲着。",
 u"后厨的案板上摆着一排碗，刀靠在锅边。",
]
POS = [
 u"老陈蹲下去，把抹布沿着石墩边往里擦，擦过的地方留下一道浅印。",
 u"面馆后厨的蒸汽把窗糊住，他把面勺伸进锅里翻了两下，捞起来甩了甩水。",
 u"汽修厂里，学徒把拖车绳解开，绳子在地上团成一小堆。",
 u"快递站门口停着三辆三轮，他挑最近那辆，把车斗里的件往边上挪了挪。",
 u"白板上的人名被人擦掉两个，他站在那儿看了会儿，把笔帽扣上。",
 u"医院走廊的灯只开了一半，他扶着墙走到尽头，把那袋片子放在椅子上。",
 u"门从外面被人推开，他侧身让开半步，等那人进来才把门带上。",
 u"他从案板上拿起一只碗，指头在碗沿转了半圈，把水甩进池子里。",
]
ok = True
for c in NEG:
    h = cp.scan_prose(c)
    print((u"[%s] 反例 %d 处：%s" % (u"PASS" if h else u"FAIL", len(h), c)))
    ok = ok and bool(h)
for c in POS:
    h = cp.scan_prose(c)
    print((u"[%s] 正例 %d 处：%s" % (u"PASS" if not h else u"FAIL", len(h), c)))
    if h:
        for it in h: print(u"    -> [%s] %s" % (it[1], it[2]))
    ok = ok and not h
print(u"结论：%s（%d 例）" % (u"全部通过" if ok else u"有失败", len(NEG) + len(POS)))
sys.exit(0 if ok else 1)
