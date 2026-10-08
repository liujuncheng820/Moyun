"""
中文VibeWriting - 服务分离架构
将StoryAgent的职责拆分到独立的服务类中，实现单一职责原则
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class StoryContext:
    """故事生成上下文，用于在不同服务间传递信息"""
    topic: str
    book_spec: Optional[str] = None
    character_profiles: Optional[str] = None
    text_plan: Optional[str] = None
    enhanced_plan: Optional[str] = None
    style_guide: Optional[str] = None
    novel_content: Optional[str] = None
    optimized_content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""
        return {
            'topic': self.topic,
            'book_spec': self.book_spec,
            'character_profiles': self.character_profiles,
            'text_plan': self.text_plan,
            'enhanced_plan': self.enhanced_plan,
            'style_guide': self.style_guide,
            'novel_content': self.novel_content,
            'optimized_content': self.optimized_content
        }


class APIClient:
    """统一的API客户端，负责所有API调用"""
    
    def __init__(self, backend_uri: str, backend: str = "deepseek", 
                 request_timeout: int = 120, max_tokens: int = 4096):
        self.backend_uri = backend_uri
        self.backend = backend
        self.request_timeout = request_timeout
        self.max_tokens = max_tokens
    
    def call_api(self, messages: List[Dict[str, str]], retries: int = 3) -> Optional[str]:
        """统一的API调用接口"""
        # 这里会调用原有的query_chat逻辑
        # 为了简化，暂时返回None，实际实现时会调用相应的后端
        return None
    
    def batch_call_api(self, batch_requests: List[Dict[str, Any]]) -> List[Optional[str]]:
        """批量API调用，支持并行处理"""
        results = []
        for request in batch_requests:
            result = self.call_api(request['messages'], request.get('retries', 3))
            results.append(result)
        return results


class PromptService:
    """提示词服务，负责构建各种提示词"""
    
    @staticmethod
    def build_character_design_prompt(book_spec: str) -> List[Dict[str, str]]:
        """构建角色设计提示词"""
        return [
            {"role": "system", "content": "你是一位专业的角色设计师，擅长创造立体、有血有肉的文学角色。"},
            {"role": "user", "content": f"""基于以下书籍规格，请设计详细的角色档案：

【书籍规格】
{book_spec}

请为每个主要角色创建详细档案，包括：
1. 基本信息：姓名、年龄、职业、外貌特征
2. 性格特质：核心性格、优缺点、行为习惯
3. 背景故事：成长经历、重要事件、人际关系
4. 内心世界：价值观、恐惧、渴望、秘密
5. 语言特色：说话方式、口头禅、表达习惯
6. 发展弧线：在故事中的成长变化轨迹
7. 冲突设置：与其他角色的矛盾点

请确保角色设计符合中文读者的审美和价值观。"""}
        ]
    
    @staticmethod
    def build_structure_optimization_prompt(character_profiles: str, text_plan: str) -> List[Dict[str, str]]:
        """构建结构优化提示词"""
        return [
            {"role": "system", "content": "你是一位专业的中文小说结构师，擅长优化故事结构和节奏。"},
            {"role": "user", "content": f"""请优化以下章节计划的结构，结合角色设计，确保：
1. 情节发展有张有弛，节奏合理
2. 章节之间有逻辑连贯性
3. 每章都有明确的冲突和转折
4. 适合中文读者的阅读习惯
5. 角色发展与情节推进相互呼应

【角色档案】
{character_profiles}

【原始章节计划】
{text_plan}

请返回优化后的详细章节大纲，包含每章的核心冲突、情感走向和关键情节点。"""}
        ]
    
    @staticmethod
    def build_style_guide_prompt(book_spec: str, character_profiles: str, enhanced_plan: str) -> List[Dict[str, str]]:
        """构建风格指导提示词"""
        return [
            {"role": "system", "content": "你是一位文学风格顾问，精通各种文学流派和写作技巧。"},
            {"role": "user", "content": f"""基于以下信息，请为这部作品确定最适合的文学风格：

【书籍规格】
{book_spec}

【角色档案】
{character_profiles}

【章节大纲】
{enhanced_plan}

请确定：
1. 叙述视角：第一人称/第三人称/多视角
2. 语言风格：现代/古典/诗意/朴实/幽默等
3. 描写重点：心理描写/环境描写/动作描写的比重
4. 对话风格：正式/口语化/地方特色
5. 节奏控制：快节奏/慢节奏/变化节奏
6. 情感基调：温暖/深沉/轻松/悲伤/励志等

请提供详细的风格指导方案。"""}
        ]
    
    @staticmethod
    def build_batch_creative_prompt(context: StoryContext) -> List[Dict[str, str]]:
        """构建批量创作提示词，将多个步骤合并"""
        return [
            {"role": "system", "content": """你是一位资深的中文小说作家和编辑，具有以下能力：
1. 角色设计：创造立体鲜明的文学角色
2. 结构优化：优化故事结构和节奏
3. 风格定调：确定最适合的文学风格
4. 内容创作：生成高质量的小说内容
5. 质量优化：润色和完善文学作品"""},
            {"role": "user", "content": f"""请基于以下书籍规格和章节计划，完成以下任务：

【书籍规格】
{context.book_spec}

【章节计划】
{context.text_plan}

请按以下格式返回结果：

=== 角色档案 ===
[详细的角色设计]

=== 优化章节大纲 ===
[优化后的章节结构]

=== 文学风格指导 ===
[风格定调方案]

=== 完整小说内容 ===
[高质量的小说正文]

请确保每个部分都精心设计，符合中文读者的审美和价值观。"""}
        ]


class StoryGenerationService:
    """故事生成服务，负责协调整个生成流程"""
    
    def __init__(self, api_client: APIClient, prompt_service: PromptService):
        self.api_client = api_client
        self.prompt_service = prompt_service
    
    def generate_story_batch(self, context: StoryContext) -> StoryContext:
        """批量生成故事，减少API调用次数"""
        print("🔄 使用批量处理模式生成故事...")
        
        # 构建批量创作提示词
        batch_prompt = self.prompt_service.build_batch_creative_prompt(context)
        
        # 单次API调用完成多个任务
        result = self.api_client.call_api(batch_prompt)
        
        if result:
            # 解析批量结果
            parsed_result = self._parse_batch_result(result)
            context.character_profiles = parsed_result.get('character_profiles')
            context.enhanced_plan = parsed_result.get('enhanced_plan')
            context.style_guide = parsed_result.get('style_guide')
            context.novel_content = parsed_result.get('novel_content')
            
            print("✅ 批量生成完成")
        else:
            print("❌ 批量生成失败，回退到分步处理")
            context = self._generate_story_step_by_step(context)
        
        return context
    
    def _parse_batch_result(self, result: str) -> Dict[str, str]:
        """解析批量结果"""
        parsed = {}
        
        # 使用正则表达式或字符串分割来解析结果
        sections = {
            'character_profiles': '=== 角色档案 ===',
            'enhanced_plan': '=== 优化章节大纲 ===',
            'style_guide': '=== 文学风格指导 ===',
            'novel_content': '=== 完整小说内容 ==='
        }
        
        current_section = None
        current_content = []
        
        for line in result.split('\n'):
            line = line.strip()
            
            # 检查是否是新的章节标题
            section_found = False
            for key, marker in sections.items():
                if marker in line:
                    # 保存前一个章节的内容
                    if current_section and current_content:
                        parsed[current_section] = '\n'.join(current_content).strip()
                    
                    current_section = key
                    current_content = []
                    section_found = True
                    break
            
            if not section_found and current_section:
                current_content.append(line)
        
        # 保存最后一个章节的内容
        if current_section and current_content:
            parsed[current_section] = '\n'.join(current_content).strip()
        
        return parsed
    
    def _generate_story_step_by_step(self, context: StoryContext) -> StoryContext:
        """分步生成故事（回退方案）"""
        print("🔄 使用分步处理模式...")
        
        # 步骤1: 角色设计
        if not context.character_profiles:
            character_prompt = self.prompt_service.build_character_design_prompt(context.book_spec)
            context.character_profiles = self.api_client.call_api(character_prompt)
        
        # 步骤2: 结构优化
        if not context.enhanced_plan and context.character_profiles:
            structure_prompt = self.prompt_service.build_structure_optimization_prompt(
                context.character_profiles, context.text_plan)
            context.enhanced_plan = self.api_client.call_api(structure_prompt)
        
        # 步骤3: 风格定调
        if not context.style_guide and context.enhanced_plan:
            style_prompt = self.prompt_service.build_style_guide_prompt(
                context.book_spec, context.character_profiles, context.enhanced_plan)
            context.style_guide = self.api_client.call_api(style_prompt)
        
        return context


class ContextManager:
    """上下文管理器，负责上下文的复用和传递"""
    
    def __init__(self):
        self._context_cache = {}
    
    def save_context(self, key: str, context: StoryContext):
        """保存上下文到缓存"""
        self._context_cache[key] = context
    
    def load_context(self, key: str) -> Optional[StoryContext]:
        """从缓存加载上下文"""
        return self._context_cache.get(key)
    
    def clear_context(self, key: str):
        """清除指定的上下文缓存"""
        if key in self._context_cache:
            del self._context_cache[key]
    
    def get_context_summary(self, context: StoryContext) -> str:
        """获取上下文摘要，用于减少重复传递"""
        summary_parts = []
        
        if context.book_spec:
            summary_parts.append(f"书籍规格: {context.book_spec[:100]}...")
        
        if context.character_profiles:
            summary_parts.append(f"角色档案: {context.character_profiles[:100]}...")
        
        if context.enhanced_plan:
            summary_parts.append(f"章节大纲: {context.enhanced_plan[:100]}...")
        
        return "\n".join(summary_parts)