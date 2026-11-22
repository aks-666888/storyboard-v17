# -*- coding: utf-8 -*-
# space_chk.py —— 空间与走位硬检（v2.9.45）
# 只查机器能判死的「画面站不住」：
#   S1 同一镜内同一人不许同时在画左和画右（也不许同时在门里和门外）
#   S2 全片同一角色/位置的左右必须固定：驾驶位、后座、车门、门不能忽左忽右
#   S3 进车门必须先在稿子里出现「开门」，不许门没开就坐进去
#   S4 不许「车尾/后备箱」与「进车门」出现在同一条动作里（人不是从后备箱进的）
import io
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_m2

SIDE = [u"画左", u"画右"]
INOUT = [u"门里", u"门外"]

# 位置标签：同一稿里只能固定一个左右（或里外）
ROLE = [u"驾驶位", u"副驾", u"后座", u"右后座", u"左后座", u"车门", u"右后门",
        u"铁门", u"店门", u"柜台", u"门口"]

ENTRY = [u"坐进", u"跨进", u"上了车", u"上车坐"]
OPEN = [u"开门", u"拉开车门", u"拉开半扇", u"把门开", u"门开", u"门敞", u"敞着门"]
TRUNK = [u"车尾", u"后备箱", u"尾箱"]

_NAME = re.compile(u"([\u4e00-\u9fa5]{2,3})(?:在|站在|坐在|蹲在|站在车)|([\u4e00-\u9fa5]{2,3})(?:在|站在|坐在)(画左|画右)")
_SIDE_OF = re.compile(u"([\u4e00-\u9fa5]{2,4})在(画左|画右)")


def _persons(prose):
    """粗略取人名：出现两次以上的 2–3 字中文词，且不是方位词。"""
    cand = re.findall(u"[\u4e00-\u9fa5]{2,3}", prose)
    cnt = {}
    for c in cand:
        cnt[c] = cnt.get(c, 0) + 1
    return [c for c, n in cnt.items() if n >= 2 and c not in
            (u"画左", u"画右", u"门里", u"门外", u"画面", u"机位", u"车门")]


def _clauses(prose):
    return [c for c in re.split(u"[，。；：、]", prose) if c.strip()]


def check_inframe(text):
    """S1：同一镜内同一人/位置不许同时在画左和画右（或门里和门外）。"""
    bad = []
    for no, _sec, prose in audit_m2.shots(text):
        left, right, inside, outside = [], [], [], []
        for c in _clauses(prose):
            for m in _SIDE_OF.finditer(c):
                subj, side = m.group(1), m.group(2)
                if u"画左" in side:
                    left.append(subj)
                else:
                    right.append(subj)
            for w in INOUT:
                if w in c:
                    (inside if w == u"门里" else outside).append(c[:14])
        for s in set(left) & set(right):
            bad.append(u"镜%d：%s 同时在画左和画右" % (no, s))
        for c in _clauses(prose):
            if u"门里" in c and u"门外" in c:
                bad.append(u"镜%d：同一句里既在门里又在门外（%s）" % (no, c[:14]))
        # 同一镜里同一人既站在又被写成坐着且都在同一侧之外
        for c in _clauses(prose):
            if u"站着" in c and u"坐着" in c:
                bad.append(u"镜%d：同一句里既站又坐（%s）" % (no, c[:14]))
    return bad


def check_axis(text):
    """S2：同一场里，同一角色的左右必须固定（换场可以换侧，同场不许漂）。

    v2.9.49：不再只认驾驶位／后座／柜台这些写死的场景词——角色名从稿子里自己抓，
    场按每镜第一个地点词切块，同块内同一人出现两种侧别即报。
    """
    PLACE = [u'门', u'门口', u'窗外', u'窗', u'桌', u'桌边', u'床', u'床沿', u'柜', u'台', u'架', u'墙',
             u'地砖', u'车', u'车厢', u'船', u'楼梯', u'楼道', u'走廊', u'屋', u'房', u'街',
             u'巷', u'摊', u'店', u'柜台', u'锅', u'场', u'院', u'病房', u'诊室', u'车间',
             u'仓库', u'码头', u'田埂', u'灶前', u'炕', u'帐篷', u'机舱', u'驾驶室']
    BAD_TAIL = u'口门桌床柜台架墙车船楼道屋房间角边里外上下前后旁侧'
    # 一场怎么切：取本镜出现过的全部地点词，与上一镜有交集就算同一场，
    # 不许只看「第一个命中的词」——那样「窗在画右」和「床在画左」会被切成两场，
    # 同一人换个方位就漏掉了。
    blocks, cur_tokens, cur = [], set(), []
    for no, _sec, prose in audit_m2.shots(text):
        toks = set(w for w in PLACE if w in prose)
        if cur and toks and cur_tokens and not (toks & cur_tokens):
            blocks.append(cur)
            cur = []
        cur.append(prose)
        cur_tokens = (cur_tokens & toks) if cur_tokens and toks else (toks or cur_tokens)
    if cur:
        blocks.append(cur)
    bad = []
    for blk in blocks:
        mapping = {}
        for prose in blk:
            for m in re.finditer(u"([\u4e00-\u9fa5]{2,4})(?:在|站在|坐在|蹲在|靠在|位于)(画左|画右)", prose):
                name = m.group(1)
                if name.endswith(u'人') and len(name) > 3:
                    name = name[:-1]
                if not name or name[-1] in BAD_TAIL or u'画' in name:
                    continue
                mapping.setdefault(name, set()).add(m.group(2))
        for name, sides in mapping.items():
            if len(sides) > 1:
                bad.append(u"%s 在同一场里忽左忽右：%s" % (name, u"／".join(sorted(sides))))
    return bad


def check_entry(text):
    """S3：进车门/坐进去，必须有开门的动作（同镜或上一镜）。"""
    shots = audit_m2.shots(text)
    bad = []
    prev = u""
    for no, _sec, prose in shots:
        if any(w in prose for w in ENTRY):
            joined = prev + prose
            if not any(w in joined for w in OPEN):
                bad.append(u"镜%d：没开门的动作就把人写进车门" % no)
        prev = prose
    return bad


def check_trunk(text):
    """S4：车尾/后备箱不许和进车门并列在同一镜动作链里。"""
    bad = []
    for no, _sec, prose in audit_m2.shots(text):
        if any(w in prose for w in TRUNK) and any(w in prose for w in ENTRY + [u"进车门", u"钻进去"]):
            bad.append(u"镜%d：车尾/后备箱与进车门混在一起" % no)
    return bad


def run_all(text):
    return [
        ("S1", check_inframe(text)),
        ("S2", check_axis(text)),
        ("S3", check_entry(text)),
        ("S4", check_trunk(text)),
    ]


def main(p):
    t = io.open(p, encoding="utf-8").read()
    ok = True
    for code, bad in run_all(t):
        print((u"[%s] %s" % (code, u"0 处" if not bad else u"；".join(bad[:4]))))
        ok = ok and not bad
    print(u"通过" if ok else u"有项未过")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(u"用法：python space_chk.py <分镜稿.md>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
