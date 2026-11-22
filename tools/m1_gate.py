#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M1 交付门 20 项自动核查（针对一份 02_剧本草稿.md）。
用法：python m1_gate.py <剧本md路径>
集成了 m1_semchk 语义硬检（A/B 两类）。
"""
import re, sys, io, contextlib, os

TOOLS = r'E:\data\marketing\plan\2026-W46\分镜技能\tools'
sys.path.insert(0, TOOLS)
import m1_semchk
import human_chk
import new_req_chk
import consist_chk
import check_prose
import flat_check
import boom_chk
import dialogue_chk

DEFAULT = r'E:\data\marketing\plan\2026-W46\分镜技能\output\20261113-技能验证-M1-薅羊毛\02_剧本草稿.md'


def seg(text, start, end):
    m = re.search(start + r'.*?(?=' + end + ')', text, re.S)
    return m.group(0) if m else ''


def table_rows(s):
    rows = [l for l in s.split('\n') if l.strip().startswith('|')]
    data = [r for r in rows if not re.match(r'^\s*\|[\s\-\|:]+\|\s*$', r)]
    return data


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    # 同步必须在检查之后：先按盘上真实状态判定，不合格当场退回重出；
    # 不许先把配套件补齐再判，那等于把不合格证据抹掉、自己给自己盖章。
    text = open(path, encoding='utf-8').read()
    R = []

    def chk(name, ok, info=''):
        R.append((name, bool(ok), info))

    # 1. ⓪ 选题匹配
    chk('⓪ 选题与爆款匹配说明', '## ⓪' in text)
    # 2. ① 开题卡四要素
    need = ['一句话 Logline', '题眼道具', '核心情绪', '对仗标题']
    chk('① 开题卡四要素齐全', all(x in text for x in need))
    # 3. 对仗标题字数相等
    mt = re.search(r'对仗标题\*{0,2}\s*[:：]\s*(.+?)\s*$', text, re.M)
    if mt:
        parts = [p.strip() for p in re.split(r'[／/]', mt.group(1))]
        if len(parts) == 2:
            eq = len(parts[0]) == len(parts[1])
            chk('① 对仗标题字数相等', eq, f'{parts[0]}({len(parts[0])}) / {parts[1]}({len(parts[1])})')
        else:
            chk('① 对仗标题字数相等', False, '未拆出两行对仗')
    else:
        chk('① 对仗标题字数相等', False, '未找到对仗标题')
    # 4. ② 分幕骨架
    chk('② 分幕骨架', '## ② 分幕骨架' in text)
    # 5. ②b 因果链 4 列
    sb = seg(text, r'## ②b', r'## ②c')
    rb = table_rows(sb)
    cols_b = len([c for c in rb[0].split('|') if c.strip()]) if rb else 0
    chk('②b 因果链 4 列', cols_b == 5, f'列数={cols_b-1}')
    chk('②b 因果链 ≥4 行', len(rb) - 1 >= 4, f'数据行={len(rb)-1}')
    # 6. ②b 每行误会起因不同（不重复）
    if len(rb) > 1:
        firsts = [r.split('|')[1].strip() for r in rb[1:]]
        chk('②b 每行内容不同', len(set(firsts)) == len(firsts))
    else:
        chk('②b 每行内容不同', False, '无数据行')
    # 7. ②c 对照表 ≥6 行
    sc = seg(text, r'## ②c', r'## ②d')
    rc = table_rows(sc)
    chk('②c 爆款对照表 ≥6 行', len(rc) - 1 >= 6, f'数据行={len(rc)-1}')
    # 8. ②c 覆盖六招式
    six = all(k in sc for k in ['①', '②', '③', '④', '⑤', '⑥'])
    chk('②c 覆盖六招式', six)
    # 9. ②c 每行落在具体段（含「幕」）
    lines_c = rc[1:] if len(rc) > 1 else []
    chk('②c 每行落在具体段(含幕)', bool(lines_c) and all('幕' in r for r in lines_c))
    # 10. ②d 四格 4 列 + ≥4 行
    sd = seg(text, r'## ②d', r'## ③')
    rd = table_rows(sd)
    cols_d = len([c for c in rd[0].split('|') if c.strip()]) if rd else 0
    chk('②d 段落动作表 4 列', cols_d == 5, f'列数={cols_d-1}')
    chk('②d 段落动作表 ≥4 行', len(rd) - 1 >= 4, f'数据行={len(rd)-1}')
    # 11. ②d 无标红重写（无空格、无"重写/平局/无变化"）
    body_d = rd[1:] if len(rd) > 1 else []
    ok_d = True
    for r in body_d:
        cells = [c.strip() for c in r.split('|')[1:-1]]
        if any(not c for c in cells) or ('重写' in r) or ('平局' in r) or ('无变化' in r):
            ok_d = False
            break
    chk('②d 无标红重写段', ok_d)
    # 12-13. ③ 故事剧本：存在 / 不编镜号 / 不写秒数
    s3 = seg(text, r'## ③', r'## ④')
    chk('③ 故事剧本存在', len(s3) > 50)
    chk('③ 不编镜号(无分镜序号)', not re.search(r'镜\s*[0-9一二三四五六七八九十百千]', s3))
    chk('③ 不写秒数(无「秒」字)', '秒' not in s3)
    # 14. ③ 无影视术语
    terms = ['8K', '电影感', '大师级', '运镜流畅', '镜头语言', '氛围感', '极富张力', '画面精美']
    hit = [t for t in terms if t in s3]
    chk('③ 无影视术语', not hit, '命中:' + ','.join(hit) if hit else '')
    # 15. ④ 情感弧六槽
    s4 = seg(text, r'## ④', r'## ⑤')
    slots = ['主情绪', '起点', '中段', '转折', '终点', '弧光']
    chk('④ 情感弧六槽齐全', all(s in s4 for s in slots))
    # 16. ④ 弧光两词不同
    ma = re.search(r'弧光\**\s*[：:]\s*从[「『](.+?)[」』]\s*到[「『](.+?)[」』]', s4)
    if ma:
        a, b = ma.group(1).strip(), ma.group(2).strip()
        chk('④ 弧光两词不同', a != b, f'{a}→{b}')
    else:
        chk('④ 弧光两词不同', False, '未解析弧光')
    # 17. ⑤ 不固化问法
    bad5 = ['待你拍板的 4 件事', '用这三个还是换', '按 180 秒', '按 18 镜']
    chk('⑤ 不固化问法', not any(b in text for b in bad5))
    # 18. ⑥ 预告 ≥10 条
    s6 = seg(text, r'## ⑥', r'## ⑦') if '## ⑦' in text else seg(text, r'## ⑥', r'\Z')
    nums = re.findall(r'^\s*\d+\.', s6, re.M)
    chk('⑥ 分镜预告 ≥10 条', len(nums) >= 10, f'条数={len(nums)}')
    # 19. ⑥ 不写具体镜号画面
    chk('⑥ 不写具体镜号画面', not re.search(r'镜\d', s6))
    # ⑥ 预告必须按当前标准写全（v2.9.37）：标准既定，出稿就得照着写。
    # 旧口径（四不写／人工通读兜底／按字数反推／术语不进正文）混过绿灯，
    # 等于让下一阶段拿一份反着的规格去出分镜，必须在剧本门就拦下。
    std6 = ['中英对照专业术语', '前后对不上五不写', '本片标准卡', '退回重出', '剧本是故事']
    old6 = ['人工逐句通读', '机器全绿不等于稿子能看', '前后对不上四不写',
            '专业说法不进正文', '按该镜台词（每秒 4.5 字）', '场头只做定位']
    miss6 = [w for w in std6 if w not in s6]
    hit6 = [w for w in old6 if w in s6]
    chk('⑥ 预告按当前标准写全（术语必填／五不写／标准卡／不靠人眼兜底）',
        not miss6 and not hit6, '缺：%s；旧：%s' % (miss6 or '无', hit6 or '无'))
    # 19b-19e 前提立住（v2.9.18 机器硬拦，口径见 SKILL §7.6.1 E）
    chk('⑦ 前提立住节存在', '## ⑦' in text)
    chk('③ 故事剧本不靠旁白（无"旁白"二字）', '旁白' not in s3)
    if '## ⑦' in text:
        s7 = text[text.find('## ⑦'):]
        end7 = s7.find('\n## ', 3)
        s7 = s7[:end7] if end7 > 0 else s7
        r7 = table_rows(s7)
        cells = []
        for r in r7[1:]:
            cs = [c.strip() for c in r.split('|')]
            cs = [c for c in cs if c]
            cells.extend(cs[1:])
        first2 = cells[:2] if len(cells) >= 2 else cells
        # 占位词按「格子里出现就算」，不按整格精确匹配：
        # 「待填（写一个动作…）」这类带括号说明的模板残留也算没填，不许蒙混过关。
        filler_word = ['旁白', '未交代', '待补', '无交代', '待填', '待定', 'undefined', '（写', '见实算值']
        def _filled(c):
            c = c.strip()
            return len(c) >= 4 and c not in ('', '无', '空') and not any(w in c for w in filler_word)
        ok7a = len(first2) == 2 and all(_filled(c) for c in first2)
        chk('⑦ 前两格落地（非空且非旁白/未交代）', ok7a, '前两格=%s' % (first2 or '缺失'))
        char_cell = cells[2] if len(cells) >= 3 else ''
        has_neg = ('否' in char_cell) or ('无矛盾' in char_cell)
        has_bare = ('矛盾' in char_cell) and ('无矛盾' not in char_cell) and ('不矛盾' not in char_cell)
        has_filler = any(w in char_cell for w in filler_word)
        ok7b = has_neg and not has_bare and not has_filler
        chk('⑦ 人设不自打已确认（填否/无矛盾）', ok7b, '人设格=%s' % (char_cell or '缺失'))
    else:
        chk('⑦ 前两格落地（非空且非旁白/未交代）', False, '无 ⑦ 节')
        chk('⑦ 人设不自打已确认（填否/无矛盾）', False, '无 ⑦ 节')
    # 20. 语义硬检 A/B
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m1_semchk.check(path)
    out = buf.getvalue()
    na = re.search(r'\[A\][^\d]*(\d+)\s*处', out)
    nb = re.search(r'\[B\][^\d]*(\d+)\s*处', out)
    na = int(na.group(1)) if na else -1
    nb = int(nb.group(1)) if nb else -1
    chk('语义自检[A]无生命物 0 处', na == 0, f'A={na}')
    chk('语义自检[B]模糊指代 0 处', nb == 0, f'B={nb}')

    # ⑥ 是要求节，里面会列举被禁的说法本身，机器判文笔时先剔掉，免得规矩把自己判违规
    _bt = re.sub(r'## ⑥.*?(?=## ⑦|\Z)', '', text, flags=re.S)

    # 25-27. 人话三道关（铁律 13，v2.9.19 机器硬拦）
    # 25A 情感落点具象：抽象情绪结果词须有邻近具体动作承载
    EMOTION = ['戳中', '治愈', '破防', '泪目', '共鸣', '击中', '暖到', '戳心', '暖化']
    CONCRETE = ['摸', '握', '攥', '捏', '展', '开', '看', '低', '颤', '抖', '堵', '哭',
                '笑', '说', '走', '蹲', '放', '扣', '摩', '挲', '咽', '抱', '愣', '僵', '红']
    emo_hit, emo_bad = [], []
    for w in EMOTION:
        for m in re.finditer(re.escape(w), _bt):
            emo_hit.append(w)
            win = _bt[max(0, m.start() - 16): m.start() + 28]
            if not any(c in win for c in CONCRETE):
                emo_bad.append(w)
    chk('13A 情感落点具象（无空泛情绪词）', len(emo_bad) == 0,
        '空泛词=%s' % (emo_bad or '无'))

    # 26B 空间调度可行：跨层/跨距离递送须有移动动词
    LOC = re.compile(r'(缓台|在[^，。]{0,8}楼|楼上|门里|门口里)')
    RECV = re.compile(r'(上来|拐上|楼下|拐进|上楼)')
    TRANSFER = re.compile(r'(送|递|塞|给)')
    MOVE = re.compile(r'(下楼|走下来|迎下来|下到|走过去迎|迎过来|迎上去|出门迎|下来迎)')
    space_bad = False
    for sent in re.split(r'[。！？\n]', _bt):
        if LOC.search(sent) and TRANSFER.search(sent) and RECV.search(sent):
            if not MOVE.search(sent):
                space_bad = True
                break
    chk('13B 空间调度可行（无跨层不通递送）', not space_bad,
        '发现楼上/缓台/门里向"上来/拐上"方递送且无移动动词' if space_bad else '无')

    # 27C 命名不撞实物：品种+食物连写 / 宠物名撞食物
    BREED = '柯基|金毛|拉布拉多|萨摩|哈士奇|橘猫|布偶|泰迪|比熊|法斗|边牧|柴犬|缅因'
    FOOD = '年糕|馒头|包子|饺子|汤圆|蛋糕|薯条|鸡腿|苹果|糖糖|米饭|面条|糖果|薯片|布丁'
    name_bad = []
    if re.search('(' + BREED + ')(' + FOOD + ')', _bt):
        name_bad.append('品种+食物连写')
    if re.search(r'叫(了)?\s*(' + FOOD + r')', _bt):
        name_bad.append('宠物名撞食物')
    chk('13C 命名不撞实物（无品种+食物连写/名撞食物）', len(name_bad) == 0,
        '问题=%s' % (name_bad or '无'))

    # 28D 文笔活人话·只写可拍（铁律 14·二）：叙事散文里不写不可拍的内心/抽象比喻
    # 先剥掉台词「」与""，只对旁白/叙事部分查
    _no_dlg = re.sub(r'[「"][^」"\n]*[」"]', '', _bt)
    UNFILM = [r'(?<![掌手脚])心里', '内心', '脑海里', '仿佛', '似乎', '好似', '宛如', '犹如',
              '像是回到了', '像是回到', '一股暖流', '莫名']
    unfilm_bad = [w for w in UNFILM if re.search(w, _no_dlg)]
    chk('13D 文笔活人话·只写可拍（无心里/仿佛/似乎等不可拍词）', len(unfilm_bad) == 0,
        '不可拍词=%s' % (unfilm_bad or '无'))

    # 29E 文笔活人话·动作须落地（铁律 14·一/三）：动作动词+时间词=物理不通（追进傍晚）
    MOTION_TIME = re.compile(
        r'(窜进|钻进|追进|跑进|冲进|扑进|奔进|闯进|溜进|挤进|跳进|退进)\s*'
        r'(傍晚|夜色|黄昏|天黑|天色|夜|凌晨|清晨|午后|黑夜|夜里|深夜)')
    mt_bad = MOTION_TIME.findall(_no_dlg)
    chk('13E 文笔活人话·动作须落地（无"追进傍晚"类动作+时间词不通）',
        len(mt_bad) == 0, '不通=%s' % (mt_bad or '无'))

    # 剧本与脚本分层：剧本是故事情节，七项括号/镜号/机位光影都是脚本的事，剧本里一处不许有
    _m3 = re.search(r"## ③[^\n]*\n(.*?)(?=\n## )", text, re.S)
    _s3 = _m3.group(1) if _m3 else ""
    _mix = []
    if re.search(u"（[男女]·[0-9]{2}·", _s3):
        _mix.append("台词七项括号")
    for _w in (u"镜号", u"镜 1", u"景别", u"机位", u"光位", u"色温", u"运镜"):
        if _w in _s3:
            _mix.append(_w)
    chk(u'剧本层只写故事情节（无七项括号／镜号／机位光位，那些归脚本）', not _mix,
        u'剧本里混进=%s' % ("、".join(_mix) if _mix else u"无"))

    # 34-37 人话硬检第二批：与 M2 门禁、主引擎共用同一份规则，不再各写一份
    for _c, _n, _ok, _d in human_chk.run_all(_bt):
        chk('%s %s' % (_c, _n), _ok, _d)

    # 爆款完全符合硬检（B1–B6）：与出稿端、主引擎同源；缺交付件当场判不合格、退回重出
    for _c, _n, _ok, _d in boom_chk.run_all(text, path):
        chk('%s %s' % (_c, _n), _ok, _d)

    # 前后对不上四查（C1/C3）：与 M2 门禁、主引擎共用同一份规则
    for _c, _n, _ok, _d in consist_chk.run_all(text, "m1"):
        chk('%s %s' % (_c, _n), _ok, _d)

    # 13G 句法文体：正文必须是叙事句（禁「段 1　村口，夜里。」这类场头当句子）
    _pr = check_prose.scan_prose(text)
    chk('13I 句法文体（无电报体/碎句/名词堆叠/段号编号/场景交代/静物当主角/段首没动作）', not _pr,
        '；'.join('%s：%s' % (k, s[:24]) for _i, k, s in _pr[:4]) or '无')

    # 13J 不平淡：动作链、外部变化、台词密度、段落信息量（平淡即不合格）
    _fl = flat_check.scan_flat(text, "m1")
    chk('13J 不平淡（动作链/外部变化/台词密度/信息量）', not _fl,
        '；'.join('%s：%s' % (k, s[:22]) for _i, k, s in _fl[:4]) or '无')

    # 13K 台词节奏：中间段每百字/每段台词下限 + 不许一路自语没人接（v2.9.52）
    for _dc, _dn, _dok, _dd in dialogue_chk.run_all(text):
        chk('%s %s' % (_dc, _dn), _dok, _dd)

    # 新要求整合硬检（N1/N2/N3/N8/N9）：与 M2 门禁、主引擎同源
    for _c, _n, _ok, _d in new_req_chk.run_all(text, "m1"):
        chk('%s %s' % (_c, _n), _ok, _d)

    import obj_agent
    import logic_chk
    import story_logic
    import craft_chk
    import relation_chk
    import effect_chk
    import ref_bank
    _oa = obj_agent.offenders(seg(text, '## ③', '## ④'))
    chk('正文没有物件自己会动（物件/部位不许当施事）', not _oa,
        '；'.join('%s←%s' % (c, w) for c, w in _oa[:3]) if _oa else '0 处')

    for _c, _bad in logic_chk.run_all(text)[:1] + logic_chk.run_all(text)[2:]:
        chk(_c, not _bad, '；'.join(_bad) if _bad else '0 处')

    # 叙事逻辑与爆款结构六条（S1–S6）
    for _c, _bad in story_logic.run_all(path):
        chk(_c, not _bad, '；'.join(_bad[:3]) if _bad else '0 处')

    # 作家／编剧技法七条（K1–K7）
    for _c, _bad in craft_chk.run_all(path):
        chk(_c, not _bad, '；'.join(_bad[:3]) if _bad else '0 处')

    # 关系检查（R1–R5）：字数不算对错，关系才算
    for _c, _bad in relation_chk.run_all(path):
        chk(_c, not _bad, '；'.join(_bad[:3]) if _bad else '0 处')

    # 效果卡：这片要哪种反应，就按那种结构核
    _ef = []
    for _c, _bad in effect_chk.run_all(path):
        if _bad:
            _ef.append(_c + '：' + _bad[0])
    chk(u'E 效果卡登记并按该效果的结构核对', not _ef, '；'.join(_ef[:3]) if _ef else '0 处')

    # 参照标杆：每个类别一个具名标杆，核它有没有用上那位的手法
    _rf = []
    for _c, _bad in ref_bank.run_all(path):
        if _bad:
            _rf.append(_c + '：' + _bad[0])
    chk(u'F 参照标杆登记并核到标志手段', not _rf, '；'.join(_rf[:3]) if _rf else '0 处')

    # 因果链：句子与技法之外，钱款/承诺/交接/职业/算术必须自洽（logic_chain_chk）
    try:
        import logic_chain_chk
        for _n, _o, _i in logic_chain_chk.run_all(path):
            chk(_n, _o, _i)
    except Exception as e:
        chk(u'L 因果链（logic_chain_chk 未跑通）', False, str(e))

    # 结论已按同步前的真实状态算定；这里只顺手补齐配套件，不改变本次判定
    npass = sum(1 for _, o, _ in R if o)
    _sync_note = ''
    try:
        _done = boom_chk.sync_run(path)
        if _done and npass < len(R):
            _sync_note = (u'[提示] 配套件已按成稿自动补齐（%s）；本次仍按补齐前状态判不合格，'
                          u'重跑一次即按补齐后状态复核。' % u'、'.join(_done))
    except Exception as e:
        _sync_note = u'[提示] 配套文件自动同步没成：%s' % e

    print('=' * 60)
    print(f'M1 交付门核查：{os.path.basename(path)}')
    print('=' * 60)
    for i, (name, ok, info) in enumerate(R, 1):
        tag = 'PASS' if ok else 'FAIL'
        line = f'[{tag}] {i:02d}. {name}'
        if info:
            line += f'  （{info}）'
        print(line)
    print('-' * 60)
    print(f'结论：{npass}/{len(R)} 项 PASS')
    if _sync_note:
        print(_sync_note)
    print('✅ M1 交付门全过' if npass == len(R) else '❌ 有项未过')
    sys.exit(0 if npass == len(R) else 1)


if __name__ == '__main__':
    main()
