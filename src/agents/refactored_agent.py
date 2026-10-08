"""
重构后的StoryAgent - 实现单一职责原则和批量处理
"""

import os
import json
from typing import Dict, List, Optional, Any
from ..services.services import (
    StoryContext, APIClient, PromptService, 
    StoryGenerationService, ContextManager
)
from ..core.prompts import (
    init_book_spec_messages, enhance_book_spec_messages,
    create_plot_chapters_messages,
    split_chapters_into_scenes_messages
)


class ConfigManager:
    """配置管理器，负责管理所有配置信息"""
    
    def __init__(self):
        self.backend_uri = os.getenv("BACKEND_URI", "http://localhost:8000/generate")
        self.backend = os.getenv("BACKEND", "deepseek")
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "120"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
        self.api_key = os.getenv("API_KEY")
        
        # 验证必要的配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置的有效性"""
        if not self.backend_uri:
            raise ValueError("BACKEND_URI 环境变量未设置")
        
        if self.backend == "openai" and not self.api_key:
            raise ValueError("使用OpenAI后端时必须设置API_KEY环境变量")
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return {
            'backend_uri': self.backend_uri,
            'backend': self.backend,
            'request_timeout': self.request_timeout,
            'max_tokens': self.max_tokens,
            'api_key': self.api_key
        }


class StoryGenerationError(Exception):
    """故事生成异常基类"""
    pass


class APIError(StoryGenerationError):
    """API调用异常"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(StoryGenerationError):
    """验证异常"""
    pass


class RefactoredStoryAgent:
    """重构后的故事代理，遵循单一职责原则"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化故事代理"""
        self.config_manager = config_manager or ConfigManager()
        
        # 初始化各个服务组件
        api_config = self.config_manager.get_api_config()
        self.api_client = APIClient(
            backend_uri=api_config['backend_uri'],
            backend=api_config['backend'],
            request_timeout=api_config['request_timeout'],
            max_tokens=api_config['max_tokens']
        )
        
        self.prompt_service = PromptService()
        self.story_service = StoryGenerationService(self.api_client, self.prompt_service)
        self.context_manager = ContextManager()
    
    def generate_story(self, topic: str, use_batch_processing: bool = True) -> Dict[str, Any]:
        """
        生成故事的主入口
        
        Args:
            topic: 故事主题
            use_batch_processing: 是否使用批量处理模式
            
        Returns:
            包含生成结果的字典
        """
        try:
            print(f"🚀 开始生成故事: {topic}")
            print(f"📊 处理模式: {'批量处理' if use_batch_processing else '分步处理'}")
            
            # 创建故事上下文
            context = StoryContext(topic=topic)
            
            # 第一阶段：基础规格生成
            context = self._generate_basic_specs(context)
            
            # 第二阶段：故事生成（支持批量处理）
            if use_batch_processing:
                context = self.story_service.generate_story_batch(context)
            else:
                context = self.story_service._generate_story_step_by_step(context)
            
            # 第三阶段：最终优化
            context = self._optimize_final_content(context)
            
            # 保存上下文以供后续使用
            self.context_manager.save_context(f"story_{topic}", context)
            
            print("✅ 故事生成完成！")
            return self._format_output(context)
            
        except Exception as e:
            print(f"❌ 故事生成失败: {str(e)}")
            raise StoryGenerationError(f"故事生成失败: {str(e)}") from e
    
    def _generate_basic_specs(self, context: StoryContext) -> StoryContext:
        """生成基础规格（书籍规格、章节计划）"""
        print("📝 第一阶段：生成基础规格...")
        
        # 步骤1: 初始化书籍规格
        init_messages = init_book_spec_messages(context.topic)
        context.book_spec = self.api_client.call_api(init_messages)
        
        if not context.book_spec:
            raise APIError("初始化书籍规格失败")
        
        # 步骤2: 增强书籍规格
        enhance_messages = enhance_book_spec_messages(context.book_spec)
        enhanced_spec = self.api_client.call_api(enhance_messages)
        
        if enhanced_spec:
            context.book_spec = enhanced_spec
        
        # 步骤3: 完善书籍规格
        complete_messages = complete_book_spec_messages(context.book_spec)
        completed_spec = self.api_client.call_api(complete_messages)
        
        if completed_spec:
            context.book_spec = completed_spec
        
        # 步骤4: 创建章节计划
        plot_messages = create_plot_chapters_messages(context.book_spec)
        context.text_plan = self.api_client.call_api(plot_messages)
        
        if not context.text_plan:
            raise APIError("创建章节计划失败")
        
        print("✅ 基础规格生成完成")
        return context
    
    def _optimize_final_content(self, context: StoryContext) -> StoryContext:
        """最终内容优化"""
        print("🎨 第三阶段：最终内容优化...")
        
        if context.novel_content:
            # 构建优化提示词
            optimize_messages = [
                {"role": "system", "content": "你是一位专业的文学编辑，擅长润色和优化中文小说。"},
                {"role": "user", "content": f"""请对以下小说内容进行最终优化：

【原始内容】
{context.novel_content}

请从以下方面进行优化：
1. 语言表达：使语言更加流畅自然
2. 情感渲染：增强情感表达的感染力
3. 细节描写：丰富环境和人物细节
4. 节奏控制：优化叙述节奏
5. 逻辑连贯：确保情节逻辑清晰
6. 文学性：提升整体文学品质

请返回优化后的完整内容。"""}
            ]
            
            optimized_content = self.api_client.call_api(optimize_messages)
            if optimized_content:
                context.optimized_content = optimized_content
                print("✅ 内容优化完成")
            else:
                print("⚠️ 内容优化失败，使用原始内容")
                context.optimized_content = context.novel_content
        
        return context
    
    def _format_output(self, context: StoryContext) -> Dict[str, Any]:
        """格式化输出结果"""
        return {
            'topic': context.topic,
            'book_spec': context.book_spec,
            'character_profiles': context.character_profiles,
            'text_plan': context.text_plan,
            'enhanced_plan': context.enhanced_plan,
            'style_guide': context.style_guide,
            'novel_content': context.optimized_content or context.novel_content,
            'generation_metadata': {
                'has_character_profiles': bool(context.character_profiles),
                'has_enhanced_plan': bool(context.enhanced_plan),
                'has_style_guide': bool(context.style_guide),
                'content_optimized': bool(context.optimized_content)
            }
        }
    
    def get_generation_progress(self, topic: str) -> Optional[Dict[str, Any]]:
        """获取生成进度"""
        context = self.context_manager.load_context(f"story_{topic}")
        if not context:
            return None
        
        progress = {
            'topic': context.topic,
            'steps_completed': [],
            'current_step': None,
            'progress_percentage': 0
        }
        
        steps = [
            ('book_spec', '书籍规格'),
            ('text_plan', '章节计划'),
            ('character_profiles', '角色档案'),
            ('enhanced_plan', '优化大纲'),
            ('style_guide', '风格指导'),
            ('novel_content', '小说内容'),
            ('optimized_content', '内容优化')
        ]
        
        completed_steps = 0
        for attr, name in steps:
            if getattr(context, attr):
                progress['steps_completed'].append(name)
                completed_steps += 1
            else:
                if not progress['current_step']:
                    progress['current_step'] = name
                break
        
        progress['progress_percentage'] = (completed_steps / len(steps)) * 100
        return progress
    
    def resume_generation(self, topic: str) -> Dict[str, Any]:
        """恢复中断的生成任务"""
        context = self.context_manager.load_context(f"story_{topic}")
        if not context:
            raise ValidationError(f"未找到主题为 '{topic}' 的生成任务")
        
        print(f"🔄 恢复生成任务: {topic}")
        
        # 根据当前进度继续生成
        if not context.novel_content:
            context = self.story_service.generate_story_batch(context)
        
        if not context.optimized_content:
            context = self._optimize_final_content(context)
        
        return self._format_output(context)


# 兼容性包装器，保持与原有代码的兼容性
class StoryAgent:
    """兼容性包装器，保持与原有代码的兼容性"""
    
    def __init__(self, backend_uri: str = None, backend: str = "deepseek", 
                 request_timeout: int = 120, max_tokens: int = 4096):
        # 设置环境变量以保持兼容性
        if backend_uri:
            os.environ["BACKEND_URI"] = backend_uri
        if backend:
            os.environ["BACKEND"] = backend
        os.environ["REQUEST_TIMEOUT"] = str(request_timeout)
        os.environ["MAX_TOKENS"] = str(max_tokens)
        
        # 创建重构后的代理
        self._agent = RefactoredStoryAgent()
    
    def generate_story(self, topic: str) -> str:
        """保持与原有接口的兼容性"""
        try:
            result = self._agent.generate_story(topic, use_batch_processing=True)
            return result.get('novel_content', '')
        except Exception as e:
            print(f"生成失败，尝试分步处理: {str(e)}")
            result = self._agent.generate_story(topic, use_batch_processing=False)
            return result.get('novel_content', '')