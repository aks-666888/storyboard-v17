# -*- coding: utf-8 -*-
"""从散文里读出「取景」与「光影」——中英对照术语与中文人话说法都认。

用于 M2 新要求硬检 N4（相邻取景重复）/ N5（光影无变化）：按用户规范，
取景／运镜／构图／光影四项用中英对照专业术语写进句子，术语本身也要能归桶，
所以词表同时收英文原词、中文释义和纯中文画面说法。
"""
import re


# ---- 专业术语（用户给定规范：景别/视角/运镜/光位中英对照，写进散文也算数） ----
TERM_DIST = [(u"极", u"Extreme Long Shot|极远景|大远景|Bird's-Eye|鸟瞰"),
             (u"远", u"Long Shot|大全景|远景"),
             (u"全", u"Full Shot|全景|中全景|Medium Long Shot"),
             (u"中", u"Medium Shot|中景|Cowboy|牛仔镜头"),
             (u"近", u"Medium Close-Up|中近景|Close-Up|近景|Two Shot|双人镜头|Over-the-Shoulder|过肩"),
             (u"特", u"Big Close-Up|Extreme Close-Up|大特写|特写|Insert|插入")]
TERM_ANGLE = [(u"俯", u"High Angle|高俯视角|Overhead Shot|顶俯|Bird's-Eye|鸟瞰|俯拍"),
              (u"仰", u"Low Angle|低仰视角|Worm's-Eye|虫眼|仰拍|Extreme Low"),
              (u"侧", u"Profile Shot|正侧|Three-Quarter|四分之三|侧拍|斜侧"),
              (u"背", u"Reverse Shot|反打|过肩|背后|后脑"),
              (u"斜", u"Dutch Angle|荷兰角|Oblique Shot|斜角"),
              (u"平", u"Eye-Level|平视视角|平拍|正面|POV|主观视角")]
TERM_MOVE = (u"Dolly In|Dolly Out|Truck Left|Truck Right|Pedestal Up|Pedestal Down|Tilt Up|Tilt Down|"
             u"Pan Left|Pan Right|Arc Shot|Orbit Shot|Circular Tracking|Follow Shot|Whip Pan|Vertigo Effect|"
             u"Spielberg Push|Crane Up|Crane Down|Static Hold|Long Take|Handheld Motion|Shaky Cam|"
             u"Through Frame|Flythrough|Creep Shot|Slow Drift|Glide Shot|Rack Focus|Pull Focus|Parallax Motion|"
             u"推镜|拉镜|横移|升降|仰摇|俯摇|摇镜|甩摇|环绕|跟拍|跟随|变焦|推近|拉远|停住|定格")


# 取景：距离桶（贴/近/中/远）
DIST = [
    ("贴", u"只框住|只剩|半张脸|一只眼|一根手指|指节|嘴角|眼皮|刀口|锁孔|一道缝"),
    ("近", u"肩膀以上|半身|到胸口|离他两步|离她两步|一步远|脸对着|脸上|脖子以上"),
    ("中", u"腰以上|全身|连人带门|连人带车|三四步|三步远|门口站|站在院里"),
    ("远", u"院子|一条街|整座|远处|大景|把人放小|屋外|村口|山坡上|路口"),
]
# 取景：角度桶
ANGLE = [
    ("俯", u"从上往下|从上面|头顶上|往下看"),
    ("仰", u"从下往上|蹲低|仰"),
    ("侧", u"侧后|斜侧|从侧面|侧身对着|半个侧脸"),
    ("背", u"背后|后脑|跟在他身后|跟在她身后|从后面"),
    ("平", u"平着看|齐眉|平视|正面|门外侧|门左前方|从门口往里|对着他"),
]

# 光影：光源词（出现即记，用来比相邻镜是否同一套）
LIGHT = [
    u"窗光", u"月光", u"路灯", u"油灯", u"煤油灯", u"灯泡", u"吊灯", u"顶灯", u"灯管",
    u"火光", u"灶火", u"柴火", u"手电", u"车灯", u"手机屏", u"屏幕光", u"日光",
    u"天光", u"黄昏", u"灯", u"逆光", u"影子", u"反光", u"灯罩", u"台灯", u"应急灯",
    u"走廊灯", u"声控灯", u"楼道灯", u"冷白", u"暖黄", u"荧光",
    u"Key Light", u"Fill Light", u"Rim Light", u"Backlight", u"Side Light",
    u"Top Light", u"Underlight", u"Catchlight", u"Practical Light", u"Hard Light",
    u"Soft Light", u"主光", u"辅光", u"轮廓光", u"逆光", u"侧光", u"顶光", u"底光", u"眼神光",
]


# 运镜：画面怎么动（人话，不许写「运镜/镜头」这类术语）
MOVE_HINT = re.compile(u"(画面|视线|画框|取景)[^。，；]{0,12}"
                      u"(推近|推上去|拉远|拉开|摇过|摇到|横移|平移|跟过去|跟上|跟住|"
                      u"升起|降下|往下压|抬|贴上去|退开|绕|甩|停住|定住|落下|扫过|滑过)")
MOVE_WORD = re.compile(u"推近|拉远|横移|平移|摇过|摇到|绕圈|绕着转|贴上去|退开|停住|定住|往下压")


def motion_ok(prose):
    """这一镜有没有写清楚画面怎么动：专业术语与人话都认。"""
    return bool(re.search(TERM_MOVE, prose, re.I) or MOVE_HINT.search(prose) or MOVE_WORD.search(prose))


def frame_code(prose):
    """返回 (距离桶, 角度桶)；先认专业术语，再认人话描述词。"""
    d = None
    for name, pat in TERM_DIST:
        if re.search(pat, prose, re.I):
            d = name
            break
    a = None
    for name, pat in TERM_ANGLE:
        if re.search(pat, prose, re.I):
            a = name
            break
    if d is not None and a is not None:
        return (d, a)
    for name, pat in DIST:
        if re.search(pat, prose):
            d = name
            break
    a = None
    for name, pat in ANGLE:
        if re.search(pat, prose):
            a = name
            break
    if d is None and a is None:
        return None
    return (d, a)


def light_set(prose):
    return set(w for w in LIGHT if w in prose)


def self_test():
    """命令行 --test：术语写法与人话写法都能判，运镜判据不放水。"""
    cases = [
        (u"专业术语能判取景与角度",
         frame_code(u"Medium Close-Up 中近景，Low Angle 低仰视角") == (u"近", u"仰")),
        (u"人话能判取景与角度",
         frame_code(u"只框住他一只手和半扇门，从下往上看") == (u"贴", u"仰")),
        (u"人话能判光影", light_set(u"月光落在台阶上") == {u"月光"}),
        (u"专业术语能判光影", u"Key Light" in light_set(u"Key Light 主光打在脸上")),
        (u"人话能判画面怎么动", motion_ok(u"画面慢慢推近，他推开门")),
        (u"专业术语能判画面怎么动", motion_ok(u"Dolly In 推镜，他站着")),
        (u"没写画面怎么动不放行", not motion_ok(u"他推开门站着，把灯拧亮")),
    ]
    bad = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(u"[%s] %s" % (u"PASS" if ok else u"FAIL", n))
    print(u"结论：%d/%d 通过" % (len(cases) - len(bad), len(cases)))
    return 1 if bad else 0


if __name__ == "__main__":
    import io, sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(self_test())
    if len(sys.argv) > 1:
        t = io.open(sys.argv[1], encoding="utf-8").read()
        print(u"取景：%s" % (frame_code(t),))
        print(u"光影：%s" % (u"／".join(sorted(light_set(t))),))
        sys.exit(0)
    print(u"用法：frame_parse.py <文档.md>  或  frame_parse.py --test")
