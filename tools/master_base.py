# -*- coding: utf-8 -*-
"""master_base.py —— 多风格大师指纹（v2.9.38）

一句话：字数只说明节奏，不说明通顺；通顺与逻辑看关系（谁做什么、指谁、几件、先后）。
这里量的不是「多少字」，而是「你这篇像不像你登记的那种风格」，以及句子里有没有东西可看。

四套指纹，全部取自公有领域原文：
  冷峻白描 —— 鲁迅《孔乙己》（1919）
  抒情细节 —— 朱自清《背影》（1925）
  市井口语 —— 老舍《骆驼祥子》（1936）
  诗性散文 —— 萧红《呼兰河传》（1940）

指纹指标（按每 100 字计密度）：可触细节、比喻、口语词、心理直说、抽象词，加句长中位与对话占比。
稿子先在开题卡登记「风格：X」，再拿 X 的指纹比；没登记直接不合格（不许拿一把尺子量所有片子）。
"""
import io
import re
import sys

STYLES = {
    u"冷峻白描": [
        u"魯鎭的酒店的格局，是和別處不同的：都是當街一個曲尺形的大櫃臺，櫃裏面豫備着熱水，可以隨時温酒。"
        u"做工的人，傍午傍晚散了工，每每花四文銅錢，買一碗酒——這是二十多年前的事，現在每碗要漲到十文。"
        u"孔乙己是站着喝酒而穿長衫的唯一的人。他身材很高大；靑白臉色，皺紋間時常夾些傷痕；一部亂蓬蓬的花白的鬍子。",
        u"孔乙己喝過半碗酒，漲紅的臉色漸漸復了原，旁人便又問道，『孔乙己，你當眞認識字麽？』"
        u"孔乙己看着問他的人，顯出不屑置辯的神氣。他們便接着說道：『你怎的連半個秀才也撈不到呢？』",
    ],
    u"抒情细节": [
        u"我與父親不相見已二年餘了，我最不能忘記的是他的背影。那年冬天，祖母死了，父親的差使也交卸了，"
        u"正是禍不單行的日子。我從北京到徐州，打算跟着父親奔喪回家。到徐州見着父親，看見滿院狼藉的東西，"
        u"又想起祖母，不禁簌簌地流下眼淚。",
    ],
    u"市井口语": [
        u"我們所要介紹的是祥子，不是駱駝，因爲『駱駝』只是個外號；那麼，我們就先說祥子，"
        u"隨手兒把駱駝與祥子那點關係說過去，也就算了。",
        u"祥子的手哆嗦得更厲害了，揣起保單，拉起車，幾乎要哭出來。他忽然想大喊一聲，把心中的痛快都喊出來。",
    ],
    u"诗性散文": [
        u"嚴冬一封鎖了大地的時候，則大地滿地裂着口。從南到北，從東到西，幾尺長的，一丈長的，"
        u"還有好幾尺寬的，滿地裂着口。嚴寒把大地凍裂了。",
        u"我家有一個大花園。這花園裏有蜂子、蝴蝶、蜻蜓、螞蚱，樣樣都有。"
        u"蝴蝶有白蝴蝶、黃蝴蝶。這種蝴蝶極小，不太好看，好看的是大紅蝴蝶，滿身帶着金粉。",
    ],
}

TOUCH = [u"张", u"張", u"枚", u"包", u"条", u"條", u"截", u"层", u"層", u"角", u"毛", u"灰", u"濕", u"湿", u"皱", u"皺", u"折",
         u"碗", u"碟", u"壶", u"壺", u"坛", u"罎", u"板", u"纸", u"紙", u"笔", u"筆", u"只", u"隻", u"颗", u"顆", u"块", u"塊", u"页", u"頁", u"摞", u"文"]
METAPHOR = [u"像", u"似", u"彷彿", u"如同", u"一般", u"好像"]
SPOKEN = [u"咋", u"啥", u"俺", u"咱", u"幹嘛", u"得", u"兒", u"吶", u"唄", u"嘿"]
PSY = [u"心裏", u"感到", u"覺得", u"難過", u"害怕", u"緊張", u"委屈", u"憤怒", u"眼淚"]
ABSTRACT = [u"幸福", u"溫暖", u"感動", u"命運", u"成長", u"治愈", u"救贖", u"人生"]


def _density(text, words):
    return round(100.0 * sum(text.count(w) for w in words) / max(1, len(text)), 2)


def fingerprint(text):
    sents = [s for s in re.split(u"[。！？；]", text) if s.strip()]
    ln = sorted(len(s) for s in sents) or [0]
    quote = sum(len(m) for m in re.findall(u"[「『“][^」』”]*[」』”]", text))
    return {
        u"细节": _density(text, TOUCH),
        u"口语": _density(text, SPOKEN),
        u"心理": _density(text, PSY),
        u"抽象": _density(text, ABSTRACT),
        u"句长中位": ln[len(ln) // 2],
        u"对话占比": round(100.0 * quote / max(1, len(text)), 1),
    }


def baselines():
    return {name: fingerprint(u"".join(texts)) for name, texts in STYLES.items()}


def _read_style(path):
    t = io.open(path, encoding="utf-8").read()
    for ln in t.split(u"\n"):
        st = ln.strip()
        if not st.startswith(u"- 风格"):
            continue
        for k in STYLES:
            if k in st:
                return k, t
    return None, t


def _prose(t):
    on, body = False, []
    for ln in t.split(u"\n"):
        st = ln.strip()
        if st.startswith(u"## ③"):
            on = True
            continue
        if on and st.startswith(u"## "):
            break
        if on and st and not re.match(r"^场[ \u3000]*\d+", st):
            if re.match(r"^[\u4e00-\u9fa5]{1,4}（[^）]{4,}）：", st):
                continue
            body.append(st)
    return body


def run_all(path):
    style, t = _read_style(path)
    paras = _prose(t)
    if not style:
        return [(u"A0 先登记风格卡（选哪套大师指纹来量）",
                 [u"开题卡没写「风格：冷峻白描／抒情细节／市井口语／诗性散文」，没有尺子就没法量"])]
    fp = fingerprint(u"".join(paras))
    bl = baselines()[style]
    out = [(u"A1 细节密度不干于本风格（%s）" % style,
            [] if fp[u"细节"] >= bl[u"细节"] * 0.5 else
            [u"本篇细节 %.2f，本风格 %.2f" % (fp[u"细节"], bl[u"细节"])]),
           (u"A3 口语密度贴合本风格（%s）" % style,
            [] if (fp[u"口语"] <= max(bl[u"口语"] * 2.0, 1.0)) else
            [u"本篇口语 %.2f，本风格 %.2f" % (fp[u"口语"], bl[u"口语"])]),
           (u"A4 心理直说不高于本风格",
            [] if fp[u"心理"] <= max(bl[u"心理"], 0.3) else [u"心理直说 %.2f，基线 %.2f" % (fp[u"心理"], bl[u"心理"])]),
           (u"A5 抽象词不高于本风格",
            [] if fp[u"抽象"] <= max(bl[u"抽象"], 0.1) else [u"抽象词 %.2f，基线 %.2f" % (fp[u"抽象"], bl[u"抽象"])]),
           (u"A6 句长中位不散（不超过本风格 2.5 倍）",
            [] if fp[u"句长中位"] <= 2.5 * bl[u"句长中位"] else
            [u"本篇 %d，本风格 %d" % (fp[u"句长中位"], bl[u"句长中位"])])]
    return out


def _selftest():
    bl = baselines()
    for k, v in bl.items():
        print(u"%s：细节 %.2f 口语 %.2f 心理 %.2f 抽象 %.2f 句长中位 %d 对话 %.1f%%"
              % (k, v[u"细节"], v[u"口语"], v[u"心理"], v[u"抽象"], v[u"句长中位"], v[u"对话占比"]))
    ok = len({v[u"口语"] for v in bl.values()}) > 1 and len({v[u"细节"] for v in bl.values()}) > 1
    print(u"[%s] 四套风格指纹互不相同" % (u"PASS" if ok else u"FAIL"))
    return ok


if __name__ == u"__main__":
    if sys.argv[1:2] == [u"--test"]:
        sys.exit(0 if _selftest() else 1)
    for p in sys.argv[1:]:
        print(u"==", p)
        for name, bad in run_all(p):
            print(u"[%s] %s" % (u"PASS" if not bad else u"FAIL", name))
            for b in bad:
                print(u"    ", b)
