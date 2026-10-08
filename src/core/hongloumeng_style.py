"""
红楼梦文风生成模块
实现Prompt层风格控制、多候选生成、重排序和自评回写
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import re


class HongloumengStyleEngine:
    """红楼梦文风引擎"""
    
    # 红楼梦风格画像
    STYLE_PROFILE = {
        "name": "红楼梦文风",
        "description": "曹雪芹《红楼梦》的古典白话小说风格",
        "features": {
            "句式": "长短句交错，善用对偶、排比，句子节奏舒缓优雅",
            "词汇": "典雅含蓄，多用诗词典故，人物语言个性化",
            "修辞": "隐喻、象征、暗示丰富，草蛇灰线，伏脉千里",
            "节奏": "张弛有度，细腻描写与情节推进交替",
            "视角": "全知视角与限知视角灵活切换",
            "情感": "含蓄内敛，哀而不伤，乐而不淫"
        },
        "constraints": {
            "sentence_length": (15, 45),  # 平均句长范围
            "poetry_ratio": 0.1,  # 诗词引用比例
            "dialogue_marker": "「」",  # 对话标记
            "avoid_modern": ["手机", "电脑", "汽车", "飞机", "电话", "电视", "网络", "微信", "QQ"],
            "preferred_words": ["且说", "只见", "原来", "当下", "一时", "不觉", "正是", "有诗为证"]
        }
    }
    
    # Few-shot示例
    FEW_SHOT_EXAMPLES = [
        {
            "input": "描述一个女子在花园中赏花",
            "output": "且说黛玉步入园中，只见满园春色，花影扶疏。那一树桃花正开得热闹，粉白相间，映着日光，煞是好看。黛玉驻足凝眸，不觉痴了。正是：\n\n桃花帘外东风软，\n桃花帘内晨妆懒。\n\n她轻叹一声，心下暗想：'这花儿开得这般好，却不知能有几日风光？'"
        },
        {
            "input": "描写两个人在房间里对话",
            "output": "宝玉进了房来，只见宝钗正坐在窗下做针线。见他进来，便放下手中活计，笑道：「宝兄弟来了，快请坐。」宝玉一面坐下，一面笑道：「姐姐好勤快，这早晚还在做活。」宝钗道：「闲着也是闲着，不如找点事做。」二人正说着，只见袭人捧上茶来。"
        },
        {
            "input": "描写一个人物的外貌",
            "output": "只见这人生得肌骨莹润，举止娴雅。唇不点而红，眉不画而翠；脸若银盆，眼如水杏。罕言寡语，人谓藏愚；安分随时，自云守拙。正是：\n\n可叹停机德，\n堪怜咏絮才。\n\n那一种端庄典雅的气度，令人望而生敬。"
        }
    ]
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """获取红楼梦风格的系统提示"""
        features_text = "\n".join([f"  - {k}：{v}" for k, v in cls.STYLE_PROFILE["features"].items()])
        
        return f"""你是曹雪芹《红楼梦》风格的传承者，深谙古典白话小说的精髓。

【风格画像】
{cls.STYLE_PROFILE["description"]}

【核心特征】
{features_text}

【写作要求】
1. 句式：长短句交错，善用对偶、排比，节奏舒缓优雅
2. 词汇：典雅含蓄，多用诗词典故，避免现代词汇
3. 修辞：善用隐喻、象征，草蛇灰线，伏脉千里
4. 节奏：张弛有度，细腻描写与情节推进交替
5. 视角：全知视角与限知视角灵活切换
6. 情感：含蓄内敛，哀而不伤，乐而不淫

【对话标记】
使用「」标记对话，如：宝玉道：「姐姐好。」

【诗词运用】
适当引用或创作诗词，以"正是："或"有诗为证："引出

【禁忌】
严禁使用现代词汇：手机、电脑、汽车、飞机、电话、电视、网络等

【常用语】
且说、只见、原来、当下、一时、不觉、正是、有诗为证"""

    @classmethod
    def get_style_refinement_prompt(cls, content: str) -> List[Dict[str, str]]:
        """获取风格提炼提示"""
        return [
            {"role": "system", "content": cls.get_system_prompt()},
            {"role": "user", "content": f"""请将以下内容改写成红楼梦风格：

【原文】
{content}

【改写要求】
1. 保持原意不变，只改变文风
2. 使用古典白话小说的表达方式
3. 适当加入诗词元素
4. 人物对话使用「」标记
5. 注意含蓄内敛的情感表达

请直接输出改写后的内容。"""}
        ]

    @classmethod
    def get_few_shot_messages(cls, user_input: str) -> List[Dict[str, str]]:
        """获取Few-shot示例消息"""
        messages = [{"role": "system", "content": cls.get_system_prompt()}]
        
        # 添加Few-shot示例
        for example in cls.FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": f"请用红楼梦风格描述：{example['input']}"})
            messages.append({"role": "assistant", "content": example['output']})
        
        # 添加当前请求
        messages.append({"role": "user", "content": f"请用红楼梦风格描述：{user_input}"})
        
        return messages

    @classmethod
    def get_self_evaluation_prompt(cls, content: str) -> List[Dict[str, str]]:
        """获取自评提示"""
        criteria = "\n".join([f"{i+1}. {k}：{v}" for i, (k, v) in enumerate(cls.STYLE_PROFILE["features"].items())])
        
        return [
            {"role": "system", "content": "你是一位严格的文学评论家，专门评估红楼梦风格的还原度。"},
            {"role": "user", "content": f"""请对以下内容进行红楼梦风格评分（0-1分）：

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
- [列出不符合红楼梦风格的地方]

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
2. 针对评估中指出的问题进行改进
3. 更加贴合红楼梦风格
4. 输出完整重写后的内容"""}
        ]


class HongloumengScorer:
    """红楼梦风格评分器"""
    
    def __init__(self):
        self.style_keywords = {
            "古典": ["且说", "只见", "原来", "当下", "一时", "不觉", "正是", "有诗为证", "却道", "话说"],
            "诗词": ["诗", "词", "赋", "曲", "对联", "匾额", "题", "吟", "咏", "诵"],
            "情感": ["叹", "怜", "惜", "悲", "喜", "愁", "闷", "痴", "醉", "醒"],
            "描写": ["只见", "但见", "遥见", "细看", "端详", "打量", "观", "望", "视", "瞧"]
        }
        
    def calculate_score(self, text: str) -> Dict[str, float]:
        """计算文本的红楼梦风格得分"""
        scores = {}
        
        # 1. 句长特征 (0-1分)
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_length = np.mean([len(s) for s in sentences])
            # 理想句长20-30字
            if 15 <= avg_length <= 45:
                scores["句长"] = 1.0 - abs(avg_length - 30) / 30
            else:
                scores["句长"] = 0.3
        else:
            scores["句长"] = 0.0
        
        # 2. 古典词汇密度 (0-1分)
        classical_count = sum(1 for word in self.style_keywords["古典"] if word in text)
        scores["古典词汇"] = min(classical_count / 3, 1.0)  # 至少3个古典词汇得满分
        
        # 3. 诗词元素 (0-1分)
        poetry_count = sum(1 for word in self.style_keywords["诗词"] if word in text)
        has_poetry = "正是：" in text or "有诗为证" in text or "诗云" in text
        scores["诗词元素"] = 0.5 if has_poetry else min(poetry_count / 2, 0.5)
        
        # 4. 对话格式 (0-1分)
        traditional_quotes = text.count("「") + text.count("」")
        modern_quotes = text.count("'") + text.count('"')
        if traditional_quotes > 0:
            scores["对话格式"] = min(traditional_quotes / 4, 1.0)
        elif modern_quotes > 0:
            scores["对话格式"] = 0.3  # 有对话但格式不对
        else:
            scores["对话格式"] = 0.5  # 没有对话
        
        # 5. 情感表达 (0-1分)
        emotion_count = sum(1 for word in self.style_keywords["情感"] if word in text)
        scores["情感表达"] = min(emotion_count / 3, 1.0)
        
        # 6. 现代词汇检测 (扣分项)
        modern_words = ["手机", "电脑", "汽车", "飞机", "电话", "电视", "网络", "微信", "QQ", "视频", "照片"]
        modern_count = sum(1 for word in modern_words if word in text)
        scores["现代词汇"] = max(0, 1.0 - modern_count * 0.3)  # 每个现代词扣0.3分
        
        # 总分 (加权平均)
        weights = {
            "句长": 0.15,
            "古典词汇": 0.20,
            "诗词元素": 0.20,
            "对话格式": 0.15,
            "情感表达": 0.15,
            "现代词汇": 0.15
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
hongloumeng_engine = HongloumengStyleEngine()
hongloumeng_scorer = HongloumengScorer()
