# -*- coding: utf-8 -*-
import io
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame_parse
import obj_agent

DIST_W = [k for k, _ in frame_parse.TERM_DIST] + [w for _, v in frame_parse.TERM_DIST for w in v.split(u"|")]
ANGLE_W = [k for k, _ in frame_parse.TERM_ANGLE] + [w for _, v in frame_parse.TERM_ANGLE for w in v.split(u"|")]
MOVE_W = [w for w in frame_parse.TERM_MOVE.split(u"|")]
LIGHT = frame_parse.LIGHT
DIR = ['画左', '画右', '画中', '门里', '门外', '台前', '柜台后', '柜台前', '面朝', '背对',
       '侧身', '侧对', '朝门口', '朝柜台', '面对面', '各占一边']
SPOT = ['门', '门口', '门外', '门里', '窗', '桌', '桌边', '椅', '床', '床边', '柜', '柜边',
        '台', '台前', '架', '墙', '地砖', '地板', '地面', '车', '车内', '车厢', '船', '船舱',
        '梯', '楼梯', '楼', '楼道', '走廊', '过道', '屋', '房', '房门口', '间', '口', '路口',
        '街', '巷', '摊', '店', '柜台', '锅', '缸', '桶', '盆', '田', '河', '桥', '场', '院']
RESULT = ['停', '落', '按', '递', '塞', '压', '推', '挂', '拢', '夹', '攥', '放', '搁', '折', '捡', '擦']


def shots(text):
    pat = re.compile(u"\\*\\*镜(\\d+)（(\\d+)秒）\\*\\*\\s*\\n+(.+?)(?=\\n\\*\\*镜|\\n## |\\Z)", re.S)
    return [(int(m.group(1)), int(m.group(2)), m.group(3).strip()) for m in pat.finditer(text)]


def scan(text):
    """返回 [(镜号, 缺项串)]；空表＝逐镜九项落位。"""
    bad = []
    for no, sec, prose in shots(text):
        tag = []
        if not any(w in prose for w in DIST_W + ANGLE_W):
            tag.append(u"缺取景")
        if not any(w in prose for w in MOVE_W) and not frame_parse.motion_ok(prose):
            tag.append(u"缺运镜")
        if u"构图" not in prose:
            tag.append(u"缺构图")
        if not any(w in prose for w in LIGHT):
            tag.append(u"缺光影")
        if not any(w in prose for w in DIR):
            tag.append(u"缺方位朝向")
        if not any(w in prose for w in SPOT):
            tag.append(u"缺地点")
        if not any(w in prose for w in RESULT):
            tag.append(u"动作没落点")
        if sec > 15:
            tag.append(u"超15秒")
        for m in re.finditer(u"（([^）]*)）", prose):
            s = m.group(1)
            if re.search(u"[A-Za-z]{3,}", s) and not re.search(u"[\u4e00-\u9fa5]", s):
                tag.append(u"术语缺中文释义")
        oa = obj_agent.offenders(prose)
        if oa:
            tag.append(u"物件施事:%s" % oa[0][1])
        if tag:
            bad.append((no, u"／".join(tag)))
    return bad


def main(p):
    t = io.open(p, encoding="utf-8").read()
    ss = shots(t)
    print(u"镜数 %d，声明合计 %d 秒" % (len(ss), sum(s for _, s, _ in ss)))
    bad = []
    for no, sec, prose in ss:
        tag = []
        if not any(w in prose for w in DIST_W + ANGLE_W):
            tag.append(u"缺取景")
        if not any(w in prose for w in MOVE_W) and not frame_parse.motion_ok(prose):
            tag.append(u"缺运镜")
        if u"构图" not in prose:
            tag.append(u"缺构图")
        if not any(w in prose for w in LIGHT):
            tag.append(u"缺光影")
        if not any(w in prose for w in DIR):
            tag.append(u"缺方位朝向")
        if not any(w in prose for w in SPOT):
            tag.append(u"缺地点")
        if not any(w in prose for w in RESULT):
            tag.append(u"动作没落点")
        if sec > 15:
            tag.append(u"超15秒")
        for m in re.finditer(u"（([^）]*)）", prose):
            s = m.group(1)
            if re.search(u"[A-Za-z]{3,}", s) and not re.search(u"[\u4e00-\u9fa5]", s):
                tag.append(u"术语缺中文释义")
        if u"：" not in prose and u"「" not in prose:
            tag.append(u"缺台词/音效")
        oa = obj_agent.offenders(prose)
        if oa:
            tag.append(u"物件施事:%s" % oa[0][1])
        if tag:
            bad.append((no, u"／".join(tag)))
    for no, tag in bad:
        print(u"镜%d  ✗ %s" % (no, tag))
    if not bad:
        print(u"九项全落位、术语四项齐、站位齐、动作有落点：逐镜通过")


if __name__ == u"__main__":
    main(sys.argv[1])
