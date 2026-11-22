# -*- coding: utf-8 -*-
"""人话硬检（共同口径）。

M1 交付门、M2 分镜自检、主引擎三处都调本文件，规则只写一份，避免各写一份越改越歪。
查的是"人一读就出戏、机器原先全放行"的那批：拍不到的感官与顿悟、半句没落点、
病句与点题金句、同一段自相矛盾、实物自己晃、以及 M1 台词到 M2 断线。

如实说明：规则只能拦已经认得的说法，认不得的新说法仍要靠人工通读，不能当万能。
"""
import re

# ── 13G：只写拍得到的（散文里不许出现拍不到的感官判断、顿悟） ──────────
SENSE_INNER = [
    (r'闻见[^。\n]{0,14}气味', '闻见气味拍不到'),
    (r'闻到[^。\n]{0,14}气味', '闻到气味拍不到'),
    (r'嗅到[^。\n]{0,14}气味', '嗅到气味拍不到'),
    (r'闻得出', '嗅觉判断拍不到'),
    (r'才懂', '顿悟是脑子里的，镜头拍不到'),
    (r'忽然懂', '顿悟是脑子里的，镜头拍不到'),
    (r'懂了', '顿悟是脑子里的，镜头拍不到'),
    (r'明白过来', '顿悟是脑子里的，镜头拍不到'),
    (r'顿时明白', '顿悟是脑子里的，镜头拍不到'),
    (r'恍然', '顿悟是脑子里的，镜头拍不到'),
    (r'一下子明白', '顿悟是脑子里的，镜头拍不到'),
]

# ── 13H：句子必须写完（半句、缺宾语、叙述判断、指代不明） ──────────────
HALF_SENTENCE = [
    (r'，是个[^，。\n]{0,12}[。\n]', '「，是个X」缺主语，半截话'),
    (r'歪歪扭扭[。！？]', '「一行字歪歪扭扭」没写写的什么，句子没落点'),
    (r'拨开[^。\n]{0,10}找[。\n]', '「拨开找」找什么没写'),
    (r'停了很久', '「停了很久」是时长判断，镜头拍不到'),
    (r'站了很久', '「站了很久」是时长判断，镜头拍不到'),
    (r'两手空着', '「两手空着」是叙述判断，不是画面'),
    (r'绳头不在了', '「绳头不在了」是叙述判断，不是画面'),
    (r'四条腿的影子', '指代不明，观众看不出那是狗'),
]

# ── 13I：台词里的病句与点题金句（只查引号内） ──────────────────────────
BAD_LINE = [
    (r'[\u4e00-\u9fa5]{1,3}他老伴', '「某某他老伴」是病句'),
    (r'怕您一(人|个人)[。！？]', '「怕您一人」缺字，不是人话'),
    (r'原来[^」\n]{0,14}是怕', '自己把主题念出来的点题金句'),
    (r'怕[^」\n]{0,12}是怕', '自己把主题念出来的点题金句'),
    (r'说到底|其实是|这才是真正', '总结升华腔'),
]

# ── 13J：同一段自相矛盾 / 实物不会自己动 ───────────────────────────────
NO_VOICE = re.compile(r'没再出声|没出声|没吭声')
LAMP_SWAY = re.compile(r'(走廊灯|路灯|灯管|荧光灯|吸顶灯)[^。\n]{0,12}晃')


def _parts(text):
    """拆出：只含叙事的散文、台词内容、按镜/按段切开的块。

    「⑥ 分镜脚本将按什么要求制作」是要求节，里面必须列举被禁的说法本身，
    不算正文；不剔掉的话，写清规矩反而会把自己的稿子判违规。
    """
    text = re.sub(r'## ⑥.*?(?=## ⑦|\Z)', '', text, flags=re.S)
    prose = re.sub(r'【[^】]*】', '', text)
    dialogue = re.findall(r'[「"]([^」"\n]*)[」"]', prose)
    prose = re.sub(r'[「"][^」"\n]*[」"]', '', prose)
    blocks = re.split(r'(?=\*\*镜\d+)', text)
    if len(blocks) <= 1:
        blocks = re.split(r'\n\s*\n', text)
    return prose, dialogue, blocks


def _hits(prose, patterns):
    out = []
    for pat, why in patterns:
        m = re.search(pat, prose)
        if m:
            out.append('%s（%s）' % (why, m.group(0).strip()[:18]))
    return out


def run_all(text):
    """返回 [(编号, 检查名, 是否通过, 说明)]，供三处门禁直接勾。"""
    prose, dialogue, blocks = _parts(text)
    res = []

    g = _hits(prose, SENSE_INNER)
    res.append(('13G', '只写拍得到的（无气味/顿悟等拍不到的判断）', not g, '；'.join(g) or '无'))

    h = _hits(prose, HALF_SENTENCE)
    res.append(('13H', '句子写完有落点（无半句/缺宾语/叙述判断）', not h, '；'.join(h) or '无'))

    i = []
    for d in dialogue:
        i += _hits(d, BAD_LINE)
    res.append(('13I', '台词是人话（无病句/点题金句）', not i, '；'.join(i) or '无'))

    j = []
    for b in blocks:
        if NO_VOICE.search(b) and re.search(r'[「"][^」"\n]*[」"]', b):
            j.append('同一段既写没出声又有人开口（%s）' % NO_VOICE.search(b).group(0))
    for m in LAMP_SWAY.finditer(prose):
        j.append('灯不会自己晃（%s）' % m.group(0).strip()[:16])
    res.append(('13J', '前后不打架（无自相矛盾/实物自晃）', not j, '；'.join(j) or '无'))

    return res


# v2.9.54：剧本台词没长度门禁（可到 24 字），分镜却要求单句 ≤14 字且底本逐句落地。
# 原样搬进分镜判超长、拆成短口语又判断线，是死结。达标做法是长台词按语义拆成
# 短句落地，所以落地判定认「整句」或「按中文标点切开、每个片段都出现」两种。
_SPLIT_DLG = re.compile(u'[，。？！；、：,;!?]')


def _dlg_pieces(d):
    """把一句长台词按中文标点切成可独立落地的短片段。"""
    return [p.strip() for p in _SPLIT_DLG.split(d) if len(p.strip()) >= 2]


def check_m12(m1_text, m2_text):
    """M1 ③ 故事剧本里的台词，必须逐句在 M2 落地。返回断线台词列表。

    短句（≤14 字）整句逐字落地；长句（>14 字）允许拆成短口语，
    只要按标点切出的每个语义片段都在分镜台词里出现，就算落地。
    """
    seg = re.search(r'## ③(.*?)## ④', m1_text, re.S)
    if not seg:
        return []
    dlg = re.findall(r'[「"]([^」"\n]*)[」"]', seg.group(1))
    miss = []
    for d in dlg:
        d = d.strip()
        if not d or d in m2_text:
            continue
        if len(d) > 14:
            pieces = _dlg_pieces(d)
            if pieces and all(p in m2_text for p in pieces):
                continue
        miss.append(d)
    return miss


def check_m12_extra(m1_text, m2_text):
    """M2 里底本没有的补写台词，逐句列出来（供门禁明文报出、人工核对）。

    底本台词常少于分镜镜数，而每镜至少一句台词，补写不可避免；
    规矩是「不许加戏」不是「不许加字」：补写的每句都要列明、不改剧情、不点题。
    v2.9.54：长台词拆出来的短片段属于「底本落地」，不算补写台词。
    """
    seg = re.search(r'## ③(.*?)## ④', m1_text, re.S)
    if not seg:
        return []
    base = set()
    for d in re.findall(r'[「"]([^」"\n]*)[」"]', seg.group(1)):
        d = d.strip()
        if not d:
            continue
        base.add(d)
        if len(d) > 14:
            for p in _dlg_pieces(d):
                base.add(p)
                base.add(p + '。')
                base.add(p + '？')
                base.add(p + '！')
    body = re.split(r'## 附表', m2_text)[0]
    out = []
    for d in re.findall(r'[「"]([^」"\n]*)[」"]', body):
        d = d.strip()
        if d and d not in base and d not in out:
            out.append(d)
    return out


def check_extra_listed(m2_text, extra):
    """补写台词必须在分镜里单列「补写台词」清单；返回 (是否列全, 缺哪几句)。"""
    if not extra:
        return True, []
    mark = re.search(r'补写台词', m2_text)
    area = m2_text[mark.start():] if mark else ''
    miss = [d for d in extra if d not in area]
    return not miss, miss


def check_extra_tone(extra):
    """补写台词不许点题、总结、升华（这类句子最容易悄悄改剧情）。"""
    bad = [r'原来', r'说到底', r'这才是真正', r'其实是', r'人生', r'从此', r'终于懂', r'才明白', r'总会']
    out = []
    for d in extra:
        if any(re.search(p, d) for p in bad):
            out.append('%s（点题/总结腔）' % d)
    return out


def line_issues(text):
    """供主引擎用：返回 [(编号, 说明)]，只列没过的。"""
    return [(c, '%s：%s' % (n, d)) for c, n, ok, d in run_all(text) if not ok]


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        _g = u'老周把旧闹钟递到柜台上，阿蓉接住翻看，拧开后盖抽出一张纸条。'
        _r = run_all(_g)
        _ok = bool(_r) and all(x[2] for x in _r)
        print(u'人话检查自检：%s（干净稿 %d 项全过）' % (u'通过' if _ok else u'未过', len(_r)))
        sys.exit(0 if _ok else 1)
    if len(sys.argv) < 2 or sys.argv[1].startswith('--'):
        print('用法：python human_chk.py <文档.md> [M1文档.md] 或 --test')
        sys.exit(1)
    t = open(sys.argv[1], encoding='utf-8').read()
    for c, n, ok, d in run_all(t):
        print('[%s] %s %s  %s' % ('PASS' if ok else 'FAIL', c, n, d))
    if len(sys.argv) > 2:
        m1 = open(sys.argv[2], encoding='utf-8').read()
        miss = check_m12(m1, t)
        print('[%s] 13K 底本不断线  %s' % ('PASS' if not miss else 'FAIL', '；'.join(miss) or '无'))
