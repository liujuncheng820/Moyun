"""
中文VibeWriting - 基于DeepSeek Reasoner的智能小说生成器

核心模块包，包含所有主要功能组件。
"""

__version__ = "1.0.0"
__author__ = "GOAT.AI"
__description__ = "基于DeepSeek Reasoner的中文小说生成器"

# 导入核心组件
from .agents.storytelling_agent import StoryAgent
from .agents.refactored_agent import RefactoredStoryAgent
from .services.services import StoryGenerationService
from .core.plan import Plan
from .core.prompts import *

__all__ = [
    'StoryAgent',
    'RefactoredStoryAgent', 
    'StoryGenerationService',
    'Plan'
]