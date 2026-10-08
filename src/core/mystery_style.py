"""
悬疑推理文风生成模块
实现悬疑风格的Prompt控制、评分与重排
"""

from typing import List, Dict, Tuple

class MysteryStyleEngine:
    """悬疑推理文风引擎"""
    
    STYLE_PROFILE = {
        "name": "悬疑/硬汉侦探文风",
        "description": "冷静、压抑、充满暗示与伏笔，强调逻辑与氛围的张力",
        "features": {
            "句式": "短促有力，节奏感强，常用倒装句或省略句，制造紧迫感",
            "词汇": "阴冷、粗砺、精准，多用视觉上的冷色调（灰、黑、锈红）和嗅觉上的异味（烟草、霉味、血腥）",
            "修辞": "冷硬派隐喻（如'像一把生锈的手术刀'），环境反衬心理",
            "节奏": "步步紧逼，在看似平静的叙述中埋下不安的种子",
            "视角": "冷静的旁观者或充满怀疑的主观视角，注意细节的非正常放大",
            "情感": "压抑、焦虑、怀疑、冷漠，即使是恐惧也是克制的"
        },
        "constraints": {
            "sentence_length": (5, 40),
            "suspense_density": 0.25, 
            "dialogue_marker": "“ ”",
            "avoid_words": ["魔法", "仙气", "穿越", "系统", "大概", "也许", "唯美", "浪漫", "粉色"],
            "preferred_words": ["阴影", "锈迹", "审视", "破绽", "违和感", "窒息", "寒意", "沉默", "脚印", "血迹"]
        }
    }
    
    FEW_SHOT_EXAMPLES = [
        {
            "input": "走进一个房间",
            "output": "门轴发出令人牙酸的吱呀声，像是一声垂死的叹息。房间里弥漫着一股陈旧的霉味，混杂着某种更甜腻的气息——那是血。窗帘紧闭，只有一丝光线像刀片一样切入黑暗，照亮了地板上那只孤零零的高跟鞋。鞋尖朝向门口，仿佛主人在最后一刻还在试图逃离。"
        },
        {
            "input": "那个人在撒谎",
            "output": "他的手指无意识地摩挲着袖口，那里有一块不起眼的油渍。回答问题前，他的视线向右上方飘忽了0.5秒。太快了，这种下意识的停顿比任何言语都更诚实。他在掩饰什么？或者说，他在害怕什么？空气中似乎有什么东西正在绷紧，像一根即将断裂的琴弦。"
        },
        {
            "input": "夜晚的街道",
            "output": "路灯像患了白内障的眼球，投下惨白而浑浊的光。街道空无一人，只有风卷起废报纸在柏油路上摩擦出的沙沙声，听起来像某种爬行动物的脚步。下水道口冒着白汽，仿佛这座城市的地下正酝酿着某种不为人知的腐烂。我感觉有一双眼睛正在阴影里盯着我的后背。"
        }
    ]

    @classmethod
    def get_system_prompt(cls) -> str:
        features_text = "\n".join([f"  - {k}：{v}" for k, v in cls.STYLE_PROFILE["features"].items()])
        return f"""你是悬疑推理小说大师（如阿加莎、东野圭吾、雷蒙德·钱德勒），擅长创作逻辑严密、氛围压抑的悬疑故事。

【风格画像】
{cls.STYLE_PROFILE["description"]}

【核心特征】
{features_text}

【写作要求】
1. 氛围：压抑、阴冷、不安。多写阴影、角落、异味。
2. 细节：放大不合理的细节，制造“违和感”。
3. 逻辑：因果关系明确，哪怕是心理活动也要有迹可循。
4. 节奏：短句为主，像心跳一样紧凑。

【常用语】
{", ".join(cls.STYLE_PROFILE["constraints"]["preferred_words"])}"""

    @classmethod
    def get_few_shot_messages(cls, user_input: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": cls.get_system_prompt()}]
        for example in cls.FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": f"请用悬疑风格描述：{example['input']}"})
            messages.append({"role": "assistant", "content": example['output']})
        messages.append({"role": "user", "content": f"请用悬疑风格描述：{user_input}"})
        return messages

    @classmethod
    def get_self_evaluation_prompt(cls, content: str) -> List[Dict[str, str]]:
        criteria = "\n".join([f"{i+1}. {k}：{v}" for i, (k, v) in enumerate(cls.STYLE_PROFILE["features"].items())])
        return [
            {"role": "system", "content": "你是一位苛刻的悬疑小说编辑，专门审查故事的逻辑漏洞和氛围营造。"},
            {"role": "user", "content": f"""请对以下内容进行悬疑风格评分（0-1分）：

【待评估内容】
{content}

【评分标准】
{criteria}

【输出格式】
总评分：[0-1之间的数字]
分项评分：
1. 句式：[分数] - [评价]
2. 词汇：[分数] - [评价]
3. 修辞：[分数] - [评价]
4. 节奏：[分数] - [评价]
5. 视角：[分数] - [评价]
6. 情感：[分数] - [评价]

不合规点：
- [列出不符合悬疑风格的地方，如剧透、逻辑硬伤、氛围太轻松]

改进建议：
- [具体的改进建议]"""}
        ]

    @classmethod
    def get_rewrite_prompt(cls, content: str, evaluation: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": cls.get_system_prompt()},
            {"role": "user", "content": f"""请根据评估意见重写以下内容，只改风格不改事实：

【原文】
{content}

【评估意见】
{evaluation}

【重写要求】
1. 保持原意和情节不变
2. 强化悬疑氛围和细节描写
3. 节奏更紧凑，逻辑更严密
4. 输出完整重写后的内容"""}
        ]

class MysteryScorer:
    """悬疑风格评分器"""
    
    def __init__(self):
        self.style_keywords = {
            "悬疑": ["阴影", "沉默", "审视", "破绽", "违和", "窒息", "寒意", "血迹", "脚印", "指纹", "凶器", "动机", "不在场", "谎言", "真相", "谜底", "尸体"],
            "氛围": ["昏暗", "潮湿", "腐烂", "生锈", "嘶哑", "惨白", "空荡", "回声", "雨夜", "迷雾", "烟草", "酒精"],
            "负面": ["魔法", "仙气", "穿越", "系统", "大概", "也许", "唯美", "浪漫", "粉色", "阳光", "温暖", "可爱", "萌"]
        }

    def calculate_score(self, text: str) -> Dict[str, float]:
        scores = {}
        text_len = len(text)
        if text_len == 0: return {"总分": 0.0}

        # 1. 悬疑浓度
        suspense_count = sum(1 for word in self.style_keywords["悬疑"] if word in text)
        density = suspense_count / (text_len / 100 + 1)
        scores["悬疑浓度"] = min(density / 3.0, 1.0)

        # 2. 氛围营造
        atmosphere_count = sum(1 for word in self.style_keywords["氛围"] if word in text)
        scores["氛围营造"] = min(atmosphere_count / (text_len / 100 + 1) / 2.0, 1.0)

        # 3. 违和词扣分
        negative_count = sum(1 for word in self.style_keywords["负面"] if word in text)
        scores["违和词"] = max(0, 1.0 - negative_count * 0.5)

        weights = {"悬疑浓度": 0.40, "氛围营造": 0.40, "违和词": 0.20}
        total_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights)
        scores["总分"] = round(total_score, 3)
        return scores

    def rank_candidates(self, candidates: List[str]) -> List[Tuple[str, float]]:
        scored = []
        for cand in candidates:
            s = self.calculate_score(cand)
            scored.append((cand, s["总分"]))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

mystery_engine = MysteryStyleEngine()
mystery_scorer = MysteryScorer()