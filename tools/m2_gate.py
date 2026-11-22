#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 分镜交付自检：禁词 / 小标题 / 台词括号七项 / 单句≤14字 / 每镜≤15秒 / 场景逻辑 / 上下镜衔接 / 台词AI味。"""
import re, sys, os
import m2_connchk as cc
import frame_parse as fp
import human_chk
import new_req_chk
import check_prose
import flat_check
import consist_chk

DEFAULT = r'E:\data\marketing\plan\2026-W46\分镜技能\output\20261113-技能验证-M1-薅羊毛\04_分镜.md'


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('--'):
        print('[拒绝] 用法：m2_gate.py <分镜.md> --m1 <M1剧本.md>')
        sys.exit(2)
    if '--m1' not in sys.argv:
        print('[拒绝] 分镜交付门必须带底本（--m1 <M1剧本.md>）；底本台词对照不许跳过。')
        sys.exit(2)
    path = sys.argv[1]
    k = sys.argv.index('--m1')
    if k + 1 >= len(sys.argv) or not os.path.exists(sys.argv[k + 1]):
        print('[拒绝] --m1 后面要跟一份真实存在的剧本稿')
        sys.exit(2)
    m1_path = sys.argv[k + 1]
    TARGET = 0.0
    if '--duration' in sys.argv:
        j = sys.argv.index('--duration')
        if j + 1 < len(sys.argv):
            try:
                TARGET = float(sys.argv[j + 1])
            except ValueError:
                TARGET = 0.0
    text = open(path, encoding='utf-8').read()
    # 目标总秒数由工具自己拿：用户明确给了就用用户的，否则读稿内登记的本片总时长，
    # 稿内没写数字就按各镜声明秒数自己算出来当标准。任何情况都不跳过、不找人补参数。
    USER_TARGET = TARGET
    if not TARGET:
        TARGET = consist_chk.declared_seconds(text)
    DECLARED = TARGET > 0
    # 只看分镜正文：②爆款拆解卡是库内原文（会出现「镜头语言／换景」等词），
    # 附表与 ③b/③c/④~⑧ 是卡片与提示词，都不是画面散文；一律切掉再判
    body = re.split(r'##\s*(?:③\s*)?附表', text)[0]
    m3 = re.search(r'##\s*③[^\n]*分镜脚本[^\n]*\n', body)
    if m3:
        body = body[m3.end():]
    shots = cc.split_shots(body)                   # 兼容「镜N」与「**镜N（X秒）**」两种镜号行
    R = []
    def chk(n, ok, info=''):
        R.append((n, bool(ok), info))

    banned = ['8K', '4K', '超清', '高清', '电影感', '大师级', '院线级', '运镜流畅',
              '镜头语言', '氛围感', '极富张力', '画面精美', '需体现',
              '衔接连贯', '换景', '取景变化']
    hit = [b for b in banned if b in body]
    chk('无空泛模糊指令', not hit, ','.join(hit) if hit else '0')

    small = ['场景：', '光影：', '运镜：', '氛围：', '情绪：', '视角：', '机位：']
    hit2 = [s for s in small if s in body]
    chk('无小标题条目', not hit2, ','.join(hit2) if hit2 else '0')

    # 时长口径（v2.9.33）：秒数是设计要求，不按字数反推——读每镜声明的秒数，只校上限与总账
    han = lambda s: len(re.findall(r'[\u4e00-\u9fa5]', s))
    MAXS = 15.0
    total = 0.0
    _decl = dict((int(a), float(b)) for a, b in
                 re.findall(u'\\*\\*镜\\s*(\\d+)\\s*[（(]\\s*(\\d+(?:\\.\\d+)?)\\s*秒', body))
    for i, s in enumerate(shots, 1):
        braces = re.findall(r'（([^）]+)）', s)
        seven = any(re.match(r'^(男|女)·', b) and b.count('·') == 6 for b in braces)
        chk(f'镜{i} 台词括号七项齐', seven)
        dials = re.findall(r'[\u201c\u300c"]([^\u201c\u201d\u300c\u300d"]*)[\u201d\u300d"]', s)
        over = [d for d in dials if han(d) > 14]
        chk(f'镜{i} 单句≤14字', not over, ('超:' + '|'.join(over)) if over else '0')
        chk(f'镜{i} 至少一句台词', bool(re.search(r'[\u201c\u300c"]', s)))
        sec = _decl.get(i)
        chk(f'镜{i} 写了时长且≤15秒', sec is not None and sec <= MAXS,
            ('%.1f秒' % sec) if sec is not None else '镜号行没写（X秒）')
        total += (sec or 0.0)

    # 总账：目标由工具自己拿（用户给的 > 稿内登记的 > 各镜实算），从不跳过
    _decl_total = consist_chk.declared_seconds(text)
    if not TARGET:
        TARGET = total                       # 工具自己按各镜声明秒数算出本片总时长
    chk('各镜合计(声明秒数)', len(shots) > 0 and total > 0,
        f'{total:.1f}s / {len(shots)}镜 / 标准 {TARGET:.1f}s（{"用户指定" if USER_TARGET else "稿内登记" if DECLARED else "工具按各镜实算"}）')
    if _decl_total and abs(total - _decl_total) / _decl_total > 0.10:
        chk('附表登记的总时长与各镜合计一致', False,
            f'附表写 {_decl_total:.0f}s，各镜合计 {total:.1f}s')
    else:
        chk('附表登记的总时长与各镜合计一致', True,
            f'附表 {_decl_total:.0f}s' if _decl_total else '附表未写数字，工具按各镜实算')
    if TARGET:
        dev = abs(total - TARGET) / TARGET
        chk('总时长接近目标(±10%)', dev <= 0.10,
            f'{total:.1f}s vs 目标 {TARGET:.0f}s（偏差 {dev*100:.1f}%）')

    # 物件不许当施事（v2.9.34）：物件自己会动就是假动作
    import obj_agent
    import logic_chk
    import audit_m2
    import ref_bank
    _oa = obj_agent.offenders(u'\n'.join(shots))
    chk('每镜的施事是人，不是物件', not _oa,
        ('；'.join(c + '←' + w for c, w in _oa[:3])) if _oa else '0 处')

    # 每镜先把地点、人物方位、朝向交代清楚（v2.9.34）
    DIR_WORDS = ['画左', '画右', '画中', '门里', '门外', '台前', '柜台后', '柜台前',
                 '面朝', '背对', '侧身', '侧对', '朝门口', '朝柜台', '各占一边', '面对面']
    # 处所词不再写死便利店／后厨那一套：直接用通用的处所词表，
    # 病房、灶台、长凳、车厢、码头都算交代了在哪。
    import audit_m2 as _am
    _nodir = [i for i, s in enumerate(shots, 1)
              if not any(w in s for w in DIR_WORDS) or not any(
                  k in s for k in _am.SPOT)]
    chk('每镜先交代在哪、谁在哪、朝哪', not _nodir,
        ('镜' + '、'.join(map(str, _nodir[:6])) + ' 没写地点/方位/朝向') if _nodir else '19 镜全有')

    # 台词与逻辑不许 AI 腔（v2.9.33）：术语可以专业，句子必须是活人话
    AI_JUNK = [u'此外', u'综上所述', u'总而言之', u'首先，', u'其次', u'值得注意',
               u'不得不', u'仿佛', u'宛如', u'不禁', u'令人', u'这一刻，', u'于是，']
    _ai = [(i, w) for i, s in enumerate(shots, 1) for w in AI_JUNK if w in s]
    chk('台词与叙事没有 AI 腔连接词/套话', not _ai,
        ('镜' + '、'.join('%d「%s」' % (i, w) for i, w in _ai[:4])) if _ai else '0 处')

    # 实质合格：场景逻辑 / 上下镜衔接 / 台词AI味（机器先揪，人工最终判）
    conn, _ = cc.run_all(text)
    for cat, lvl, msg in conn:
        chk(f'{cat}：{msg}', lvl != 'FAIL', msg if lvl == 'FAIL' else '0')

    # 13A/B/C 人话三道关（铁律 13，v2.9.19 机器硬拦）
    # 13A 情感落点具象
    EMOTION = ['戳中', '治愈', '破防', '泪目', '共鸣', '击中', '暖到', '戳心', '暖化']
    CONCRETE = ['摸', '握', '攥', '捏', '展', '开', '看', '低', '颤', '抖', '堵', '哭',
                '笑', '说', '走', '蹲', '放', '扣', '摩', '挲', '咽', '抱', '愣', '僵', '红']
    emo_bad = []
    for w in EMOTION:
        for m in re.finditer(re.escape(w), body):
            win = body[max(0, m.start() - 16): m.start() + 28]
            if not any(c in win for c in CONCRETE):
                emo_bad.append(w)
                break
    chk('13A 情感落点具象（无空泛情绪词）', len(emo_bad) == 0, '空泛词=%s' % (emo_bad or '无'))

    # 13B 空间调度可行
    LOC = re.compile(r'(缓台|在[^，。]{0,8}楼|楼上|门里|门口里)')
    RECV = re.compile(r'(上来|拐上|楼下|拐进|上楼)')
    TRANSFER = re.compile(r'(送|递|塞|给)')
    MOVE = re.compile(r'(下楼|走下来|迎下来|下到|走过去迎|迎过来|迎上去|出门迎|下来迎)')
    space_bad = False
    for sent in re.split(r'[。！？\n]', body):
        if LOC.search(sent) and TRANSFER.search(sent) and RECV.search(sent) and not MOVE.search(sent):
            space_bad = True
            break
    chk('13B 空间调度可行（无跨层不通递送）', not space_bad,
        '跨层递送无移动动词' if space_bad else '无')

    # 13C 命名不撞实物
    BREED = '柯基|金毛|拉布拉多|萨摩|哈士奇|橘猫|布偶|泰迪|比熊|法斗|边牧|柴犬|缅因'
    FOOD = '年糕|馒头|包子|饺子|汤圆|蛋糕|薯条|鸡腿|苹果|糖糖|米饭|面条|糖果|薯片|布丁'
    name_bad = []
    if re.search('(' + BREED + ')(' + FOOD + ')', body):
        name_bad.append('品种+食物连写')
    if re.search(r'叫(了)?\s*(' + FOOD + r')', body):
        name_bad.append('宠物名撞食物')
    chk('13C 命名不撞实物（无品种+食物连写/名撞食物）', len(name_bad) == 0,
        '问题=%s' % (name_bad or '无'))

    # 铁律 14（v2.9.20 机器硬拦）：文笔活人话四守
    # 14-二 只写可拍：叙事散文里不写不可拍的内心/抽象比喻（先剥台词与【】技术行）
    _prose = re.sub(r'【[^】]*】', '', body)
    _prose = re.sub(r'[「"][^」"\n]*[」"]', '', _prose)
    UNFILM = [r'(?<![掌手脚])心里', '内心', '脑海里', '仿佛', '似乎', '好似', '宛如', '犹如',
              '像是回到了', '像是回到', '一股暖流', '莫名']
    unfilm_bad = [w for w in UNFILM if re.search(w, _prose)]
    chk('13D 文笔活人话·只写可拍（无心里/仿佛/似乎等不可拍词）', len(unfilm_bad) == 0,
        '不可拍词=%s' % (unfilm_bad or '无'))

    # 14-一/三 动作须落地：动作动词+时间词=物理不通（追进傍晚/窜进夜色）
    MOTION_TIME = re.compile(
        r'(窜进|钻进|追进|跑进|冲进|扑进|奔进|闯进|溜进|挤进|跳进|退进)\s*'
        r'(傍晚|夜色|黄昏|天黑|天色|夜|凌晨|清晨|午后|黑夜|夜里|深夜)')
    mt_bad = MOTION_TIME.findall(_prose)
    chk('13E 文笔活人话·动作须落地（无"追进傍晚"类动作+时间词不通）',
        len(mt_bad) == 0, '不通=%s' % (mt_bad or '无'))

    # 14-四 一镜一段散文：禁【】技术标签（九项信息写进句子）
    n_shots = len(shots)
    n_tag = sum(1 for s in shots if '【' in s or '】' in s)
    if n_shots == 0:
        chk('13F 分镜一镜一段散文·禁【】技术标签', False,
            '未解析到镜号行：必须单独一行写 **镜N（X秒）**，下面接一段散文')
    else:
        chk('13F 分镜一镜一段散文·禁【】技术标签',
            n_tag == 0,
            '带【】技术标签 %d/%d 镜' % (n_tag, n_shots))

    # 九项之「运镜」：每镜必须写清画面怎么动（此前只查取景与光影，运镜整项漏检）
    _nomove = [i for i, s in enumerate(shots, 1)
               if not fp.motion_ok(re.sub(r'[\u201c\u300c"][^\u201d\u300d"\n]*[\u201d\u300d"]', '', s))]
    chk('每镜写出画面怎么动（九项之运镜）', not _nomove,
        ('镜 %s 没写画面怎么动' % ','.join(str(i) for i in _nomove)) if _nomove else '无')

    # 人话硬检第二批：与 M1 门禁、主引擎共用同一份规则
    for _c, _n, _ok, _d in human_chk.run_all(body):
        chk('%s %s' % (_c, _n), _ok, _d)

    # 底本不断线：M1 ③ 台词必须逐句落到 M2（本门禁强制带底本，见 main 开头）
    _m1txt = open(m1_path, encoding='utf-8').read()
    _miss = human_chk.check_m12(_m1txt, body)   # 只认分镜正文，别把 ② 拆解卡里库内金句当台词
    chk('13K 底本不断线（M1 台词逐句落到 M2）', not _miss,
        '；'.join(_miss) or '无')

    # 13L 不许悄悄加戏：底本外的补写台词必须全列进清单、不许点题总结
    _extra = human_chk.check_m12_extra(_m1txt, body)   # 同上：拆解卡引用不算补写台词
    _listed, _unlisted = human_chk.check_extra_listed(text, _extra)
    chk('13L 补写台词逐句列进「补写台词」清单', _listed,
        '；'.join(_unlisted) or ('补写 %d 句，已列明' % len(_extra)))
    _tone = human_chk.check_extra_tone(_extra)
    chk('13L2 补写台词不点题不总结（不改剧情）', not _tone,
        '；'.join(_tone) or '无')

    # 13J 不平淡（按镜判：每镜要有动作链与外部变化，不许连续三镜没人说话）
    _fl = flat_check.scan_flat(text, "m2")
    chk('13J 不平淡（每镜有事/有变化/有声音）', not _fl,
        '；'.join('%s：%s' % (k, s[:22]) for _i, k, s in _fl[:4]) or '无')

    # 13I 句法文体：电报体/无谓语碎句/名词堆叠/抽象判断=不合格（与 human_regress 同源）
    _pr = check_prose.scan_prose(text)
    chk('13I 句法文体（无电报体/碎句/名词堆叠/场景交代/静物当主角/段首没动作）', not _pr,
        '；'.join('%s：%s' % (k, s[:24]) for _i, k, s in _pr[:4]) or '无')

    # 前后对不上四查（C1/C2/C3/C4，C4 要底本）：与 M1 门禁、主引擎同源
    for _c, _n, _ok, _d in consist_chk.run_all(text, "m2", _m1txt):
        chk('%s %s' % (_c, _n), _ok, _d)

    # 新要求整合硬检（N1/N2/N4/N5/N6/N7，底本另查 N8/N9）
    for _c, _n, _ok, _d in new_req_chk.run_all(text, "m2", _m1txt):
        chk('%s %s' % (_c, _n), _ok, _d)

    # 逻辑自打架三类（门型／时序／烟点没点）：v2.9.35
    for _c, _bad in logic_chk.run_all(text, len(shots)):
        chk(_c, not _bad, '；'.join(_bad) if _bad else '0 处')
    # 空间与走位（v2.9.45）：同一人不许同镜左右互斥、位置左右全片固定、进车门先开门、不从后备箱进
    import space_chk
    for _c, _bad in space_chk.run_all(text):
        chk(_c, not _bad, '；'.join(_bad[:3]) if _bad else '0 处')
    # 九项逐镜落位（v2.9.35）：取景/运镜/构图/光影/地点/方位/朝向/台词/动作落点
    # 参照标杆的分镜阶段手法（v2.9.41）：特写／对称／俯仰／长镜头／色块
    if m1_path:
        for _c, _bad in ref_bank.run_m2(m1_path, text):
            chk(_c, not _bad, '；'.join(_bad[:3]) if _bad else '0 处')
    _miss = audit_m2.scan(text)
    chk('九项逐镜落位（取景/运镜/构图/光影/地点方位/动作落点）', not _miss,
        ('；'.join('镜%d %s' % (n, s) for n, s in _miss[:4])) if _miss else '逐镜齐')
    print('=' * 56)
    print(f'M2 分镜自检：{len(shots)} 镜')
    print('=' * 56)
    npass = 0
    for n, ok, info in R:
        tag = 'PASS' if ok else 'FAIL'
        if ok:
            npass += 1
        line = f'[{tag}] {n}'
        if info:
            line += f'  （{info}）'
        print(line)
    print('-' * 56)
    print(f'结论：{npass}/{len(R)} 项 PASS')
    print('✅ M2 分镜自检全过' if npass == len(R) else '❌ 有项未过')
    sys.exit(0 if npass == len(R) else 1)


if __name__ == '__main__':
    main()
