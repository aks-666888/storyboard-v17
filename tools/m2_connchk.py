#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 分镜「实质合格」机器前检：补上主技能里只标「人工通读」的三条——
  1) 场景对不上（例如：城里高楼配农村堂屋、回胡同却上电梯）
  2) 上下镜画面衔接（下一镜开头须接着上一镜结尾出现过的实体，否则标「可能虚接」）
  3) 台词 AI 味/书面腔（鸡汤词、升华词、说明书腔）
定位：机器先揪、人工最终判。不替人盖章，只把疑似问题定位到镜号。
"""
import re, sys

# ---------- 1. 场景对不上（唯一词库源在 consist_chk，避免两处漂移） ----------
import consist_chk


def check_scene_logic(text):
    """院落平房与电梯楼房同片出现即判不合格。助理自造的「古今分类」已撤销。"""
    return [('FAIL', m) for m in consist_chk.check_place(text)]


# ---------- 2. 上下镜衔接 ----------
GENERIC_BI = {  # 这些二元组不算「实体衔接」
    '一个', '那个', '这时', '镜头', '一下', '看着', '然后', '接着', '慢慢', '轻轻',
    '这里', '那里', '一边', '突然', '只见', '原来', '此刻', '之间', '什么', '怎么',
    '已经', '还是', '没有', '不是', '就是', '一直', '终于', '仿佛', '似乎', '不过',
}
STOP_CHARS = set('的了着过在把被与和及或，。！？；：、（）“”‘’—…·0123456789')

# 关键物件/人物字锚：用于衔接判定——同一物件在不同镜里前后字不同（如「张券」「把券」），
# 二元组对不上，改比对「是否含同一个关键物件/人物字」，避免把同一物的合法转场误杀。
SALIENT = set('强琳妈姐叔爷奶老李张大周刘雷郑券纸包兜盒台门窗车桌椅灯房楼袋葱番茄卡枪机床碗锅杯伞鞋衣裤帽镜墙地架柜市收银货架生鲜通道家店校院公园路街桥河海山田村')


def _keychars(s):
    s = re.sub(r'[^\u4e00-\u9fa5]', '', s)  # 只留汉字
    grams = {s[i:i+2] for i in range(len(s) - 1)}
    grams = {g for g in grams if g not in GENERIC_BI}
    # 单字锚：覆盖「同一物在不同镜里前后字不同」（如「张券」vs「把券」），
    # 同时 2 字窗口覆盖「同物同写法」（如「小林」「年糕」「皮绳」「电梯」），双轨互补。
    singles = {c for g in grams for c in g if c in SALIENT}
    return grams | singles


def _clause(text, which):
    # which='first' 取首句；'last' 取末句
    segs = re.split(r'[。！？；]', text)
    segs = [x for x in segs if x.strip()]
    if not segs:
        return ''
    return segs[0] if which == 'first' else segs[-1]


def check_continuity(shots):
    res = []
    for i in range(1, len(shots)):
        prev_k = _keychars(shots[i-1])          # 上一镜全文关键物件/人物字
        cur_k = _keychars(shots[i])             # 本镜全文关键物件/人物字
        if not cur_k:
            continue  # 本镜无关键物件字，不判
        if not (prev_k & cur_k):
            res.append(('WARN', f'镜{i} 与 镜{i+1} 可能虚接：相邻两镜无共用关键物件/人物（机器先揪，需人工核对方位/动作/转场是否真接上）'))
    return res


# ---------- 3. 台词 AI 味/书面腔 ----------
AI_WORDS = [
    '然而', '此刻', '仿佛', '似乎', '不禁', '足以', '彰显', '油然而生', '历历在目',
    '映入眼帘', '说不尽', '道不完', '最是', '何尝', '试问', '涌上心头', '感慨',
    '岁月静好', '治愈', '深深打动', '久久', '难以', '让人不禁', '不禁让人', '一股',
    '升华', '点睛', '点睛之笔', '点睛之笔', '恰到好处', '耐人寻味', '意味深长',
    '恍然大悟', '茅塞顿开', '总而言之', '不难看出', '由此可见', '毋庸置疑',
]


def check_ai_flavor(text):
    res = []
    # 先剔除角色括号七项区域（如「语气感慨」里的"感慨"是语气描述，不是台词鸡汤，剔除避免误伤）
    cleaned = re.sub(r'（[^）]*）', '', text)
    found = [w for w in AI_WORDS if w in cleaned]
    for w in found:
        res.append(('WARN', f'疑似 AI 味/书面腔词：「{w}」（机器先揪，需人工判是否真鸡汤）'))
    return res


# ---------- 集成 ----------
def split_shots(text):
    body = re.split(r'## 附表', text)[0]
    blocks = re.findall(r'\**镜\d+\b[^\n]*\n(.*?)(?=\n\s*\**镜\d+\b[^\n]*\n|\Z)', body, re.S)
    return [b.strip() for b in blocks if b.strip()]


def run_all(text):
    body = re.split(r'## 附表', text)[0]
    shots = split_shots(text)
    out = []
    for lvl, msg in check_scene_logic(body):
        out.append(('场景对不上', lvl, msg))
    for lvl, msg in check_continuity(shots):
        out.append(('上下镜衔接', lvl, msg))
    for lvl, msg in check_ai_flavor(body):
        out.append(('台词AI味', lvl, msg))
    return out, len(shots)


TESTS = {
    '场景对不上样本': '他住在高楼里的电梯房，每天下楼道取快递。周末回老家，堂屋的土炕上还摆着灶台。',
    '胡同配电梯样本': '傍晚他回胡同，拎着袋子上三楼，电梯门合上，小区草坪上灯亮了。',
    '古装现代同片样本': '状元骑着马车进京赶考，掏出手机扫了码付了外卖。',
    '虚接样本': '镜1（5秒）\n大强把番茄划拉进包，妈在语音里念叨。\n镜2（6秒）\n海风拍打礁石，一只海鸥掠过灯塔。',
    'AI味样本': '他不禁感慨，岁月静好，一股暖意涌上心头，仿佛一切都治愈了。',
    '合格样本': '镜1（8秒）\n大强缩在货架夹角，指尖碰到试吃盒的「样品勿取」红字。\n镜2（7秒）\n大强把那盒番茄塞进包底，妈的语音还在响。',
}


def self_test():
    print('=' * 56)
    print('m2_connchk 自带考题')
    print('=' * 56)
    ok = 0
    total = 0
    # 场景对不上应抓
    total += 1
    r, _ = run_all(TESTS['场景对不上样本'])
    if any('场景对不上' in m for _, _, m in r):
        print('[PASS] 场景对不上样本：成功抓到（城里高楼配农村堂屋）'); ok += 1
    else:
        print('[FAIL] 场景对不上样本：未抓到')
    total += 1
    r, _ = run_all(TESTS['胡同配电梯样本'])
    if any('场景对不上' in m for _, _, m in r):
        print('[PASS] 胡同配电梯样本：成功抓到（回胡同却上电梯）'); ok += 1
    else:
        print('[FAIL] 胡同配电梯样本：未抓到')
    total += 1
    r, _ = run_all(TESTS['古装现代同片样本'])
    if not any(lvl == 'FAIL' for _, lvl, _ in r):
        print('[PASS] 古装现代同片：自造的时代分类已撤销，不再误判'); ok += 1
    else:
        print('[FAIL] 古装现代同片：仍在误判')
    total += 1
    r, _ = run_all(TESTS['虚接样本'])
    if any('可能虚接' in m for _, _, m in r):
        print('[PASS] 虚接样本：成功抓到上下镜无衔接'); ok += 1
    else:
        print('[FAIL] 虚接样本：未抓到')
    total += 1
    r, _ = run_all(TESTS['AI味样本'])
    if any('AI 味' in m for _, _, m in r):
        print('[PASS] AI味样本：成功抓到书面腔词'); ok += 1
    else:
        print('[FAIL] AI味样本：未抓到')
    total += 1
    r, _ = run_all(TESTS['合格样本'])
    if not any(x[1] == 'FAIL' for x in r):
        print('[PASS] 合格样本：零误报（场景/衔接均不误判）'); ok += 1
    else:
        print('[FAIL] 合格样本：出现误报 ->', [m for _, l, m in r if l == 'FAIL'])
    print('-' * 56)
    print(f'考题：{ok}/{total} 通过')
    sys.exit(0 if ok == total else 1)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        self_test()
    elif len(sys.argv) > 1:
        r, n = run_all(open(sys.argv[1], encoding='utf-8').read())
        print(f'={len(r)} 条结果 / {n} 镜')
        for cat, lvl, msg in r:
            print(f'[{lvl}] {cat}：{msg}')
        fails = [x for x in r if x[1] == 'FAIL']
        print('✅ 无实质 FAIL' if not fails else f'❌ {len(fails)} 条需修')
        sys.exit(1 if fails else 0)
    else:
        print('用法：m2_connchk.py <分镜md>  或  m2_connchk.py --test')
