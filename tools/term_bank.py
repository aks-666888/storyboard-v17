# -*- coding: utf-8 -*-
"""专业术语库（唯一规则源）。

口径（用户给定规范，v2.9.33）：分镜九项里的取景、运镜、构图、光影用**影视专业术语**，
中英对照（英文原词 + 中文释义），术语直接写进散文句子，不另起【】字段行。
术语出现在正文属正常；N10 只拦【】字段行与「取景：」这类小标题。
"""
import re

TERMS = {
    "运镜": [
        u"Dolly In 物理推镜", u"Dolly Out 物理拉镜", u"Truck Left 左横移", u"Truck Right 右横移",
        u"Pedestal Up 机位垂直上升", u"Pedestal Down 机位垂直下降", u"Tilt Up 仰摇", u"Tilt Down 俯摇",
        u"Pan Left 左摇", u"Pan Right 右摇", u"Arc Shot 弧形运镜", u"Orbit Shot 环绕运镜",
        u"Circular Tracking 环形跟拍", u"Follow Shot 跟随运镜", u"Whip Pan 甩摇",
        u"Vertigo Effect 希区柯克变焦", u"Hitchcock Pull 希区柯克推镜", u"Spielberg Push 斯皮尔伯格慢推",
        u"Crane Up 升镜", u"Crane Down 降镜", u"Long Take 长镜头", u"Static Hold 静态锁帧",
        u"Handheld Motion 手持律动", u"Shaky Cam 剧烈抖镜", u"Through Frame 穿梭运镜",
        u"Flythrough 空间穿梭", u"Creep Shot 极慢潜行推镜", u"Slow Drift 缓慢漂移",
        u"Glide Shot 顺滑悬浮运镜", u"Floating Motion 悬浮感运镜", u"Staccato Motion 顿挫式运镜",
        u"Lateral Drift 侧向漂移", u"Recoil Pan 回弹摇镜", u"Rack Focus 快速焦点跳转",
        u"Pull Focus 缓慢跟焦", u"Parallax Motion 视差运动",
        u"Dolly Zoom 推拉变焦", u"Snorricam 身体固定机位", u"Crane Arc 升降弧线",
        u"Tilt Reveal 摇镜揭示",
        # v2.9.54 补：同一动作的常用英文写法也认，免得写对了却被判没写
        u"Tracking Shot 跟随运镜", u"Push In 缓推", u"Pull Out 缓拉", u"Follow Focus 跟焦",
        u"Static Camera 静态机位", u"Steadicam 斯坦尼康跟拍", u"Zoom In 变焦推近", u"Zoom Out 变焦拉远",
    ],
    "取景": [
        u"Extreme Long Shot 极远景", u"Long Shot 大全景", u"Full Shot 全景",
        u"Medium Long Shot 中全景", u"Medium Shot 中景", u"Medium Close-Up 中近景",
        u"Close-Up 近景", u"Big Close-Up 特写", u"Extreme Close-Up 大特写",
        u"Cowboy Shot 牛仔镜头", u"Two Shot 双人镜头", u"Three Shot 三人镜头",
        u"Group Shot 群像镜头", u"Single Shot 单人镜头", u"Clean Single 干净单人镜头",
        u"Over-the-Shoulder Shot 过肩镜头", u"Reverse Shot 反打镜头", u"Profile Shot 正侧镜头",
        u"Three-Quarter Shot 四分之三侧面", u"POV Shot 主观视角", u"Reaction Shot 反应镜头",
        u"Insert Shot 插入细节镜头", u"Insert Closeup 特写插入镜头", u"Cutaway 切出空镜",
        u"Eye-Level Shot 平视视角", u"Low Angle 低仰视角", u"Extreme Low Angle 极限低角度",
        u"High Angle 高俯视角", u"Bird's-Eye View 鸟瞰视角", u"Overhead Shot 顶俯镜头",
        u"Worm's-Eye View 虫眼视角", u"Dutch Angle 荷兰角", u"Oblique Shot 斜角镜头",
        u"Wide Shot 宽景", u"Establishing Shot 交代镜头", u"Hand Insert 手部特写",
    ],
    "构图": [
        u"Frame within Frame 框中框", u"Symmetrical Framing 对称构图", u"Asymmetrical Framing 非对称构图",
        u"Centered Framing 中心构图", u"Diagonal Framing 对角线构图", u"Layered Framing 多层构图",
        u"Leading Lines 引导线构图", u"Negative Space 留白构图", u"Negative Framing 负形构图",
        u"Deep Space Composition 纵深构图", u"Tight Framing 紧构图", u"Loose Framing 松构图",
        u"Free Frame 开放式无边界构图", u"Reflected Shot 反射构图", u"Split Frame 分割画面构图",
        u"Masked Frame 遮罩构图",
        u"Rule of Thirds 三分构图", u"Off-Center Framing 偏心构图", u"Detail Framing 细节框",
    ],
    "光影": [
        u"Key Light 主光", u"Fill Light 辅光", u"Ambient Fill 环境辅光", u"Rim Light 轮廓光",
        u"Rim Glow 轮廓光晕", u"Rim Separation 轮廓分离光", u"Backlight 逆光", u"Side Light 侧光",
        u"Back-Side Light 侧逆光", u"Kick Light 踢脚侧轮廓光", u"Top Light 顶光", u"Underlight 底光",
        u"Catchlight 眼神光", u"Practical Light 场景固有光源", u"Bounce Light 反光板反射光",
        u"Negative Fill 负补光", u"Specular Highlight 高光反光点", u"Hard Light 硬光",
        u"Soft Light 软光", u"Flat Lighting 平光", u"Cross Light 交叉光",
        u"Cast Shadow 投影", u"Low Key 低调光", u"High Key 高调光", u"Silhouette 剪影",
        u"Golden Hour 黄金时刻", u"Deep Focus 大景深",
    ],
}

CATS = ["运镜", "取景", "构图", "光影"]

# 兼容别名：只取英文原词，供按英文清单调用的旧调用方使用
EN_TERMS = dict((c, [w.partition(u" ")[0] for w in TERMS[c]]) for c in CATS)


def split_term(w):
    """'Dolly In 物理推镜' -> ('Dolly In', '物理推镜')。"""
    en, _, cn = w.partition(u" ")
    return en, cn


def hit(category, text):
    """返回文本里出现过的该类术语（英文原词或中文释义任一命中即算）。"""
    out = []
    for w in TERMS.get(category, []):
        en, cn = split_term(w)
        if re.search(re.escape(en), text, re.I) or (cn and cn in text):
            out.append(w)
    return out


def hit_all(text):
    """四类全扫，返回 {类: [命中术语]}。"""
    return dict((c, hit(c, text)) for c in CATS)


def all_terms():
    flat = []
    for cat in CATS:
        flat.extend(TERMS[cat])
    return flat


def english_terms():
    """库里含英文原词的条目（应为全部）。"""
    return [w for w in all_terms() if re.search(u"[A-Za-z]", w)]


def chinese_terms():
    """库里带中文释义的条目（应为全部）。"""
    return [w for w in all_terms() if re.search(u"[\u4e00-\u9fa5]", w)]


def has_english():
    """兼容旧调用：返回含英文的条目（库里全部中英对照，非空属正常）。"""
    return english_terms()


def missing(text):
    """返回这一镜四类里没写到的类别（九项覆盖自检用）。"""
    return [c for c in CATS if not hit(c, text)]


if __name__ == "__main__":
    import sys, os, io
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sk = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "storyboard-v17", "SKILL.md"), encoding="utf-8").read()
        ok = (len(all_terms()) >= 100
              and len(english_terms()) == len(all_terms())
              and len(chinese_terms()) == len(all_terms())
              and all(TERMS[c][0] in sk for c in CATS))
        print(u"术语表自检：%s（%d 条，中英对照 %d 条，四类首条均写进主规则）"
              % (u"通过" if ok else u"未过", len(all_terms()), len(english_terms())))
        sys.exit(0 if ok else 1)
    print(u"四类合计 %d 条；中英对照 %d 条" % (len(all_terms()), len(english_terms())))
    if len(sys.argv) > 1:
        if sys.argv[1].startswith("--"):
            print(u"用法：python term_bank.py <文档.md> 或 --test")
            sys.exit(2)
        t = io.open(sys.argv[1], encoding="utf-8").read()
        for cat, h in hit_all(t).items():
            if h:
                print(u"%s：%s" % (cat, u"／".join(h)))
