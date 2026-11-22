#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M1 语义合理性自检（通用，不绑题材）。

扫剧本 / 分镜交付 md 的「## ③ 故事剧本」正文段，揪出两类需人工复核的
疑似语义错（机器先揪，人工最终判，避免漏给观众看）：

  A. 无生命物疑似自己位移 / 摆姿态
     —— 句中含无生命名词（机子 / 箱 / 布 / 照片 / 钱 / 门 …）紧邻位移动词
        （走 / 跑 / 站 / 坐 / 蹲 / 爬 / 迈 / 跳 / 躺 / 立 / 跪 / 趴），
        且句内没有使动前缀（搬 / 抬 / 挪 / 运 / 拿 / 推 / 拉 / 送 / 带），
        即「机子走」「箱子站」这类错。使动复合（搬走 / 抬走 / 挪走）不算。

  B. 模糊指代
     —— 出现「这 / 那 ＋（破 / 老 / 小）？＋ 玩意儿 / 东西 / 啥 / 什么」
        这类不点名的具体名词，提醒改成具体物（机子 / 缝纫机 / 纸箱）。

用法：python m1_semchk.py <md文件路径>
"""
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 常见无生命名词（通用，不绑具体题材）
INANIMATE = [
    '机子', '缝纫机', '箱子', '纸箱', '盒子', '布袋', '红布', '布', '纸片',
    '照片', '相片', '钱', '门', '桌子', '椅子', '碗', '杯子', '鞋', '鞋样',
    '灯泡', '电视', '手机', '自行车', '车', '铁疙瘩', '砖', '书', '本子',
    '绳子', '线轴', '抽板', '铁', '桌子', '柜子', '盆', '桶',
]
# 仅生命体 / 拟人才能发出的位移动词或姿态动词
LIFE_VERBS = ['走', '跑', '奔', '站', '坐', '蹲', '爬', '迈', '跳', '躺', '立', '跪', '趴']
# 使动前缀（人让物位移，复合后不算物自己动）
CAUSE_VERBS = ['搬', '抬', '挪', '运', '拿', '推', '拉', '送', '带', '扛', '抱', '拎']
# 人称代词（句内出现这些单字代词，危险动词视为人发出，不算物自己动）
PERSON = ['他', '她', '我', '你', '咱', '人']
# 通用人名动作模式：2–4 个中文字（人名/角色）后紧跟一个人物动作动词，
# 命中说明该句有人物在执行动作，无生命物只是伴随/地点，A 类整句跳过。
# 不再写死具体角色名——任何题材的人物都靠这条通用识别，杜绝"换题材就误报"。
HUMAN_ACTION = re.compile(
    r'[\u4e00-\u9fa5]{2,4}(?:拎|扛|抱|背|拿|端|蹲|走|站|坐|跑|爬|跪|躺|趴|'
    r'立|迈|跳|敲|说|看|问|回|转|洗|搓|擦|放|推|拉|递|指|摆|按|拧|翻|听|贴|拆|装)'
)
# 模糊指代词
VAGUE = ['玩意儿', '东西', '啥', '什么', '玩意']

# 具体名词白名单（用于 B 类：若前文已点名，模糊词可豁免，这里仅作提示）
CONCRETE_HINT = ['机子', '缝纫机', '纸箱', '箱子', '布', '鞋样', '红布', '照片', '手机', '门', '桌子']


def extract_body(text):
    m = re.search(r'## ③.*?(?=## ④)', text, re.S)
    if m:
        return m.group(0)
    # 无 ③ 标记时退化为全文件轻扫（分镜稿等）
    return text


def split_sentences(body):
    parts = re.split(r'(?<=[。！？\n])', body)
    return [p.strip() for p in parts if p.strip()]


def check(path):
    text = open(path, encoding='utf-8').read()
    body = extract_body(text)
    sents = split_sentences(body)
    issues_a = []
    issues_b = []

    for i, s in enumerate(sents):
        # ---- A：无生命物 + 危险动词 ----
        for noun in INANIMATE:
            if noun not in s:
                continue
            for v in LIFE_VERBS:
                # 名词与动词之间不许跨分句标点（，。、；！？“”引号换行），
                # 否则"老张把门推开，机子慢慢走"会把"门+走"乱配成一对。
                gap = r'[^，。、；！？\n“”‘’]{0,6}'
                near = re.search(re.escape(noun) + r'(' + gap + r')' + re.escape(v), s) or \
                       re.search(re.escape(v) + r'(' + gap + r')' + re.escape(noun), s)
                if not near:
                    continue
                # 「蹲着从门缝递进去」：无生命名词紧跟方位介词，是目的地不是主语。
                # 只按名词与动词的距离配，会把人做的动作误判成「门自己蹲」。
                pos_noun = s.find(noun, near.start(), near.end())
                if pos_noun > 0 and re.search(
                        u'(从|往|朝|向|到|进|回|沿|顺着|在|把|给|被|让)$',
                        s[max(0, pos_noun - 2):pos_noun]):
                    continue
                # 定位危险动词 V 在该片段中的位置
                pos_v = s.find(v, near.start(), near.end())
                if pos_v == -1:
                    pos_v = near.start()
                # 方位介词＋无生命地点＋动作＝人的位移（往单元门走／朝门口跑去／回到桌边坐下）：
                # "门/桌/车"在这里是目的地不是主语，不算"门自己走"。不修会误伤大量正常句。
                before = s[max(0, pos_v - 12):pos_v]
                if re.search(r'(往|朝|向|到|进|回|沿|顺着)[^，。、；！？\n]{0,8}$', before):
                    continue
                # 只看 V 前面 6 字窗口（含 V 本身）：窗口内的主语若是人，才视为人发出
                win = s[max(0, pos_v - 6):pos_v + 1]
                safe = False
                m_ha = HUMAN_ACTION.search(win)
                if m_ha:
                    head = m_ha.group()[:-1]          # 去掉末尾动词，剩人名/物名
                    if not any(ina in head for ina in INANIMATE):
                        safe = True                   # 头部不是无生命物 → 是人名动作
                # 代词（他/她/我/你）按整句判定：代词必是人，且不误伤真错句
                if not safe and any(p in s for p in PERSON):
                    safe = True
                if safe:
                    continue
                # 排除使动复合：搬走 / 抬走 / 挪走 …（动词前紧邻为使动词即人让物动）
                if pos_v > 0 and s[pos_v - 1] in CAUSE_VERBS:
                    continue
                issues_a.append((i + 1, s, f'{noun}+{v}'))
                break

        # ---- B：模糊指代 ----
        for m2 in re.finditer(r'[这那](?:破|老|小)?(' + '|'.join(VAGUE) + r')', s):
            issues_b.append((i + 1, s, m2.group(0)))

    print(f'文件：{path}')
    print(f'\n[A] 无生命物 + 位移动词疑似（已排除使动复合，需人工复核）：{len(issues_a)} 处')
    for ln, s, tag in issues_a:
        print(f'  句{ln} [{tag}]：{s}')

    print(f'\n[B] 模糊指代（这/那+玩意儿/东西/啥/什么，需人工复核）：{len(issues_b)} 处')
    for ln, s, w in issues_b:
        print(f'  句{ln} [{w}]：{s}')

    if not issues_a and not issues_b:
        print('  ✅ 未检出疑似语义错（仍建议人工通读一遍）')
    return len(issues_a) + len(issues_b)


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--test':
        # 自带考题：真错必须抓到，常见正常句不许误报
        import tempfile, os
        cases = [
            # (句子, 期望报告条数, 说明)
            ('机子慢慢走开了。', 1, '真错：机子自己走'),
            ('箱子站在墙角，一动不动。', 1, '真错：箱子站'),
            ('老张把门推开，机子慢慢走开了，箱子站在一边。', 2, '跨分句不许乱配对：只报机子走/箱子站，不报门'),
            ('小雷拎着水桶蹲到门口。', 0, '人蹲不误报'),
            ('周敏蹲在地上，把鞋样按大小理齐。', 0, '人蹲+鞋样不误报'),
            ('这破机子今天必须搬走。', 0, '使动"搬走"不算机子自己走'),
            ('他进门先看了一眼机子，说这号蜜蜂牌的铁厚。', 0, '代词主语句不误报'),
            ('刘师傅没急着搬，蹲下去把机头往下按了按。', 0, '人名+蹲不误报'),
            ('师傅尝不出却说咸了，他没反驳。', 0, '无危险组合'),
            ('小林两手空着，转身往单元门走。', 0, '往+门+走是人的位移，门是目的地不误报'),
            ('他朝门口跑去，把箱子撂在台阶上。', 0, '朝+门口+跑不误报'),
            ('老陈蹲着从门缝把白蜡烛递进去。', 0, '蹲着从门缝：门缝是方位不是主语'),
            ('门慢慢走开了。', 1, '真错：门自己走，仍需抓到'),
        ]
        ok = True
        for text, expect, why in cases:
            fd, tmp = tempfile.mkstemp(suffix='.md')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write('## ③ 故事剧本\n' + text + '\n')
            n = check(tmp)
            os.remove(tmp)
            mark = 'PASS' if n == expect else 'FAIL'
            if n != expect:
                ok = False
            print(f'[{mark}] 期望{expect}实际{n}  {why}')
        print('\n结论：' + ('考题全过 ✅' if ok else '有考题不过 ❌'))
        sys.exit(0 if ok else 1)
    if len(sys.argv) < 2:
        print('用法：python m1_semchk.py <md文件路径> | --test')
        sys.exit(1)
    check(sys.argv[1])
