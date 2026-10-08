"""
科幻文风生成模块
实现Prompt层风格控制、多候选生成、重排序和自评回写
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import re


class SciFiStyleEngine:
    """科幻文风引擎"""
    
    # 科幻风格画像
    STYLE_PROFILE = {
        "name": "硬科幻/赛博朋克文风",
        "description": "融合了刘慈欣的宏大叙事与威廉·吉布森的赛博朋克质感的科幻风格",
        "features": {
            "句式": "冷静客观，多用陈述句和判断句，逻辑连接词丰富，兼具短促的动作描写与复杂的理论阐述",
            "词汇": "高科技密度，使用准确的科学术语或自洽的伪科学名词，避免玄幻/魔法词汇",
            "修辞": "科技隐喻，数据化描写，宏观与微观视角的快速切换",
            "节奏": "冷峻、紧凑，在信息过载与绝对寂静间切换",
            "视角": "客观记录者视角，或被技术异化的主观视角",
            "情感": "理性、克制，对技术/宇宙的敬畏，或对高科技低生活的冷漠疏离"
        },
        "constraints": {
            "sentence_length": (10, 60),  # 允许更极端的长短句
            "tech_density": 0.15,  # 科技词汇密度
            "dialogue_marker": "“ ”",  # 标准引号，或无引号的意识流
            "avoid_fantasy": ["魔力", "灵气", "修仙", "鬼魂", "穿越", "王爷", "宫殿"],
            "preferred_words": ["算法", "熵", "奇点", "神经", "接口", "辐射", "轨道", "矩阵", "全息", "合成"]
        }
    }
    
    # Few-shot示例
    FEW_SHOT_EXAMPLES = [
        {
            "input": "描述日出",
            "output": "恒星的光谱从长波向短波偏移，刺破了平流层的尘埃云。第一缕光子撞击在城市穹顶的复合材料外壳上，引发了连锁的光电效应。原本死寂的钢铁丛林瞬间被激活，无数全息广告牌在纳秒级延迟内同时亮起，将贫民窟的阴影染成了病态的霓虹色。"
        },
        {
            "input": "两个人告别",
            "output": "“连接断开。”K的声音没有任何波澜，像是一条预录的系统提示音。他拔掉了后颈的数据线，眼中的蓝色数据流逐渐熄灭。“记忆体已经备份上传了，肉体的距离没有意义。”她看着他，试图从那张合成皮肤的脸上读出一丝人类的犹豫，但只看到了义眼对焦时的机械微动。"
        },
        {
            "input": "描写一个废弃的房间",
            "output": "这间屋子是热力学第二定律的完美标本。空气中悬浮着过饱和的尘埃，全息投影仪早已因短路烧焦，散发着臭氧和烧焦塑料的味道。角落里，一台古老的服务器还在低声嗡嗡作响，红色的状态灯像是一只濒死的复眼，在黑暗中孤独地闪烁，计算着早已无人关心的哈希值。"
        }
    ]

    @classmethod
    def get_system_prompt(cls) -> str:
        """获取科幻风格的系统提示"""
        features_text = "\n".join([f"  - {k}：{v}" for k, v in cls.STYLE_PROFILE["features"].items()])
        
        return f"""你是科幻文学大师（如刘慈欣、威廉·吉布森、阿瑟·克拉克）的集合体，擅长创作硬科幻与赛博朋克风格的小说。

【风格画像】
{cls.STYLE_PROFILE["description"]}

【核心特征】
{features_text}

【写作要求】
1. 句式：冷静客观，逻辑严密。善用技术隐喻。
2. 词汇：大量使用科技名词（物理、计算机、生物学等），构建高科技氛围。
3. 描写：侧重于物质的物理属性、数据的流动、光影的数字化表现。
4. 视角：宏大的宇宙视角或微观的数据视角。
5. 情感：理性克制，避免滥情，体现科技对人的异化或人对宇宙的渺小感。

【禁忌】
严禁使用玄幻、魔法、武侠、宫廷等非科幻词汇。

【常用语】
{", ".join(cls.STYLE_PROFILE["constraints"]["preferred_words"])}"""

    @classmethod
    def get_style_refinement_prompt(cls, content: str) -> List[Dict[str, str]]:
        """获取风格提炼提示"""
        return [
            {"role": "system", "content": cls.get_system_prompt()},
            {"role": "user", "content": f"""请将以下内容改写成硬科幻/赛博朋克风格：

【原文】
{content}

【改写要求】
1. 保持原意不变，将普通描述转化为科幻视角的描述
2. 加入具体的科技细节和术语
3. 营造冷峻、高科技或废土的氛围
4. 强化理性与逻辑感

请直接输出改写后的内容。"""}
        ]

    @classmethod
    def get_few_shot_messages(cls, user_input: str) -> List[Dict[str, str]]:
        """获取Few-shot示例消息"""
        messages = [{"role": "system", "content": cls.get_system_prompt()}]
        
        # 添加Few-shot示例
        for example in cls.FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": f"请用科幻风格描述：{example['input']}"})
            messages.append({"role": "assistant", "content": example['output']})
        
        # 添加当前请求
        messages.append({"role": "user", "content": f"请用科幻风格描述：{user_input}"})
        
        return messages

    @classmethod
    def get_self_evaluation_prompt(cls, content: str) -> List[Dict[str, str]]:
        """获取自评提示"""
        criteria = "\n".join([f"{i+1}. {k}：{v}" for i, (k, v) in enumerate(cls.STYLE_PROFILE["features"].items())])
        
        return [
            {"role": "system", "content": "你是一位苛刻的科幻小说编辑，专门评估文本的科幻“硬度”和赛博朋克“味道”。"},
            {"role": "user", "content": f"""请对以下内容进行科幻风格评分（0-1分）：

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
- [列出不符合科幻风格的地方，如伪科学、玄幻词汇、过于感性的描写]

改进建议：
- [具体的改进建议]"""}
        ]

    @classmethod
    def get_rewrite_prompt(cls, content: str, evaluation: str) -> List[Dict[str, str]]:
        """获取重写提示"""
        return [
            {"role": "system", "content": cls.get_system_prompt()},
            {"role": "user", "content": f"""请根据评估意见重写以下内容，只改风格不改事实：

【原文】
{content}

【评估意见】
{evaluation}

【重写要求】
1. 保持原意和情节不变
2. 针对评估中指出的问题进行改进（如增加科技细节，去除不当修辞）
3. 更加贴合硬科幻/赛博朋克风格
4. 输出完整重写后的内容"""}
        ]


class SciFiScorer:
    """科幻风格评分器"""
    
    def __init__(self):
        self.style_keywords = {
            "科技": ["量子", "算法", "矩阵", "神经", "接口", "全息", "辐射", "轨道", "聚变", "纳米", "基因", "机械", "数据", "终端", "协议", "加密", "义体", "仿生", "奇点", "熵"],
            "氛围": ["霓虹", "铬", "金属", "废墟", "寂静", "冰冷", "阴影", "电流", "脉冲", "合成", "塑料", "酸雨", "烟雾"],
            "逻辑": ["因此", "导致", "推导", "概率", "变量", "参数", "系统", "逻辑", "分析", "计算"],
            "负面": ["魔力", "灵气", "仙人", "鬼魂", "穿越", "王爷", "奴婢", "微臣"]
        }

    def calculate_score(self, text: str) -> Dict[str, float]:
        """计算文本的科幻风格得分"""
        scores = {}
        
        # 1. 科技密度 (0-1分)
        tech_count = sum(1 for word in self.style_keywords["科技"] if word in text)
        # 假设每100字有3个科技词为满分
        text_len = len(text)
        if text_len > 0:
            density = tech_count / (text_len / 100 + 1)
            scores["科技密度"] = min(density / 3.0, 1.0)
        else:
            scores["科技密度"] = 0.0
        
        # 2. 氛围营造 (0-1分)
        atmosphere_count = sum(1 for word in self.style_keywords["氛围"] if word in text)
        if text_len > 0:
             density = atmosphere_count / (text_len / 100 + 1)
             scores["氛围营造"] = min(density / 2.0, 1.0)
        else:
            scores["氛围营造"] = 0.0

        # 3. 逻辑性 (0-1分)
        logic_count = sum(1 for word in self.style_keywords["逻辑"] if word in text)
        scores["逻辑性"] = min(logic_count / 2, 1.0)
        
        # 4. 违和词汇检测 (扣分项)
        fantasy_count = sum(1 for word in self.style_keywords["负面"] if word in text)
        scores["违和词汇"] = max(0, 1.0 - fantasy_count * 0.5)  # 严厉扣分
        
        # 总分 (加权平均)
        weights = {
            "科技密度": 0.40,
            "氛围营造": 0.30,
            "逻辑性": 0.10,
            "违和词汇": 0.20
        }
        
        total_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights)
        scores["总分"] = round(total_score, 3)
        
        return scores

    def rank_candidates(self, candidates: List[str]) -> List[Tuple[str, float]]:
        """对候选文本进行排序"""
        scored_candidates = []
        for candidate in candidates:
            scores = self.calculate_score(candidate)
            scored_candidates.append((candidate, scores["总分"]))
        
        # 按分数降序排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates


# 全局实例
scifi_engine = SciFiStyleEngine()
scifi_scorer = SciFiScorer()