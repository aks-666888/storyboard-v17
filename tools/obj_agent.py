# -*- coding: utf-8 -*-
# obj_agent.py —— 物件当施事检测（v2.9.34）
# 判据：一个分句里，物件名后面 12 字内出现动作用词，且该分句没有人物/身体部位施事，也没有「把/被/让/使/给/由」，
# 就算「物件自己会动」。这是高置信样例检测，不做全量语法分析。
import io, re, sys

OBJ = ['拖把', '抹布', '水痕', '水渍', '照片', '纸', '硬币', '抽屉', '锅盖', '锅', '伞骨', '伞面',
       '纸巾', '手机', '烟灰', '水汽', '反光', '顶灯', '灯泡', '雨水', '雨点', '帘布', '袖口',
       '指尖', '手指', '指缝', '杯壁', '币面', '热气', '螺丝刀', '纸杯', '后盖', '钟']
MOT = ['拖', '推', '拉', '滑', '落', '亮', '照', '抽', '压', '撞', '晃', '走', '进', '出', '停',
       '抖', '闪', '晕', '洇', '引', '框', '切', '砸', '滴', '转', '飘', '散', '弹', '划',
       '收', '挪', '贴', '抬', '降', '搬', '爬', '飞']
PERS = ['阿哲', '老周', '阿蓉', '他', '她', '谁', '手', '脚', '膝', '指尖上']
# 通用施事判据（v2.9.37）：「小满从抽屉里抽出…」这类句子，动作是人做的，
# 只是人名没写进上面那张表。介词结构前面还站着主语，就不能算物件自己会动。
# 靠人名白名单认施事，换一部新稿就误判，这是根因，不靠继续往表里加名字解决。
PREP = ('从', '在', '往', '向', '朝', '用', '拿', '隔着', '顺着', '沿着', '把', '将')
_PREP_STRIP = re.compile(u'从|在|往|向|朝|用|拿|隔着|顺着|沿着|把|将')
# 介词要按「独立使用」判：拖把／伞把／门把／锁把 里的「把」不是介词（v2.9.35 修）
SAFE_PAT = [u'(?<![拖伞门锁车手靶拉])把', u'被', u'让', u'使', u'给', u'由',
            u'跟着', u'顺着', u'沿着', u'往上', u'往下']
_SAFE = [re.compile(x) for x in SAFE_PAT]

def _pat(extra=None):
    """物件当施事的检测式：物件名表 + 本片自己登记的道具。
    每片道具不同，只靠固定物件表必然漏判新题材，所以本片道具也并进来。"""
    objs = list(OBJ)
    for it in (extra or []):
        if it and it not in objs:
            objs.append(it)
    return re.compile(u'(?:%s)[^，。；！？]{0,12}?(?:%s)' % (u'|'.join(objs), u'|'.join(MOT)))


def offenders(text, skip_prefix=('#', '-', '**镜', '|', '>'), extra=None):
    out = []
    for line in text.split(u'\n'):
        s = line.strip()
        if not s or s.startswith(skip_prefix):
            continue
        for cl in re.split(u'[。；！？，]', s):
            cl = cl.strip()
            if not cl:
                continue
            m = _pat(extra).search(cl)
            if not m:
                continue
            head = cl[:m.start()]
            if any(p in head for p in PERS):
                continue
            if any(r.search(cl) for r in _SAFE):
                continue
            # 介词前还有内容＝前面站着主语（多半是人名），动作是人发出的
            if any(p in head for p in PREP) and _PREP_STRIP.sub(u'', head).strip():
                continue
            out.append((cl[:40], m.group(0)))
    return out


def self_test():
    """换个新名字也不能误报；没人做动作的物件仍要拦下。"""
    good = [u"小满从抽屉里抽出退件登记簿，摊在纸包旁边。",
            u"赵明远用左手把存根推到柜台上。",
            u"阿蓉从绒布上拿起螺丝刀。"]
    bad = [u"抽屉里抽出一叠取件条。",
           u"抹布在台面上滑过去。"]
    ok = (not any(offenders(t) for t in good)
          and all(offenders(t) for t in bad))
    print(u"物件施事自测：%s（新人名放行 %d 条，物件自动 %d 条拦下）"
          % (u"通过" if ok else u"未过", len(good), len(bad)))
    return 0 if ok else 1


if __name__ == '__main__':
    if '--test' in sys.argv:
        sys.exit(self_test())
    for p in sys.argv[1:]:
        t = io.open(p, encoding='utf-8').read()
        try:
            import craft_chk
            extra = craft_chk._props(p)
        except Exception:
            extra = None
        hits = offenders(t, extra=extra)
        print(u'%s：%d 处' % (p.split('\\')[-1], len(hits)))
        for cl, w in hits:
            print(u'    「%s」  ← %s' % (cl, w))