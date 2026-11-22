#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logic_chain_chk —— 因果链硬检（跨题材，不含任何具体题材/人物/时长/镜数）

补的是 m1_gate 原来没有的一层：句子合格、技法合格，但因果接不上，照样退回。

L1 钱款链：稿里一旦出现借钱/欠账/寄钱/汇款/工钱/利息，必须同时给出
   ① 金额（数字）② 处置句（收/不收/没动/留着/攒）③ 处置理由句（怕/不敢/留着/等你/收了…就）
L2 承诺兑现：引号内出现「等我／等我回／回来取／还完就来／下回」这类承诺句，
   后 35% 必须出现兑现句或明确落空句（回来了／取走／没来／不来了／等不到／断了）
L3 道具交接：题眼道具每次出现时，若同句有交接动词（给/递/推/塞/放/摆/扔/收/留/拿走），
   句中必须有具体持有方（人名或「左手/右手+名」），不许出现「东西自己换了地方」
L4 职业反常识：主角职业与该职业的基本能力出现直接冲突即判不合格
   （锁匠/开锁匠↔打不开、撬不开自己上的锁；医生/护士↔不会包扎；厨师↔不会切菜）
L5 钱数算术：同时出现「一年N块」与「寄了M年」时，正文必须出现 N×M 这个数

用法：python logic_chain_chk.py <剧本md路径>
"""
import re, sys, io

MONEY_WORDS = ['借', '欠', '寄过钱', '汇款', '汇了', '工钱', '利息', '还钱', '还你', '还清']
KNOW_WORDS = ['收', '不收', '没动', '留着', '攒', '存着', '压在']
WHY_WORDS = ['怕', '不敢', '没敢', '等你', '留着', '收了', '还清']
PROMISE = ['等我回', '等我', '回来取', '还完就来', '还完就来取']
KEEP_WORDS = ['回来了', '取走', '来取', '没来', '不来了', '等不到', '没等到', '断了', '没回来']
HANDOVER_VERBS = ['给', '递', '推', '塞', '放', '摆', '扔', '收', '留', '拿走', '交给', '按在']
JOB_CLASH = [
    (['锁匠', '开锁', '配钥匙'], ['打不开', '撬不开', '开不了']),
    (['医生', '护士'], ['不会包扎', '不会缝']),
    (['厨师', '大厨'], ['不会切', '不会炒']),
]


def body_of(text):
    """取 ③ 故事剧本正文（没有就退回全文）。"""
    m = re.search(r'##\s*③.*?(?=\n##\s*[④⑤⑥⑦⑧])', text, re.S)
    return m.group(0) if m else text


def sentences(s):
    return [x for x in re.split(r'[。！？\n]', s) if x.strip()]


def parapraphs(s):
    return [p.strip() for p in s.split('\n') if p.strip() and not p.strip().startswith('#')]


def check_money(body):
    if not any(w in body for w in MONEY_WORDS):
        return (u"L1 钱款链（借/欠/寄/还 必须写清金额·处置·理由）", True, u"稿里没有钱款线")
    num = u"[零一二两三四五六七八九十百千\\d]{1,6}"
    amount = re.search(u"(借|欠|还|寄)[^。；]{0,8}" + num, body) or re.search(num + u"\\s*(块|元|万)", body)
    disposal = [x for x in sentences(body) if any(w in x for w in KNOW_WORDS)]
    why = [x for x in disposal if re.search(u"就|怕|不敢|没敢|等你|还清", x)]
    miss = []
    if not amount:
        miss.append(u"没写借/欠/寄/还的金额")
    if not disposal:
        miss.append(u"没写这笔钱怎么处置（收/不收/没动/留着）")
    if not why:
        miss.append(u"没写为什么这样处置")
    return (u"L1 钱款链（借/欠/寄/还 必须写清金额·处置·理由）", not miss,
            u"；".join(miss) if miss else u"金额、处置、理由齐全")


def check_promise(body):
    ps = parapraphs(body)
    hit = None
    for i, p in enumerate(ps):
        for w in PROMISE:
            if '「' in p and w in p:
                hit = (i, w)
                break
        if hit:
            break
    if not hit:
        return ('L2 承诺兑现（承诺句必须后文兑现或明确落空）', True, '没有承诺句')
    i, w = hit
    tail = '\n'.join(ps[int(len(ps) * 0.65):])
    ok = any(x in tail for x in KEEP_WORDS)
    return ('L2 承诺兑现（承诺句必须后文兑现或明确落空）', ok,
            ('承诺「%s」在后文有兑现/落空' % w) if ok else ('承诺「%s」后文没兑现也没落空' % w))


def prop_name(text):
    m = re.search(r'题眼道具\*{0,2}\s*[:：]\s*([^\n（(]+)', text)
    return m.group(1).strip() if m else ''


def check_handover(text, body):
    prop = prop_name(text)
    if not prop:
        return (u"L3 道具交接（每次换手写清交给谁）", False, u"① 里没有登记题眼道具")
    short = prop[:4] if len(prop) > 4 else prop
    core = prop[-1:]
    verb = u"给|递给|推|塞|放|摆|扔|收|留|交给|按在|拿走|捧|端|拿|抱|拎"
    holder = u"他|她|我|你|[\u4e00-\u9fa5]{2,3}(把|抱着|拿着|拎着|捧着|端着|递给|递给)"
    hits = []
    for s2 in sentences(body):
        if (short in s2 or prop in s2 or core in s2) and re.search(verb, s2):
            hits.append(s2)
    if not hits:
        return (u"L3 道具交接（每次换手写清交给谁）", False, u"全文没有一句写清题眼道具在谁手里")
    bad = [x.strip()[:26] for x in hits if not re.search(holder, x)]
    return (u"L3 道具交接（每次换手写清交给谁）", not bad,
            u"；".join(bad[:2]) if bad else (u"交接句 %d 处，都有持有方" % len(hits)))


def check_job_clash(body):
    bad = []
    for jobs, clashes in JOB_CLASH:
        for j in jobs:
            if j not in body:
                continue
            for c in clashes:
                if c in body:
                    bad.append('%s 与「%s」' % (j, c))
    return ('L4 职业反常识（主角职业不许和自己的本事打架）', not bad,
            '；'.join(bad[:2]) if bad else '0 处')


def cn2num(s):
    d = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    if s.isdigit():
        return int(s)
    if s in d:
        return d[s]
    total, cur = 0, 0
    for ch in s:
        if ch in d:
            cur = d[ch]
        elif ch == '十':
            total += (cur or 1) * 10
            cur = 0
        elif ch == '百':
            total += (cur or 1) * 100
            cur = 0
        elif ch == '千':
            total += (cur or 1) * 1000
            cur = 0
        else:
            return None
    return total + cur


def all_nums(s):
    """正文里所有能读成数的东西（阿拉伯数字＋中文数字）。"""
    out = set()
    for tok in re.findall(r'[零一二两三四五六七八九十百千\d]{1,8}', s):
        v = cn2num(tok)
        if v:
            out.add(v)
    return out


def check_math(body):
    per = re.search(r'一年\s*([零一二两三四五六七八九十百千\d]{1,6})\s*(?:块|元)?', body)
    yrs = re.search(r'寄了\s*([零一二两三四五六七八九十百千\d]{1,6})\s*年', body)
    if not (per and yrs):
        return ('L5 钱数算术（一年N×M年 必须等于正文的钱数）', True, '没有按年寄钱的写法')
    n, m = cn2num(per.group(1)), cn2num(yrs.group(1))
    if n is None or m is None:
        return ('L5 钱数算术（一年N×M年 必须等于正文的钱数）', True, '数字读不出来，跳过')
    total = n * m
    ok = total in all_nums(body)
    return ('L5 钱数算术（一年N×M年 必须等于正文的钱数）', ok,
            ('%d×%d=%d，正文有' % (n, m, total)) if ok else ('%d×%d=%d，正文没有这个总数' % (n, m, total)))




TRIGGER = [u"最后一天", u"最后一晚", u"最后", u"末班", u"搬走", u"关门", u"明天走", u"今晚就走", u"就没了"]
WHY_NOW = [u"再不来", u"来不及", u"就没了", u"就拆", u"只剩", u"就关门", u"最后", u"明天", u"赶", u"赶不上"]
STALL = [u"八年", u"六年", u"十年", u"多年", u"好几年", u"二十年", u"十几年"]
NOT_YET = [u"没来", u"没去", u"没搬", u"没开", u"没动", u"没敢", u"没找", u"等着", u"等过", u"还留着"]


def check_why_now(body):
    """为什么偏偏是现在：出现时间压力就必须同时交代非做不可的理由；没有时间压力则不适用。"""
    hits = [x for x in parapraphs(body) if any(w in x for w in TRIGGER)]
    if not hits:
        return (u"L6 动机·为什么是现在（有时间压力就要交代非现在不可）", True, u"本片没有截止式时间压力，不适用")
    for x in hits:
        if any(w in x for w in WHY_NOW):
            return (u"L6 动机·为什么是现在（有时间压力就要交代非现在不可）", True, u"时间压力段里有非做不可的理由")
    return (u"L6 动机·为什么是现在（有时间压力就要交代非现在不可）", False,
            u"写了时间压力，但没说为什么非这段时间不可")


def check_why_delay(body):
    """为什么拖到今天：只有「多年悬置」才要求交代；开店十年这类背景不算悬置。"""
    has_year = bool(re.search(u"[零一二两三四五六七八九十]+年", body))
    stall = [x for x in sentences(body)
             if any(w in x for w in (u"一直", u"这些年", u"还留着", u"没搬", u"没来", u"没敢", u"等过", u"守", u"锁着", u"放着"))]
    if not has_year:
        stall = []
    if not stall:
        return (u"L7 动机·为什么拖到今天（有多年悬置才要求交代）", True, u"没有多年悬置，不适用")
    why = [x for x in sentences(body)
           if any(w in x for w in (u"怕", u"不敢", u"走不开", u"不知道", u"因为", u"只有", u"孩子", u"妈", u"没人",
                                     u"拆", u"通知", u"最后", u"搬", u"租金", u"涨"))]
    return (u"L7 动机·为什么拖到今天（有多年悬置才要求交代）", bool(why),
            (u"悬置 %d 处，有理由句" % len(stall)) if why else u"写了多年悬置，却没有一句交代为什么一直没动")



THEME_TAGS = [
    (u"青梅竹马", [u"小时候", u"童年", u"上学", u"校门口", u"弹珠", u"同桌", u"七岁", u"那年"]),
    (u"发小", [u"小时候", u"童年", u"上学", u"校门口", u"弹珠", u"七岁"]),
    (u"初恋", [u"第一次", u"喜欢", u"那时候", u"小时候"]),
]


def check_theme_landed(text, body):
    """题材登记了关系，正文就必须有这种关系的具体戏；只写一句设定不算。"""
    card = u""
    for m in re.finditer(u"一句话 Logline：(.+)|一句话故事核：(.+)", text):
        card += (m.group(1) or m.group(2) or u"")
    for tag, ev in THEME_TAGS:
        if tag not in card:
            continue
        shared = (u"一起", u"两个人", u"给他", u"给她", u"挂到", u"分", u"蹲", u"教", u"背", u"牵", u"送", u"陪")
        hit = [x for x in sentences(body)
               if any(w in x for w in ev) and any(s in x for s in shared)]
        if hit:
            return (u"L8 题材落地（登记的关系必须在正文里演出来）", True,
                    u"「%s」有一整句两人共同的童年戏" % tag)
        return (u"L8 题材落地（登记的关系必须在正文里演出来）", False,
                u"登记了「%s」，正文里没有一句戏兑现这段关系" % tag)
    return (u"L8 题材落地（登记的关系必须在正文里演出来）", True, u"没有需要落地的关系题材")


def run_all(path):
    text = io.open(path, encoding='utf-8').read()
    body = body_of(text)
    out = [check_money(body), check_promise(body), check_handover(text, body),
           check_job_clash(body), check_math(body),
           check_why_now(body), check_why_delay(body), check_theme_landed(text, body)]
    return out


def main():
    p = sys.argv[1]
    for name, ok, info in run_all(p):
        print('[%s] %s  （%s）' % ('PASS' if ok else 'FAIL', name, info))


if __name__ == '__main__':
    main()
