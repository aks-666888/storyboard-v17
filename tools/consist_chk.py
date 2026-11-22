# -*- coding: utf-8 -*-
"""前后对不上（通用·全题材）：同一处地方、同一盏灯、同一件东西，前后说法不许打架。

M1 交付门、M2 交付门、主引擎三处共用这一份规矩，不各写一份。
只认通用中文词，不含任何本次题材、人物、片名、地名。
定位：机器先揪出具体句子，人工最终判；揪不出来不表示稿子没问题。
"""
import re

# ── 住处形态：同一个故事里，主角住处不该一会儿是院落平房、一会儿是电梯楼房 ──
# 例如「城里高楼配农村堂屋」「回胡同却上了三楼的电梯」，都属用户说的「场景对不上」。
PLACE_NEW = ('高楼', '电梯', '楼道', '单元楼', '公寓', '小区', '物业', '地下车库', '门禁')
PLACE_OLD = ('堂屋', '土炕', '农房', '平房', '灶台', '柴火', '菜地', '村口',
             '胡同', '弄堂', '四合院')

# ── 同一处光源的色温 ──
LIGHT_KEYS = (
    ('廊灯', ('走廊灯', '楼道灯', '声控灯', '廊灯', '吸顶灯', '荧光灯', '荧光', '楼道冷光', '走廊')),
    ('屋里漏出的光', ('门缝', '屋里', '屋内', '门里', '窗光', '台灯')),
    ('电梯光', ('轿厢', '顶灯', '电梯')),
    ('门口光', ('台阶', '门口', '单元门')),
    ('天光', ('天光', '晨光', '日头', '夕阳', '傍晚', '树影')),
)
COLD = ('冷白', '冷蓝', '冷光', '冷调', '冷色', '冷斑', '冷影', '青白')
WARM = ('暖黄', '暖光', '暖调', '暖色', '暖橙', '橙黄', '昏黄', '染温')

# ── 题眼道具的归属链 ──
HAND = ('递到', '递给', '接到', '攥在', '托在', '捏在', '拿在', '捧在', '手里', '手上', '攥着', '托着', '捏着')
BODY = ('戴着', '戴在', '扣在', '脖子', '颈上', '套在', '扣回', '勒紧', '扣好')
LOST = ('留在', '挂在', '勾住', '卡在', '落在', '掉在', '枝上', '刺里', '门缝底下')
HANDOFF = ('取下', '摘下', '解下', '解开', '扣回', '扣上', '放下', '捡', '拾', '塞',
           '拿回', '找回', '掰开', '抽出', '重新扣', '递', '接')
# 道具自己脱离/被外力带走，也写清了「怎么从一处到另一处」，不算凭空换地方
DETACH = ('扯脱', '崩开', '挣脱', '勾住', '滑落', '掉下', '落在', '留在', '甩下', '扯断')


def _light_key(clause):
    for key, words in LIGHT_KEYS:
        if any(w in clause for w in words):
            return key
    return None


def _temps(clause):
    out = []
    if any(w in clause for w in COLD):
        out.append('冷')
    if any(w in clause for w in WARM):
        out.append('暖')
    return out


def check_light(text):
    """同一处灯/同一处光，前后不许一会儿冷白一会儿暖黄。返回问题句列表。

    新写法把光写进画面句子，旧写法写进【】技术行；两种都扫，旧稿照样拦得住。
    只认「同一小句里既有光源词又有色温词」的片段，避免把别处的暖光算到廊灯头上。
    """
    body = re.split(r'##\s*(?:③\s*)?附表', text)[0]
    seen = {}
    shot = 0
    for line in body.splitlines():
        m = re.match(r'\**镜(\d+)', line.strip())
        if m:
            shot = int(m.group(1))
            continue
        if line.lstrip().startswith(('#', '|', '>', '-')):
            continue
        bits = re.findall(r'【([^】]*)】', line)
        plain = re.sub(r'【[^】]*】', '', line)
        clauses = []
        for tag in bits:
            clauses.extend(re.split(r'[，,；;。·、]', tag))
        clauses.extend(re.split(r'[，,；;。]', plain))
        for cl in clauses:
            key = _light_key(cl)
            if not key:
                continue
            for t in _temps(cl):
                seen.setdefault(key, []).append((t, shot, cl.strip()))
    out = []
    for key, items in seen.items():
        cold = [x for x in items if x[0] == '冷']
        warm = [x for x in items if x[0] == '暖']
        if cold and warm:
            c, w = cold[0], warm[0]
            pos = lambda k: ('镜%d' % k) if k else '前文'
            out.append('%s前后打架：%s 写「%s」，%s 写「%s」' %
                       (key, pos(c[1]), c[2][:26], pos(w[1]), w[2][:26]))
    return out


def prop_name(m1_text, m2_text=''):
    """从开题卡「题眼道具」字段取名；取不到就返回空串（不硬凑、不乱猜）。"""
    m = re.search(r'题眼道具\*{0,2}\s*[:：]\s*([^\n（(]+)', m1_text or '')
    if not m:
        return ''
    raw = m.group(1).strip().strip('。·、 ')
    raw = re.sub(r'[（(].*', '', raw).strip()
    if not raw:
        return ''
    cand = [raw]
    if len(raw) >= 3:
        cand.append(raw[-2:])
    body = m2_text or m1_text
    return max(cand, key=lambda x: body.count(x))


def _clauses(sent, name):
    """只取真正提到这件东西的小句，避免同句里别人的动作被算成交接。"""
    return [c for c in re.split(r'[，,；;]', sent) if name in c]


def _handoff(sent, name):
    return any(_has(c, HANDOFF) for c in _clauses(sent, name))


def _has(s, words):
    return any(w in s for w in words)


def _state(sent, name):
    """状态只在提到这件东西的小句里判；交接词也只在这些小句里算。"""
    tags = set()
    for c in _clauses(sent, name):
        if _has(c, HAND):
            tags.add('在人手里')
        if _has(c, BODY):
            tags.add('戴在身上')
        if _has(c, LOST):
            tags.add('遗落在外')
    return tags


def _section(text, start_pat, end_pat):
    m = re.search(start_pat + r'(.*?)(?=' + end_pat + r'|\Z)', text, re.S)
    return m.group(1) if m else ''


def _sentences(text, name):
    """全篇按句切开；不含道具名的句子也要留着，交接动作常常另起一句写。"""
    return [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]


def _prop_chain(sents, name, label):
    """同一件东西：同句互斥状态／跨句凭空换地方，且没写交接动作＝前后打架。"""
    out = []
    prev = None
    pending = False          # 两句之间曾写过交接动作（另起一句写的也算）
    for s in sents:
        if name not in s:
            if _has(s, HANDOFF) or _has(s, DETACH):
                pending = True
            continue
        st = _state(s, name)
        changed = _handoff(s, name) or _has(s, DETACH) or pending
        if st:
            if '在人手里' in st and (st & {'戴在身上', '遗落在外'}) and not changed:
                out.append('%s：同一句里%s既在人手里又在别处，没写怎么过去的（%s）' %
                           (label, name, s[:30]))
            if prev and not (st & prev) and not changed:
                out.append('%s：%s上一句还在%s，下一句就变成%s，中间没写交接动作（%s）' %
                           (label, name, '/'.join(sorted(prev)), '/'.join(sorted(st)), s[:30]))
            prev = st
            pending = False
        elif changed:
            prev = None      # 写了交接动作，链条从这里重算
            pending = False
    return out


def check_prop(text, stage, m1_text=None):
    """题眼道具的归属链：M1 查分幕骨架与故事正文、M2 带底本时查逐镜与跨稿。"""
    name = prop_name(m1_text or text, text)
    if not name:
        return []                # 开题卡没写题眼道具时交给 ① 四要素门禁，不硬猜物件
    out = []
    if stage == 'm1':
        skel = _section(text, r'##\s*②[^\n]*\n', r'##\s*②b|##\s*③')
        body = _section(text, r'##\s*③[^\n]*\n', r'##\s*④')
        out += _prop_chain(_sentences(body, name), name, '故事正文')
        s0 = [s for s in _sentences(skel, name) if name in s]
        b0 = [s for s in _sentences(body, name) if name in s]
        if s0 and b0:
            a = _state(s0[0], name)
            c = _state(b0[0], name)
            if a and c and not (a & c) and not _handoff(b0[0], name):
                out.append('%s：分幕骨架写「%s」，故事正文开头却「%s」，中间没交代怎么变的' %
                           (name, '/'.join(sorted(a)), '/'.join(sorted(c))))
    else:
        body = re.split(r'##\s*(?:③\s*)?附表', text)[0]
        out += _prop_chain(_sentences(body, name), name, '分镜内部')
        if m1_text:
            m1body = _section(m1_text, r'##\s*③[^\n]*\n', r'##\s*④') or m1_text
            last = [s for s in _sentences(m1body, name) if name in s]
            first = [s for s in _sentences(body, name) if name in s]
            if last and first:
                a = _state(last[-1], name)
                c = _state(first[0], name)
                if a and c and not (a & c) and not _handoff(first[0], name):
                    out.append('%s：底本结尾「%s」，分镜开头却「%s」，没交代怎么变的' %
                               (name, '/'.join(sorted(a)), '/'.join(sorted(c))))
    return out


def check_place(text):
    """场景对不上：同一份稿里，院落平房与电梯楼房同片出现。"""
    a = [w for w in PLACE_NEW if w in text]
    b = [w for w in PLACE_OLD if w in text]
    if a and b:
        return ['场景对不上：%s 与 %s 同片出现（例如高楼配堂屋、回胡同却上电梯）' %
                ('/'.join(a[:4]), '/'.join(b[:4]))]
    return []


def check_place_m12(m1_text, m2_text):
    """底本写过的住处，分镜里一次没出现，通篇换成另一类住处＝换地方没交代。"""
    b1 = [w for w in PLACE_OLD if w in m1_text]
    b2 = [w for w in PLACE_OLD if w in m2_text]
    a2 = [w for w in PLACE_NEW if w in m2_text]
    if b1 and not b2 and a2:
        return ['底本写「%s」，分镜一处没提，通篇是「%s」，换地方没交代' %
                ('/'.join(b1[:3]), '/'.join(a2[:3]))]
    return []


def _strip_requirements(text):
    """「⑥ 分镜脚本将按什么要求制作」是要求节，里面必须列举被禁的说法本身。

    不剔掉的话，规矩里写的反例（回胡同却上电梯、走廊灯忽冷忽暖）会把自己的稿子判违规。
    """
    # 只剔「⑥」这一节，不吞掉它后面的 ⑦/⑧；要求节标题各稿略有不同，按节边界切
    return re.sub(r'^##\s*⑥[^\n]*\n.*?(?=^##\s|\Z)', '', text or '', flags=re.S | re.M)


# ── 本片标准卡：出稿时自己写进附表，检查按它逐项核，不把缺口留给人 ──
# 不靠穷举同义词：稿子先登记「全片只有哪一处地方、哪一种光、道具经过哪几处」，
# 正文里凡跟登记对不上的说法一律判不合格，换没登记过的新说法也照样抓得住。
DECL_PLACE = re.compile(r'^\s*[-*]?\s*(?:本片地点|场景与光)[：:]\s*(.+)$', re.M)
DECL_LIGHT = re.compile(r'^\s*[-*]?\s*(?:本片主光|场景与光)[：:]\s*(.+)$', re.M)
DECL_PROP = re.compile(r'^\s*[-*]?\s*(?:本片题眼道具|题眼道具去向)[：:]\s*(.+)$', re.M)
DECL_SECS = re.compile(r'^\s*[-*]?\s*(?:本片总时长|时长合计)[：:]\s*(.+)$', re.M)

# 剧本层的「故事三段卡」：出稿时自己把本片地点、开场交代什么、结尾落在哪写死，
# 检查照这三项核正文首段与末段。换了卡外的新说法一样判不合格，不靠列同义词。
ARC_PLACE = re.compile(r'^\s*[-*]?\s*故事地点[：:]\s*(.+)$', re.M)
ARC_OPEN = re.compile(r'^\s*[-*]?\s*开场交代[：:]\s*(.+)$', re.M)
ARC_END = re.compile(r'^\s*[-*]?\s*结尾落点[：:]\s*(.+)$', re.M)
# 剧本是故事，不是脚本：场头、内外景抬头、镜头怎么拍，都是分镜脚本那一步的东西
SCRIPT_HEAD = re.compile(r'^\s*(?:场|镜|段)\s*[0-9一二三四五六七八九十]|^[^\n]{0,8}[内外]景[·・]', re.M)
CAMERA_WORDS = (u'画面', u'镜头', u'机位', u'推近', u'特写', u'运镜', u'构图',
                u'光影', u'景别', u'切回', u'黑屏', u'分镜脚本')

# 色温是封闭的两类物理属性，不是同义词清单；任何「发青／泛蓝／冷白」都归冷，
# 任何「暖黄／昏黄／橙光」都归暖。只用不含歧义的字，避开「照得发白」这类亮度描写。
COLD_WORDS = ('冷', '青', '蓝')
WARM_WORDS = ('暖', '黄', '橙', '昏')
OLD_MARKS = ('院子', '院坝', '院墙', '院里', '院内', '院门口', '堂屋', '土炕', '农房', '平房', '柴火', '菜地', '村口',
             '胡同', '弄堂', '四合院')
NEW_MARKS = ('高楼', '电梯', '楼道', '单元楼', '公寓', '小区', '物业',
             '地下车库', '门禁', '楼房', '楼层')
PUT_PAT = re.compile(
    r'(?:摆在|放在|搁在|压在|摊在|留在|挂在|塞在|立在|搁到|推到|收到|放到|塞进|收进)'
    r'([^，。；、\s]{1,10})')


def _appendix(text):
    """只取附表那一节，不把后面的卡片、提示词算进登记。"""
    parts = re.split(r'##\s*(?:③\s*)?附表', text or '')
    if len(parts) < 2:
        return ''
    return re.split(r'\n##\s', parts[1])[0]


def declared(text):
    """读附表里本片自己登记的标准；返回四项，没写就是空串。"""
    tail = _appendix(text)

    def _one(pat):
        m = pat.search(tail)
        return m.group(1).strip() if m else ''

    return {'place': _one(DECL_PLACE), 'light': _one(DECL_LIGHT),
            'prop': _one(DECL_PROP), 'secs': _one(DECL_SECS)}


def declared_seconds(text):
    """本片总时长：先读稿内登记；没写具体数字，工具自己把各镜声明的秒数加起来当标准。

    标准始终由工具拿到手，不跳过、不拒绝、不找人要参数。
    """
    d = declared(text).get('secs', '')
    m = re.search(r'(\d+(?:\.\d+)?)\s*秒', d)
    if m:
        return float(m.group(1))
    m = re.search(r'(?:总|共|合计)\s*(\d+(?:\.\d+)?)\s*秒', text or '')
    if m:
        return float(m.group(1))
    secs = [float(x) for x in re.findall(
        r'\*\*镜\s*\d+\s*[（(]\s*(\d+(?:\.\d+)?)\s*秒', text or '')]
    return sum(secs) if secs else 0.0


def check_decl(text, m1_text=None):
    """C5：正文必须和本片登记的标准逐项对上。"""
    tail = _appendix(text)
    if len(tail.strip()) < 40:      # 短考题只带「## 附表」四个字，不是交付稿，不拿登记卡要求它
        return []
    d = declared(text)
    out = []
    for k, label in (('place', '场景与光／本片地点'),
                     ('prop', '题眼道具去向'), ('secs', '时长合计')):
        if not d[k]:
            out.append('附表没登记「%s」：出稿时要把本片标准写全，检查才能照着核' % label)
    # 登记了就得写死：总秒数要是具体数字，不许留「待定／见实算值／现算」这类占位等人补
    if d['secs']:
        if not re.search(r'\d+(?:\.\d+)?\s*秒', d['secs']):
            out.append('附表「时长合计」没写具体秒数：出稿时就把总秒数算出来写死，不许留给用户补')
        if any(w in d['secs'] for w in ('待定', '见实算值', '现算', '实算值', '交付门')):
            out.append('附表「时长合计」写了占位说法：标准要写死，不许留给用户补')
    if out:
        return out
    body = re.split(r'##\s*(?:③\s*)?附表', text)[0]
    m3 = re.search(r'##\s*③[^\n]*分镜脚本[^\n]*\n', body)
    if m3:
        body = body[m3.end():]

    # ① 灯：登记一种色温，正文不许出现另一类
    anchor_l = d['light'] or d['place']
    is_cold = any(w in anchor_l for w in COLD_WORDS)
    is_warm = any(w in anchor_l for w in WARM_WORDS)
    if is_cold != is_warm:
        bad = WARM_WORDS if is_cold else COLD_WORDS
        for sent in re.split(r'[。！？\n，,；;]', body):
            if any(w in sent for w in bad) and any(w in sent for w in ('灯', '光', '亮', '照', '管', '泡')):
                out.append('灯色跟本片登记的不一致：登记「%s」，正文写「%s」' %
                           ('冷' if is_cold else '暖', sent.strip()[:24]))
                break

    # ② 地方：登记「全片一处」，正文冒出另一类住处就是换了地方
    anch = d['place']
    a_old = any(w in anch for w in OLD_MARKS)
    a_new = any(w in anch for w in NEW_MARKS)
    bad_marks = NEW_MARKS if a_old else (OLD_MARKS if a_new else OLD_MARKS + NEW_MARKS)
    for sent in re.split(r'[。！？\n]', body):
        hit = [w for w in bad_marks if w in sent and w not in anch]
        if hit:
            out.append('地方跟本片登记的不一致：登记「%s」，正文出现「%s」' %
                       (anch[:16], '/'.join(hit[:2])))
            break

    # ③ 道具：只认登记过的去向链，冒出链外落点就是凭空换地方
    chain = d['prop']
    name = prop_name(m1_text or text, text)
    # 骨架稿只写「逐镜交接」没有具体落点时，交回 C3 的交接动作判据，不误报
    if chain and name and chain.count('→') >= 2:
        seen = set()
        for sent in re.split(r'[。！？\n]', body):
            if name not in sent:
                continue
            # 只看「这件东西被放到哪儿」：道具名后面紧跟着的落点动词，
            # 别把同句里别人（放大镜、纸条）的动作算到它头上
            for nm in re.finditer(re.escape(name), sent):
                near = sent[nm.end():nm.end() + 12]
                for m in PUT_PAT.finditer(near):
                    spot = m.group(1)
                    keys = [spot[i:i + 2] for i in range(max(1, len(spot) - 1))]
                    # 同一处落点只报一次，不刷屏
                    if not any(k in chain for k in keys) and spot[:3] not in seen:
                        seen.add(spot[:3])
                        out.append('%s 落到「%s」，本片登记的去向链里没有这一处' % (name, spot[:8]))
    return out


def _story_paras(text):
    """只取 ③ 故事剧本的段落，按空行分段。"""
    m = re.search(r'##\s*③[^\n]*\n(.*?)(?=\n##\s|\Z)', text, re.S)
    if not m:
        return []
    return [p.strip() for p in re.split(r'\n\s*\n', m.group(1)) if p.strip()]


def check_story_arc(text):
    """C6：剧本是故事，不是脚本。

    开头第一段先从登记的故事地点写起，把这地方是什么、哪天、出了什么事、谁在这儿
    交代清楚；交代完才进具体行为剧情；末段收在登记的落点上。全篇不写场头、
    不写镜头怎么拍——那是阶段二分镜脚本的事。
    """
    if re.search(r"##\s*③[^\n]*分镜脚本", text):
        return []          # 分镜脚本是脚本层，不是故事层
    if u"离线骨架说明" in text and u"待填骨架" in text:
        return []          # 填空用的骨架不是交付稿；成品稿由剧本门按这张卡硬查
    paras = _story_paras(text)
    if len(paras) < 3 or sum(len(p) for p in paras) < 120:
        return []          # 短考题不是交付稿，不拿三段卡要求它

    def _one(pat):
        m = pat.search(text)
        return m.group(1).strip() if m else u''

    d = {'place': _one(ARC_PLACE), 'open': _one(ARC_OPEN), 'end': _one(ARC_END)}
    out = []
    for k, label in ((u'place', u'故事地点'), (u'open', u'开场交代'), (u'end', u'结尾落点')):
        if not d[k] or any(w in d[k] for w in (u'待填', u'待定', u'见下', u'〈', u'<')):
            out.append(u'没把「%s」写死：出稿时自己登记本片实际值，检查照着核' % label)
    if out:
        return out

    def _hit(keys, para):
        """按登记的话逐字核对；换没列过的新说法也照样判不合格。"""
        grams = [keys[i:i + 3] for i in range(max(1, len(keys) - 2))]
        return any(g in para for g in grams)

    first, last = paras[0], paras[-1]
    if d['place'] not in first:
        out.append(u'故事开头没从「%s」交代起：一上来就是行为剧情，判不合格、退回重出' % d['place'])
    if not _hit(d['open'], first):
        out.append(u'开头没交代这地方是什么、哪天、出了什么事：对不上登记的「开场交代」')
    if len(first) < 40:
        out.append(u'开头交代只有 %d 字：地方、日子、由头、人要交代清楚' % len(first))
    if u'「' in first or u'“' in first:
        out.append(u'开头交代里塞了台词：先讲故事，对话从中间剧情起')
    if any(w in first for w in CAMERA_WORDS):
        out.append(u'开头写了镜头怎么拍：细到画面和行为是分镜脚本的事，剧本只讲故事')
    if SCRIPT_HEAD.search(u'\n'.join(paras)):
        out.append(u'正文出现场头／内外景抬头：那是脚本格式，剧本不写')
    if not _hit(d['end'], last):
        out.append(u'结尾没收在登记的落点上：末段对不上「结尾落点」')
    return out


def _scene_text(text):
    """C1 只按本片实际场景判定：③ 故事正文 ＋ ① 开题卡登记的那处地方。

    ⓪ 双源样本拆解、②c 对照表里写的都是别人片子里的场景（村口、院子、堂屋），
    拿它们跟本片的楼道比，会把「引用别片」误判成「本片一会儿村口一会儿楼道」。
    稿子没有 ③ 段时（自检探针、分镜片段），退回按全文查，不放过真打架的句子。
    """
    body = re.search(r'^##\s*③[^\n]*\n(.*?)(?=^##\s|\Z)', text or '', flags=re.S | re.M)
    if not body:
        return text or ''
    card = re.search(r'^##\s*①[^\n]*\n(.*?)(?=^##\s|\Z)', text or '', flags=re.S | re.M)
    return ((card.group(1) if card else '') + '\n' + body.group(1))


def run_all(text, stage='m1', m1_text=None):
    """返回 [(编号, 检查名, 是否通过, 说明)]，三处门禁直接勾。"""
    raw = text
    text = _strip_requirements(text)
    m1_text = _strip_requirements(m1_text) if m1_text else None
    res = []
    p = check_place(_scene_text(text))
    res.append(('C1', '场景前后同一个地方（无高楼配堂屋）', not p, '；'.join(p) or '无'))

    l = check_light(text)   # 剧本与分镜都查；剧本没有镜号时报错写「前文」
    res.append(('C2', '同一处灯前后一个色温（无忽冷忽暖）', not l, '；'.join(l) or '无'))

    pr = check_prop(text, stage, m1_text)
    res.append(('C3', '同一件东西去了哪有交代（不凭空换地方）', not pr, '；'.join(pr) or '无'))

    if stage == 'm2' and m1_text:
        pm = check_place_m12(m1_text, text)
        res.append(('C4', '分镜没把底本的地方悄悄换掉', not pm, '；'.join(pm) or '无'))
    if stage == 'm2':
        dl = check_decl(text, m1_text)
        res.append(('C5', '正文符合本片登记的标准（不用人眼兜底）', not dl, '；'.join(dl) or '无'))
    if stage == 'm1':
        arc = check_story_arc(raw)
        res.append(('C6', '剧本是故事：开头交代、中间剧情、结尾收住（不写成脚本）',
                    not arc, '；'.join(arc) or '无'))
    return res


def line_issues(text, stage='m1', m1_text=None):
    """供主引擎用：只列没过的。"""
    return [(c, '%s：%s' % (n, d)) for c, n, ok, d in run_all(text, stage, m1_text) if not ok]


TESTS = {
    '场景打架': '傍晚他回胡同，拎着袋子上三楼，电梯门合上，小区草坪上灯亮了。',
    '灯色打架': '## ③ 分镜脚本\n**镜1（6秒）**\n【中景·平视·固定·中心构图·声控灯冷白打亮水泥地】\n他抬手敲门。\n'
              '**镜2（6秒）**\n【近景·平视·固定·框中框·走廊灯暖黄照在门板上】\n他把手放下。\n## 附表\n',
    '散文灯色打架': '## ③ 分镜脚本\n**镜1（6秒）**\n'
              '他走到单元楼门口，声控灯冷白地亮起来，照着水泥地，他抬手敲门。\n'
              '小林（女·30·清亮·平·中·随意·楼道声）：「我上来了。」\n'
              '**镜2（6秒）**\n他推开门，走廊灯暖黄地照在门板上，他把手放下。\n'
              '小林（女·30·清亮·平·中·随意·楼道声）：「进来了。」\n## 附表\n',
    '散文灯色一致': '## ③ 分镜脚本\n**镜1（6秒）**\n'
              '他走到单元楼门口，声控灯冷白地亮起来，照着水泥地，他抬手敲门。\n'
              '**镜2（6秒）**\n他推开门，走廊灯冷白地照在门板上，他把手放下。\n## 附表\n',
    '道具换地方': '## ① 开题卡\n- **题眼道具**：狗项圈。\n## ② 分幕骨架\n张姨把项圈递给她。\n## ③ 故事剧本\n张姨把项圈勒紧，狗没动。\n## ④ 情感线\n',
    '干净稿': '## ① 开题卡\n- **题眼道具**：旧木梳。\n## ② 分幕骨架\n他把木梳递给她。\n## ③ 故事剧本\n她把木梳接过去，攥在手里。\n## ④ 情感线\n',
}


def self_test():
    print('=' * 56)
    print('前后对不上 · 自带考题')
    print('=' * 56)
    ok = 0
    total = 0
    cases = [
        ('场景打架应被拦', any(not x[2] and x[0] == 'C1' for x in run_all(TESTS['场景打架'], 'm1'))),
        ('灯色打架应被拦', any(not x[2] and x[0] == 'C2' for x in run_all(TESTS['灯色打架'], 'm2'))),
        ('散文稿灯忽冷忽暖应被拦', any(not x[2] and x[0] == 'C2' for x in run_all(TESTS['散文灯色打架'], 'm2'))),
        ('散文稿灯色一致零误报', all(x[2] for x in run_all(TESTS['散文灯色一致'], 'm2'))),
        ('剧本阶段同样查灯色（写稿时就拦）',
         any(not x[2] and x[0] == 'C2' for x in run_all(
             '## ③ 故事剧本\n他走到门口，声控灯冷白地亮起来。\n他推开门，走廊灯暖黄地照在门板上。\n',
             'm1'))),
        ('道具凭空换地方应被拦', any(not x[2] and x[0] == 'C3' for x in run_all(TESTS['道具换地方'], 'm1'))),
        ('干净稿零误报', all(x[2] for x in run_all(TESTS['干净稿'], 'm1'))),
        ('删掉自造的古今分类：古装词与现代物件同片不再判不合格',
         all(x[2] for x in run_all('状元骑着马车进京赶考，掏出手机扫了码付了外卖。', 'm1'))),
        ('跨稿换地方应被拦',
         any(not x[2] and x[0] == 'C4' for x in run_all(
             '## ③ 分镜脚本\n**镜1（6秒）**\n【中景·平视·固定·中心构图·电梯里冷白灯亮着】\n他进了单元楼。\n## 附表\n',
             'm2', '## ① 开题卡\n## ② 分幕骨架\n他回胡同，上了三楼。\n'))),
    ]
    for name, cond in cases:
        total += 1
        print('[%s] %s' % ('PASS' if cond else 'FAIL', name))
        ok += 1 if cond else 0
    print('-' * 56)
    print('考题：%d/%d 通过' % (ok, total))
    return 0 if ok == total else 1


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(self_test())
    if len(sys.argv) > 1:
        t = open(sys.argv[1], encoding='utf-8').read()
        st = 'm2' if '分镜' in t[:200] else 'm1'
        for c, n, good, d in run_all(t, st):
            print('[%s] %s %s  %s' % ('PASS' if good else 'FAIL', c, n, d))
        sys.exit(0)
    print('用法：consist_chk.py <文档.md>  或  consist_chk.py --test')
