"""
言情文风生成模块
实现言情风格的Prompt控制、评分与重排
"""

from typing import List, Dict, Tuple

class RomanceStyleEngine:
    """言情文风引擎"""
    
    STYLE_PROFILE = {
        "name": "言情/纯爱文风",
        "description": "细腻的情感流露与唯美的感官描写，侧重人物内心世界的刻画",
        "features": {
            "句式": "细腻柔美，多用长短句结合，善用排比与层递，注重语言的韵律感",
            "词汇": "情感色彩浓郁，多用感官形容词（视觉、触觉、听觉），避免过于生硬的动词",
            "修辞": "通感、比喻（花草、天气、光影）、拟人，将情绪具象化",
            "节奏": "舒缓、以此推动情感递进，在关键情感点进行特写式慢镜头描写",
            "视角": "深情的第三人称或沉浸式第一人称，聚焦于微表情与肢体语言",
            "情感": "极致的爱恨，细腻的拉扯，氛围感强，注重'此时无声胜有声'的张力"
        },
        "constraints": {
            "sentence_length": (5, 50),
            "emotion_density": 0.2, 
            "dialogue_marker": "“ ”",
            "avoid_words": ["系统", "逻辑", "参数", "硬核", "大概", "可能", "屌丝", "牛逼"],
            "preferred_words": ["眸光", "指尖", "滚烫", "窒息", "缱绻", "悸动", "沦陷", "微颤", "余晖", "破碎"]
        }
    }
    
    FEW_SHOT_EXAMPLES = [
        {
            "input": "两个人见面",
            "output": "隔着熙攘的人潮，她的目光还是精准地撞入了他眼底深处。那一瞬间，周遭的喧嚣仿佛被按下了静音键，只有心跳声震耳欲聋。他站在光影交界处，白衬衫被风吹起一角，连同那双含笑的桃花眼，轻易便揉碎了她积攒多年的防线。"
        },
        {
            "input": "他生气了",
            "output": "他没有说话，只是指尖用力到泛白，紧紧扣住手中的玻璃杯。平日里总是含笑的眸子此刻像是结了一层薄冰，寒意顺着视线蔓延，冻得她下意识瑟缩了一下。空气仿佛凝固，每一次呼吸都变得小心翼翼，生怕惊扰了这场即将爆发的风暴。"
        },
        {
            "input": "下雨天",
            "output": "雨丝细密地织成一张网，将这座城市温柔地困在其中。潮湿的水汽顺着半开的窗缝潜入，带着泥土特有的腥气，也勾起了那些发霉的旧时光。雨滴敲打在梧桐叶上，一声声，像是谁在心头轻叩，乱了节拍，也湿了眼眶。"
        }
    ]

    @classmethod
    def get_system_prompt(cls) -> str:
        features_text = "\n".join([f"  - {k}：{v}" for k, v in cls.STYLE_PROFILE["features"].items()])
        return f"""你是言情小说大神（如顾漫、匪我思存、桐华），擅长创作细腻动人、氛围感极强的言情小说。

【风格画像】
{cls.STYLE_PROFILE["description"]}

【核心特征】
{features_text}

【写作要求】
1. 描写：调动五感（视听嗅味触），特别是触觉和视觉的光影变化。
2. 心理：将抽象的情绪转化为具象的生理反应（如指尖发颤、呼吸停滞）。
3. 氛围：注重环境烘托，以景写情。
4. 词汇：优美、雅致，避免大白话和科技/公文用语。

【常用语】
{", ".join(cls.STYLE_PROFILE["constraints"]["preferred_words"])}"""

    @classmethod
    def get_few_shot_messages(cls, user_input: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": cls.get_system_prompt()}]
        for example in cls.FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": f"请用言情风格描述：{example['input']}"})
            messages.append({"role": "assistant", "content": example['output']})
        messages.append({"role": "user", "content": f"请用言情风格描述：{user_input}"})
        return messages

    @classmethod
    def get_self_evaluation_prompt(cls, content: str) -> List[Dict[str, str]]:
        criteria = "\n".join([f"{i+1}. {k}：{v}" for i, (k, v) in enumerate(cls.STYLE_PROFILE["features"].items())])
        return [
            {"role": "system", "content": "你是一位资深的言情小说主编，专门把控文稿的情感浓度和文字美感。"},
            {"role": "user", "content": f"""请对以下内容进行言情风格评分（0-1分）：

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
- [列出不符合言情风格的地方，如过于直白、缺乏美感、逻辑词过多]

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
2. 强化情感描写和氛围渲染
3. 使用更唯美细腻的词汇
4. 输出完整重写后的内容"""}
        ]

class RomanceScorer:
    """言情风格评分器"""
    
    def __init__(self):
        self.style_keywords = {
            "情感": ["悸动", "心跳", "窒息", "沦陷", "温柔", "缱绻", "酸涩", "滚烫", "冰凉", "颤抖", "眼眶", "泪", "吻", "拥抱", "指尖"],
            "唯美": ["光影", "余晖", "微风", "涟漪", "星辰", "破碎", "清澈", "朦胧", "斑驳", "白衣", "裙摆", "发丝"],
            "负面": ["系统", "逻辑", "参数", "硬核", "大概", "也许", "牛逼", "卧槽", "他妈的", "老子", "矩阵", "辐射"]
        }

    def calculate_score(self, text: str) -> Dict[str, float]:
        scores = {}
        text_len = len(text)
        if text_len == 0: return {"总分": 0.0}

        # 1. 情感浓度
        emotion_count = sum(1 for word in self.style_keywords["情感"] if word in text)
        density = emotion_count / (text_len / 100 + 1)
        scores["情感浓度"] = min(density / 3.0, 1.0)

        # 2. 唯美度
        beauty_count = sum(1 for word in self.style_keywords["唯美"] if word in text)
        scores["唯美度"] = min(beauty_count / (text_len / 100 + 1) / 2.0, 1.0)

        # 3. 违和词扣分
        negative_count = sum(1 for word in self.style_keywords["负面"] if word in text)
        scores["违和词"] = max(0, 1.0 - negative_count * 0.5)

        weights = {"情感浓度": 0.45, "唯美度": 0.35, "违和词": 0.20}
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

romance_engine = RomanceStyleEngine()
romance_scorer = RomanceScorer()