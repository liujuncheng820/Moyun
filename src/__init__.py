"""
Moyun - A multi-stage framework for long-form Chinese story generation.

Core package containing all principal components.
"""

__version__ = "1.0.0"
__author__ = "Moyun"
__description__ = "Multi-stage Chinese story generation framework"

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