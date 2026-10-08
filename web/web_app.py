#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
中文VibeWriting - 基于DeepSeek Reasoner的交互式智能小说生成器
Web应用主程序

采用DeepSeek Reasoner作为核心AI引擎，提供专业级的中文小说创作能力
基于 Flask + Socket.IO 实现实时交互界面，支持步骤级用户控制
"""

import os
import sys
import threading
import time
import json
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import logging
from dotenv import load_dotenv
import markdown

# 加载 .env 文件
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
print(f"🔄 正在加载 .env 文件: {dotenv_path}")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print("✅ .env 文件加载成功")
    print(f"   QWEN_API_KEY: {'*' * 8 + os.environ.get('QWEN_API_KEY', '')[-4:] if os.environ.get('QWEN_API_KEY') else '未设置'}")
    print(f"   VOLCANO_API_KEY: {'*' * 8 + os.environ.get('VOLCANO_API_KEY', '')[-4:] if os.environ.get('VOLCANO_API_KEY') else '未设置'}")
    print(f"   DEEPSEEK_API_KEY: {'*' * 8 + os.environ.get('DEEPSEEK_API_KEY', '')[-4:] if os.environ.get('DEEPSEEK_API_KEY') else '未设置'}")
    print(f"   OPENAI_API_KEY: {'*' * 8 + os.environ.get('OPENAI_API_KEY', '')[-4:] if os.environ.get('OPENAI_API_KEY') else '未设置'}")
else:
    print("⚠️ .env 文件不存在")
    load_dotenv()  # 尝试加载默认位置

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.storytelling_agent import StoryAgent
from src.agents.hongloumeng_generator import HongloumengGenerator, get_hongloumeng_generator
from src.agents.scifi_generator import SciFiGenerator, get_scifi_generator
from src.agents.style_generator import get_style_generator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 创建 SocketIO 实例
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 全局变量
story_agent = None
hongloumeng_generator = None  # 红楼梦文风生成器
scifi_generator = None        # 科幻文风生成器
romance_generator = None      # 言情文风生成器
mystery_generator = None      # 悬疑文风生成器
generation_threads = {}
user_sessions = {}  # 存储用户会话状态

# 故事生成步骤定义
STORY_STEPS = [
    {
        'id': 'init_book_spec',
        'name': '书籍规格初始化',
        'description': '根据您的需求初始化小说的基本规格和框架',
        'method': 'init_book_spec',
        'prompt_template': '基于主题"{topic}"，请初始化小说的基本规格：\n1. 故事类型和体裁\n2. 目标字数和章节数\n3. 主要受众群体\n4. 整体风格定位\n请提供详细的规格设计。'
    },
    {
        'id': 'enhance_book_spec',
        'name': '书籍规格增强',
        'description': '深化和完善小说的整体设定和背景',
        'method': 'enhance_book_spec',
        'prompt_template': '基于初始规格，请深化小说设定：\n1. 故事背景的详细设定\n2. 核心主题的深入阐述\n3. 独特元素和创新点\n4. 整体架构的完善\n请提供增强后的规格。'
    },
    {
        'id': 'character_design',
        'name': '角色深度设计',
        'description': '创建丰富立体的角色形象和人物关系',
        'method': 'character_design',
        'prompt_template': '基于小说规格，请设计主要角色：\n1. 主角的性格特点和背景\n2. 重要配角的设定\n3. 角色间的关系网络\n4. 角色的成长轨迹\n请创建立体的角色形象。'
    },
    {
        'id': 'create_plot_chapters',
        'name': '章节计划创建',
        'description': '构建完整的故事大纲和章节结构',
        'method': 'create_plot_chapters',
        'prompt_template': '基于角色设计，请创建章节计划：\n1. 故事的起承转合结构\n2. 各章节的主要情节\n3. 冲突和转折点安排\n4. 高潮和结局设计\n请提供详细的章节大纲。'
    },
    {
        'id': 'optimize_chapter_plan',
        'name': '章节计划优化',
        'description': '优化和调整章节安排，确保故事节奏',
        'method': 'optimize_chapter_plan',
        'prompt_template': '请优化章节计划：\n1. 调整章节间的逻辑关系\n2. 优化故事节奏和张力\n3. 完善悬念和伏笔\n4. 确保情节的连贯性\n请提供优化后的章节安排。'
    },
    {
        'id': 'set_literary_style',
        'name': '文学风格定调',
        'description': '确定小说的写作风格和叙述方式',
        'method': 'set_literary_style',
        'prompt_template': '请确定小说的文学风格：\n1. 叙述视角和语调\n2. 文字风格和表达方式\n3. 对话风格特点\n4. 描写技巧和手法\n请提供风格指导方案。'
    },
    {
        'id': 'generate_novel',
        'name': '高质量内容生成',
        'description': '生成精彩的小说内容和场景描写',
        'method': 'generate_novel',
        'prompt_template': '基于所有前期设定，请开始撰写小说内容：\n1. 精彩的开篇场景\n2. 主要情节的展开\n3. 角色互动和对话\n4. 环境氛围的营造\n请撰写高质量的小说内容。'
    },
    {
        'id': 'optimize_content',
        'name': '内容质量优化',
        'description': '最终优化和润色，提升内容质量',
        'method': 'optimize_content',
        'prompt_template': '请对小说内容进行最终优化：\n1. 语言表达的精炼\n2. 情节逻辑的完善\n3. 角色形象的深化\n4. 整体质量的提升\n请提供最终优化版本。'
    }
]

def resolve_llm_endpoint_and_model(backend, model):
    backend = (backend or os.getenv("DEFAULT_LLM_BACKEND", "deepseek")).lower()
    if backend == "deepseek":
        endpoint = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    elif backend == "qwen":
        endpoint = os.getenv(
            "QWEN_API_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        default_model = os.getenv("QWEN_MODEL", "qwen-plus")
    elif backend == "volcano":
        endpoint = os.getenv(
            "VOLCANO_API_URL",
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        )
        # Volcano 通常需要具体的 Endpoint ID，这里设一个占位符或默认值
        default_model = os.getenv("VOLCANO_MODEL", "ep-20240604123456-abcde")
    elif backend == "openai":
        endpoint = os.getenv(
            "OPENAI_API_URL",
            "https://api.openai.com/v1/chat/completions",
        )
        default_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    else:
        backend = "deepseek"
        endpoint = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

    resolved_model = model or default_model
    return backend, endpoint, resolved_model

def create_story_agent(backend, model):
    backend, endpoint, resolved_model = resolve_llm_endpoint_and_model(backend, model)
    return StoryAgent(
        backend_uri=endpoint,
        backend=backend,
        form="novel",
        max_tokens=2048,
        request_timeout=300,
        extra_options={"model": resolved_model},
    )

def get_session_story_agent(session):
    return getattr(session, "story_agent", None) or story_agent

class UserSession:
    """用户会话管理类"""
    def __init__(self, session_id):
        self.session_id = session_id
        self.current_step_index = 0
        self.step_results = {}
        self.topic = ""
        self.is_active = False
        self.is_generating = False
        self.should_pause = False
        self.hongloumeng_enabled = False  # 红楼梦文风开关
        self.scifi_enabled = False        # 科幻文风开关
        self.romance_enabled = False      # 言情文风开关
        self.mystery_enabled = False      # 悬疑文风开关
        self.llm_backend = os.getenv("DEFAULT_LLM_BACKEND", "deepseek").lower()
        self.llm_model = os.getenv("DEFAULT_LLM_MODEL")
        self.story_agent = None
        
    def reset(self):
        """重置会话状态"""
        self.current_step_index = 0
        self.step_results = {}
        self.topic = ""
        self.is_active = False
        self.is_generating = False
        self.should_pause = False
        self.hongloumeng_enabled = False
        self.scifi_enabled = False
        self.romance_enabled = False
        self.mystery_enabled = False
    
    def get_current_step(self):
        """获取当前步骤"""
        if self.current_step_index < len(STORY_STEPS):
            return STORY_STEPS[self.current_step_index]
        return None
    
    def advance_step(self):
        """前进到下一步"""
        self.current_step_index += 1
    
    def is_complete(self):
        """检查是否完成所有步骤"""
        return self.current_step_index >= len(STORY_STEPS)
    
    def get_context_for_step(self, step_id):
        """为指定步骤获取上下文"""
        context_parts = []
        
        # 添加主题
        if self.topic:
            context_parts.append(f"故事主题：{self.topic}")
        
        # 添加之前步骤的结果
        for step in STORY_STEPS:
            if step['id'] == step_id:
                break
            if step['id'] in self.step_results:
                result = self.step_results[step['id']]
                # 确保result是字符串类型
                if isinstance(result, list) and len(result) > 0:
                    result = result[0]
                elif isinstance(result, list):
                    result = "生成内容为空"
                if not result.startswith("已跳过步骤"):
                    context_parts.append(f"{step['name']}：{result}")
        
        return "\n\n".join(context_parts) if context_parts else ""

def initialize_story_agent():
    """初始化故事生成器"""
    global story_agent, hongloumeng_generator, scifi_generator, romance_generator, mystery_generator
    
    try:
        story_agent = create_story_agent(
            os.getenv("DEFAULT_LLM_BACKEND", "deepseek"),
            os.getenv("DEFAULT_LLM_MODEL"),
        )
        
        # 初始化红楼梦文风生成器
        try:
            hongloumeng_generator = get_hongloumeng_generator()
            logger.info("✅ 红楼梦文风生成器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 红楼梦文风生成器初始化失败: {e}")
            hongloumeng_generator = None
            
        # 初始化科幻文风生成器
        try:
            scifi_generator = get_scifi_generator()
            logger.info("✅ 科幻文风生成器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 科幻文风生成器初始化失败: {e}")
            scifi_generator = None
            
        # 初始化言情文风生成器
        try:
            romance_generator = get_style_generator("romance")
            logger.info("✅ 言情文风生成器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 言情文风生成器初始化失败: {e}")
            romance_generator = None

        # 初始化悬疑文风生成器
        try:
            mystery_generator = get_style_generator("mystery")
            logger.info("✅ 悬疑文风生成器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 悬疑文风生成器初始化失败: {e}")
            mystery_generator = None
        
        logger.info("✅ 中文VibeWriting引擎初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 引擎初始化失败: {e}")
        return False

# Flask 路由

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

# Socket.IO 事件处理器

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    user_sessions[session_id] = UserSession(session_id)
    print(f'用户 {session_id} 已连接')

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in user_sessions:
        del user_sessions[session_id]
    print(f'用户 {session_id} 已断开连接')

@socketio.on('hongloumeng_toggle')
def handle_hongloumeng_toggle(data):
    """处理红楼梦文风开关"""
    session_id = request.sid
    enabled = data.get('enabled', False)
    
    if session_id in user_sessions:
        user_sessions[session_id].hongloumeng_enabled = enabled
        status = "开启" if enabled else "关闭"
        # 互斥处理
        if enabled:
            user_sessions[session_id].scifi_enabled = False
            user_sessions[session_id].romance_enabled = False
            user_sessions[session_id].mystery_enabled = False
            
        print(f'用户 {session_id} {status}了红楼梦文风模式')
        emit('message', {'type': 'info', 'content': f'红楼梦文风模式已{status}'})

@socketio.on('scifi_toggle')
def handle_scifi_toggle(data):
    """处理科幻文风开关"""
    session_id = request.sid
    enabled = data.get('enabled', False)
    
    if session_id in user_sessions:
        user_sessions[session_id].scifi_enabled = enabled
        status = "开启" if enabled else "关闭"
        # 互斥处理
        if enabled:
            user_sessions[session_id].hongloumeng_enabled = False
            user_sessions[session_id].romance_enabled = False
            user_sessions[session_id].mystery_enabled = False
            
        print(f'用户 {session_id} {status}了科幻文风模式')
        emit('message', {'type': 'info', 'content': f'科幻文风模式已{status}'})

@socketio.on('romance_toggle')
def handle_romance_toggle(data):
    """处理言情文风开关"""
    session_id = request.sid
    enabled = data.get('enabled', False)
    
    if session_id in user_sessions:
        user_sessions[session_id].romance_enabled = enabled
        status = "开启" if enabled else "关闭"
        # 互斥处理
        if enabled:
            user_sessions[session_id].hongloumeng_enabled = False
            user_sessions[session_id].scifi_enabled = False
            user_sessions[session_id].mystery_enabled = False
            
        print(f'用户 {session_id} {status}了言情文风模式')
        emit('message', {'type': 'info', 'content': f'言情文风模式已{status}'})

@socketio.on('mystery_toggle')
def handle_mystery_toggle(data):
    """处理悬疑文风开关"""
    session_id = request.sid
    enabled = data.get('enabled', False)
    
    if session_id in user_sessions:
        user_sessions[session_id].mystery_enabled = enabled
        status = "开启" if enabled else "关闭"
        # 互斥处理
        if enabled:
            user_sessions[session_id].hongloumeng_enabled = False
            user_sessions[session_id].scifi_enabled = False
            user_sessions[session_id].romance_enabled = False
            
        print(f'用户 {session_id} {status}了悬疑文风模式')
        emit('message', {'type': 'info', 'content': f'悬疑文风模式已{status}'})

@socketio.on('set_llm')
def handle_set_llm(data):
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return

    session = user_sessions[session_id]
    backend = (data.get('llm_backend') or session.llm_backend or "deepseek").lower()
    model = data.get('llm_model') or session.llm_model
    session.llm_backend = backend
    session.llm_model = model
    session.story_agent = create_story_agent(session.llm_backend, session.llm_model)
    
    # 检查 Key 是否配置
    if backend == 'qwen':
        key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not key:
            emit('message', {'type': 'warning', 'content': '⚠️ 未检测到 QWEN_API_KEY，请检查环境变量设置'})
            print("⚠️ [Qwen] 未检测到 API Key")
    elif backend == 'volcano':
        key = os.getenv("VOLCANO_API_KEY")
        if not key:
            emit('message', {'type': 'warning', 'content': '⚠️ 未检测到 VOLCANO_API_KEY，请检查环境变量设置'})
            print("⚠️ [Volcano] 未检测到 API Key")
    elif backend == 'openai':
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            emit('message', {'type': 'warning', 'content': '⚠️ 未检测到 OPENAI_API_KEY，请检查环境变量设置'})
            print("⚠️ [OpenAI] 未检测到 API Key")
    elif backend == 'deepseek':
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            emit('message', {'type': 'warning', 'content': '⚠️ 未检测到 DEEPSEEK_API_KEY，请检查环境变量设置'})
            print("⚠️ [DeepSeek] 未检测到 API Key")

    emit('message', {'type': 'info', 'content': f'已切换模型：{session.llm_backend} / {session.llm_model}'})

@socketio.on('start_story_generation')
def handle_start_story_generation(data):
    session_id = request.sid
    print(f"🔄 收到故事生成请求: {data}")  # 添加调试日志
    
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    session.topic = data.get('topic', '')
    session.llm_backend = (data.get('llm_backend') or session.llm_backend or "deepseek").lower()
    session.llm_model = data.get('llm_model') or session.llm_model
    session.story_agent = create_story_agent(session.llm_backend, session.llm_model)
    session.is_active = True
    session.current_step_index = 0
    session.step_results = {}
    
    # 检查 Key 是否配置
    if session.llm_backend == 'qwen':
        key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not key:
            print("❌ [Qwen] 启动生成失败：未检测到 API Key")
            emit('error_message', {'error': '未配置 Qwen API Key，请设置环境变量 QWEN_API_KEY'})
            return
    elif session.llm_backend == 'volcano':
        key = os.getenv("VOLCANO_API_KEY")
        if not key:
            print("❌ [Volcano] 启动生成失败：未检测到 API Key")
            emit('error_message', {'error': '未配置 Volcano API Key，请设置环境变量 VOLCANO_API_KEY'})
            return
    elif session.llm_backend == 'openai':
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            print("❌ [OpenAI] 启动生成失败：未检测到 API Key")
            emit('error_message', {'error': '未配置 OpenAI API Key，请设置环境变量 OPENAI_API_KEY'})
            return
    elif session.llm_backend == 'deepseek':
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            print("❌ [DeepSeek] 启动生成失败：未检测到 API Key")
            emit('error_message', {'error': '未配置 DeepSeek API Key，请设置环境变量 DEEPSEEK_API_KEY'})
            return

    print(f"📝 开始生成故事，主题: {session.topic}")  # 添加调试日志
    
    # 发送步骤列表
    emit('story_steps', {
        'steps': STORY_STEPS,
        'topic': session.topic,
        'llm_backend': session.llm_backend,
        'llm_model': session.llm_model,
    })
    
    # 发送第一个步骤，等待用户选择
    current_step = session.get_current_step()
    if current_step:
        emit('next_step', {
            'step': current_step,
            'step_index': session.current_step_index,
            'total_steps': len(STORY_STEPS)
        })
@socketio.on('auto_execute_next_step')
def handle_auto_execute_next_step(data):
    session_id = request.sid
    print(f"🔄 收到 auto_execute_next_step 事件，session_id: {session_id}")
    
    if session_id not in user_sessions:
        print(f"❌ session_id {session_id} 不存在于 user_sessions 中")
        return
    
    session = user_sessions[session_id]
    agent = get_session_story_agent(session)
    step_id = data.get('step_id')
    print(f"🎯 要执行的步骤ID: {step_id}")
    
    current_step = session.get_current_step()
    print(f"📍 当前步骤: {current_step['id'] if current_step else 'None'}")
    
    if not current_step or current_step['id'] != step_id:
        print(f"❌ 步骤不匹配或不存在，当前: {current_step['id'] if current_step else 'None'}, 请求: {step_id}")
        return
    
    print(f"✅ 开始自动执行步骤: {current_step['name']}")
    
    try:
        session.is_generating = True
        session.should_pause = False
        emit('step_generating', {'message': f'正在生成：{current_step["name"]}'})
        
        # 根据步骤ID调用对应的方法
        result = None
        try:
            # 检查是否需要暂停
            if session.should_pause:
                session.is_generating = False
                emit('step_paused', {'step_id': step_id, 'message': '生成已暂停'})
                return
            
            method_name = current_step.get('method')
            if hasattr(agent, method_name):
                method = getattr(agent, method_name)
                if method_name == 'create_book_spec':
                    result = method(session.topic)
                else:
                    # 获取之前步骤的结果作为上下文
                    context = session.get_context_for_step(current_step['id'])
                    result = method(context)
            else:
                result = f"方法 {method_name} 未找到"
            
            if result:
                session.step_results[current_step['id']] = result
                print(f"✅ 步骤 {current_step['id']} 完成，结果长度: {len(result)}")
                emit('step_result', {
                    'step_id': current_step['id'],
                    'result': markdown.markdown(result),
                    'skipped': False,
                    'custom': False,
                    'regenerated': False
                })
                
                # 更新步骤索引但不自动执行下一步
                print(f"📈 当前步骤索引: {session.current_step_index}, 总步骤数: {len(STORY_STEPS)}")
                session.current_step_index += 1
                print(f"📈 更新后步骤索引: {session.current_step_index}")
                
                if session.current_step_index < len(STORY_STEPS):
                    next_step = session.get_current_step()
                    print(f"🔄 准备显示下一步选项: {next_step['name']} (ID: {next_step['id']})")
                    emit('next_step', {
                        'step': next_step,
                        'step_index': session.current_step_index,
                        'total_steps': len(STORY_STEPS)
                    })
                    print(f"📤 已发送 next_step 事件，等待用户选择")
                    # 移除自动执行逻辑，让用户手动选择
                else:
                    print("🎉 所有步骤已完成，准备生成最终小说")
                    # 所有步骤完成
                    final_novel = generate_final_novel(session)
                    emit('story_complete', {
                        'message': '🎉 故事生成完成！',
                        'novel_content': markdown.markdown(final_novel)
                    })
                    
        except Exception as e:
            print(f"生成步骤时出错: {str(e)}")
            emit('error_message', {'error': f'生成失败: {str(e)}'})
        finally:
            session.is_generating = False
            
    except Exception as e:
        print(f"自动执行步骤时出错: {str(e)}")
        emit('error_message', {'error': f'自动执行失败: {str(e)}'})

@socketio.on('execute_step')
def handle_execute_step(data):
    """处理步骤执行请求"""
    print(f"🎯 收到执行步骤请求: {data}")
    
    step_id = data.get('step_id')
    action = data.get('action', 'generate')
    session_id = request.sid
    
    print(f"📋 步骤ID: {step_id}, 动作: {action}, 会话ID: {session_id}")
    
    if session_id not in user_sessions:
        print(f"❌ 会话 {session_id} 不存在")
        emit('error_message', {'error': '会话不存在，请重新开始'})
        return
    
    session = user_sessions[session_id]
    agent = get_session_story_agent(session)
    print(f"✅ 找到会话，当前主题: {session.topic}")
    
    # 查找当前步骤
    current_step = None
    for step in STORY_STEPS:
        if step['id'] == step_id:
            current_step = step
            break
    
    if not current_step:
        print(f"❌ 未找到步骤: {step_id}")
        emit('error_message', {'error': f'未找到步骤: {step_id}'})
        return
    
    print(f"📝 找到步骤: {current_step['name']}")
    
    try:
        if action == 'skip':
            print(f"⏭️ 跳过步骤: {step_id}")
            # 跳过步骤
            result = f"已跳过步骤：{current_step['name']}"
            session.step_results[step_id] = result
            emit('step_result', {
                'step_id': step_id,
                'result': result,
                'skipped': True
            })
        elif action == 'custom':
            print(f"✏️ 使用自定义内容: {step_id}")
            # 使用用户自定义内容
            user_input = data.get('user_input', '')
            session.step_results[step_id] = user_input
            emit('step_result', {
                'step_id': step_id,
                'result': user_input,
                'custom': True
            })
        elif action == 'generate':
            print(f"🚀 开始生成步骤: {step_id}")
            # AI生成内容
            session.is_generating = True
            session.should_pause = False
            emit('step_generating', {'message': f'正在生成：{current_step["name"]}'})
            
            # 根据步骤ID调用对应的方法
            result = None
            try:
                print(f"🔧 进入生成逻辑，步骤: {step_id}")
                # 检查是否需要暂停
                if session.should_pause:
                    print("⏸️ 检测到暂停信号")
                    session.is_generating = False
                    emit('step_paused', {'step_id': step_id, 'message': '生成已暂停'})
                    return
                
                if step_id == 'init_book_spec':
                    print(f"🔄 开始调用 init_book_spec，主题: {session.topic}")
                    _, result = agent.init_book_spec(session.topic)
                    print(f"✅ init_book_spec 调用完成，结果长度: {len(result) if result else 0}")
                elif step_id == 'enhance_book_spec':
                    # 获取前一步的结果作为输入
                    book_spec = session.step_results.get('init_book_spec', '')
                    if book_spec:
                        _, result = agent.enhance_book_spec(book_spec)
                    else:
                        result = "错误：需要先完成书籍规格初始化"
                elif step_id == 'character_design':
                    # 使用增强后的书籍规格
                    book_spec = session.step_results.get('enhance_book_spec', 
                                session.step_results.get('init_book_spec', ''))
                    if book_spec:
                        result = agent.character_design(book_spec)
                    else:
                        result = "错误：需要先完成书籍规格设定"
                elif step_id == 'create_plot_chapters':
                    book_spec = session.step_results.get('enhance_book_spec', 
                                session.step_results.get('init_book_spec', ''))
                    if book_spec:
                        _, result = agent.create_plot_chapters(book_spec)
                    else:
                        result = "错误：需要先完成书籍规格设定"
                elif step_id in ['optimize_chapter_plan', 'set_literary_style', 'generate_novel', 'optimize_content']:
                    # 对于其他步骤，调用对应的独立方法
                    if step_id == 'optimize_chapter_plan':
                        chapter_plan = session.step_results.get('create_plot_chapters', '')
                        book_spec = session.step_results.get('enhance_book_spec', 
                                    session.step_results.get('init_book_spec', ''))
                        character_profiles = session.step_results.get('character_design', '')
                        result = agent.optimize_chapter_plan(chapter_plan, book_spec, character_profiles)
                    elif step_id == 'set_literary_style':
                        book_spec = session.step_results.get('enhance_book_spec', 
                                    session.step_results.get('init_book_spec', ''))
                        character_profiles = session.step_results.get('character_design', '')
                        chapter_plan = session.step_results.get('optimize_chapter_plan', 
                                      session.step_results.get('create_plot_chapters', ''))
                        result = agent.set_literary_style(book_spec, character_profiles, chapter_plan)
                    elif step_id == 'generate_novel':
                        book_spec = session.step_results.get('enhance_book_spec', 
                                    session.step_results.get('init_book_spec', ''))
                        character_profiles = session.step_results.get('character_design', '')
                        chapter_plan = session.step_results.get('optimize_chapter_plan', 
                                      session.step_results.get('create_plot_chapters', ''))
                        style_guide = session.step_results.get('set_literary_style', '')
                        
                        # 检查是否启用红楼梦文风
                        if session.hongloumeng_enabled and hongloumeng_generator:
                            print("🎭 使用红楼梦文风生成小说...")
                            emit('step_generating', {'message': '正在使用红楼梦文风生成（多候选+重排序+自评回写）...'})
                            
                            # 先使用常规方式生成内容
                            raw_result = agent.generate_novel(book_spec, character_profiles, chapter_plan, style_guide)
                            
                            # 然后使用红楼梦生成器进行风格转换
                            if raw_result:
                                if isinstance(raw_result, list):
                                    raw_text = raw_result[0] if raw_result else ""
                                else:
                                    raw_text = raw_result
                                
                                # 使用红楼梦生成器进行风格改写
                                hongloumeng_result = hongloumeng_generator.refine_content(raw_text)
                                result = hongloumeng_result if hongloumeng_result else raw_result
                            else:
                                result = raw_result
                        
                        # 检查是否启用科幻文风
                        elif session.scifi_enabled and scifi_generator:
                            print("🚀 使用科幻文风生成小说...")
                            emit('step_generating', {'message': '正在使用硬科幻/赛博朋克文风生成（多候选+重排序+自评回写）...'})
                            
                            # 先使用常规方式生成内容
                            raw_result = agent.generate_novel(book_spec, character_profiles, chapter_plan, style_guide)
                            
                            # 然后使用科幻生成器进行风格转换
                            if raw_result:
                                if isinstance(raw_result, list):
                                    raw_text = raw_result[0] if raw_result else ""
                                else:
                                    raw_text = raw_result
                                
                                # 使用科幻生成器进行风格改写
                                scifi_result = scifi_generator.self_evaluate_and_rewrite(raw_text)
                                result = scifi_result if scifi_result else raw_text
                            else:
                                result = raw_result
                        
                        # 检查是否启用言情文风
                        elif session.romance_enabled and romance_generator:
                            print("💕 使用言情文风生成小说...")
                            emit('step_generating', {'message': '正在使用言情文风生成（多候选+重排序+自评回写）...'})
                            
                            raw_result = agent.generate_novel(book_spec, character_profiles, chapter_plan, style_guide)
                            if raw_result:
                                raw_text = raw_result[0] if isinstance(raw_result, list) else raw_result
                                result = romance_generator.self_evaluate_and_rewrite(raw_text) or raw_text
                            else:
                                result = raw_result

                        # 检查是否启用悬疑文风
                        elif session.mystery_enabled and mystery_generator:
                            print("🔍 使用悬疑文风生成小说...")
                            emit('step_generating', {'message': '正在使用悬疑文风生成（多候选+重排序+自评回写）...'})
                            
                            raw_result = agent.generate_novel(book_spec, character_profiles, chapter_plan, style_guide)
                            if raw_result:
                                raw_text = raw_result[0] if isinstance(raw_result, list) else raw_result
                                result = mystery_generator.self_evaluate_and_rewrite(raw_text) or raw_text
                            else:
                                result = raw_result
                        else:
                            result = agent.generate_novel(book_spec, character_profiles, chapter_plan, style_guide)
                    elif step_id == 'optimize_content':
                        novel_content = session.step_results.get('generate_novel', '')
                        if novel_content:
                            result = agent.optimize_content(novel_content)
                        else:
                            result = "错误：需要先生成小说内容"
                else:
                    # 默认处理
                    context = session.get_context_for_step(step_id)
                    prompt = current_step['prompt_template'].format(topic=session.topic)
                    full_prompt = f"{context}\n\n{prompt}" if context else prompt
                    result = agent.query_chat([{"role": "user", "content": full_prompt}])
                
                # 确保结果是字符串格式
                if result is None:
                    result = "生成失败，请重试"
                elif isinstance(result, list) and len(result) > 0:
                    result = result[0]
                elif isinstance(result, list):
                    result = "生成内容为空"
                    
            except Exception as e:
                result = f"生成失败：{str(e)}"
                print(f"❌ 步骤 {step_id} 生成失败: {e}")
                import traceback
                traceback.print_exc()  # 打印完整的错误堆栈
            finally:
                session.is_generating = False
            
            session.step_results[step_id] = result
            
            emit('step_result', {
                'step_id': step_id,
                'result': result,
                'generated': True
            })
        
        # 更新步骤索引并检查是否有下一步
        step_index = None
        for i, step in enumerate(STORY_STEPS):
            if step['id'] == step_id:
                step_index = i
                break
        
        if step_index is not None:
            session.current_step_index = step_index + 1
            print(f"📈 更新步骤索引到: {session.current_step_index}")
            
            if session.current_step_index < len(STORY_STEPS):
                next_step = STORY_STEPS[session.current_step_index]
                print(f"🔄 准备显示下一步选项: {next_step['name']} (ID: {next_step['id']})")
                emit('next_step', {
                    'step': next_step,
                    'step_index': session.current_step_index,
                    'total_steps': len(STORY_STEPS)
                })
                print(f"📤 已发送 next_step 事件，等待用户选择")
            else:
                print("🎉 所有步骤已完成，准备生成最终小说")
                # 生成最终小说内容
                final_novel = generate_final_novel(session)
                emit('story_complete', {
                    'message': '🎉 故事生成完成！',
                    'novel_content': markdown.markdown(final_novel)
                })
    
    except Exception as e:
        print(f"生成步骤时出错: {e}")
        emit('error_message', {'error': f'生成失败: {str(e)}'})

@socketio.on('regenerate_step')
def handle_regenerate_step(data):
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    agent = get_session_story_agent(session)
    step_id = data.get('step_id')
    
    # 找到对应的步骤
    step = None
    for s in STORY_STEPS:
        if s['id'] == step_id:
            step = s
            break
    
    if not step:
        emit('error_message', {'error': '步骤不存在'})
        return
    
    try:
        emit('step_generating', {'message': f'正在重新生成：{step["name"]}'})
        
        # 构建提示词
        context = session.get_context_for_step(step_id)
        prompt = step['prompt_template'].format(topic=session.topic)
        full_prompt = f"{context}\n\n{prompt}\n\n请提供一个不同的版本：" if context else f"{prompt}\n\n请提供一个不同的版本："
        
        # 调用AI重新生成
        result = agent.generate_story(full_prompt)
        session.step_results[step_id] = result
        
        emit('step_result', {
            'step_id': step_id,
            'result': markdown.markdown(result),
            'regenerated': True
        })
    
    except Exception as e:
        print(f"重新生成步骤时出错: {e}")
        emit('error_message', {'error': f'重新生成失败: {str(e)}'})

@socketio.on('modify_step')
def handle_modify_step(data):
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    step_id = data.get('step_id')
    content = data.get('content', '')
    
    if not content.strip():
        emit('error_message', {'error': '内容不能为空'})
        return
    
    # 更新步骤结果
    session.step_results[step_id] = content
    
    emit('step_modified', {
        'step_id': step_id,
        'content': content
    })

@socketio.on('skip_step')
def handle_skip_step(data):
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    step_id = data.get('step_id')
    
    # 标记步骤为跳过
    session.step_results[step_id] = "[此步骤已跳过]"
    
    emit('step_result', {
        'step_id': step_id,
        'result': "[此步骤已跳过]",
        'skipped': True
    })
    
    # 检查是否完成所有步骤
    session.advance_step()
    if session.is_complete():
        # 生成最终小说内容
        final_novel = generate_final_novel(session)
        emit('story_complete', {
            'message': '故事生成完成！',
            'novel_content': final_novel
        })
    else:
        # 发送下一个步骤
        next_step = session.get_current_step()
        if next_step:
            emit('next_step', {
                'step': next_step,
                'step_index': session.current_step_index,
                'total_steps': len(STORY_STEPS)
            })

@socketio.on('custom_step')
def handle_custom_step(data):
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    step_id = data.get('step_id')
    content = data.get('content', '')
    
    if not content.strip():
        emit('error_message', {'error': '自定义内容不能为空'})
        return
    
    # 保存自定义内容
    session.step_results[step_id] = content.strip()
    
    emit('step_result', {
        'step_id': step_id,
        'result': content.strip(),
        'custom': True
    })
    
    # 检查是否完成所有步骤
    session.advance_step()
    if session.is_complete():
        # 生成最终小说内容
        final_novel = generate_final_novel(session)
        emit('story_complete', {
            'message': '故事生成完成！',
            'novel_content': final_novel
        })
    else:
        # 发送下一个步骤
        next_step = session.get_current_step()
        if next_step:
            emit('next_step', {
                'step': next_step,
                'step_index': session.current_step_index,
                'total_steps': len(STORY_STEPS)
            })

@socketio.on('pause_generation')
def handle_pause_generation(data):
    """暂停当前生成"""
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    if session.is_generating:
        session.should_pause = True
        emit('generation_paused', {'message': '正在暂停生成...'})
    else:
        emit('error_message', {'error': '当前没有正在进行的生成任务'})

@socketio.on('skip_current_step')
def handle_skip_current_step(data):
    """跳过当前正在生成的步骤"""
    session_id = request.sid
    if session_id not in user_sessions:
        emit('error_message', {'error': '会话不存在'})
        return
    
    session = user_sessions[session_id]
    current_step = session.get_current_step()
    
    if not current_step:
        emit('error_message', {'error': '没有当前步骤'})
        return
    
    # 停止生成并跳过
    session.should_pause = True
    session.is_generating = False
    
    step_id = current_step['id']
    result = f"已跳过步骤：{current_step['name']}"
    session.step_results[step_id] = result
    
    emit('step_result', {
        'step_id': step_id,
        'result': result,
        'skipped': True
    })

@socketio.on('get_session_status')
def handle_get_session_status():
    session_id = request.sid
    if session_id not in user_sessions:
        emit('session_status', {'exists': False})
        return
    
    session = user_sessions[session_id]
    emit('session_status', {
        'exists': True,
        'topic': session.topic,
        'current_step': session.current_step_index,
        'total_steps': len(STORY_STEPS),
        'is_complete': session.is_complete(),
        'step_results': session.step_results
    })

def generate_final_novel(session):
    """生成最终的纯净小说内容"""
    try:
        agent = get_session_story_agent(session)
        # 收集所有步骤的结果
        all_content = []
        for step in STORY_STEPS:
            step_id = step['id']
            if step_id in session.step_results and session.step_results[step_id].strip():
                all_content.append(session.step_results[step_id])
        
        if not all_content:
            return "暂无内容"
        
        # 合并所有内容
        combined_content = "\n\n".join(all_content)
        
        # 使用AI优化和整理最终内容
        optimization_prompt = f"""
请将以下分步骤生成的小说内容整理成一个完整、流畅的小说。要求：
1. 保持故事的连贯性和逻辑性
2. 优化语言表达，使其更加流畅自然
3. 去除任何步骤标记或生成过程的痕迹
4. 确保内容完整且具有良好的可读性
5. 只输出最终的小说正文，不要包含任何说明或注释

原始内容：
{combined_content}

请输出整理后的完整小说：
"""
        
        final_novel = agent.optimize_content(optimization_prompt)
        return final_novel
        
    except Exception as e:
        print(f"生成最终小说时出错: {e}")
        # 如果优化失败，返回原始合并内容
        all_content = []
        for step in STORY_STEPS:
            step_id = step['id']
            if step_id in session.step_results and session.step_results[step_id].strip():
                all_content.append(session.step_results[step_id])
        return "\n\n".join(all_content) if all_content else "暂无内容"

def get_local_ip():
    """获取本机IP地址"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    print("🌟 中文VibeWriting - DeepSeek Reasoner交互式智能小说生成器启动中...")
    
    # 初始化DeepSeek Reasoner引擎
    if not initialize_story_agent():
        print("❌ DeepSeek Reasoner引擎初始化失败，请检查API配置")
        sys.exit(1)
    
    # 获取本机IP
    local_ip = get_local_ip()
    port = 5000
    
    print(f"📱 本地访问：http://localhost:{port}")
    print(f"🌐 局域网访问：http://{local_ip}:{port}")
    print("⚠️  注意：局域网内其他用户也可以访问！")
    print("💡 现在支持步骤级交互控制，您可以：")
    print("   - 选择生成、跳过或自定义每个步骤")
    print("   - 审查和修改每个步骤的结果")
    print("   - 重新生成不满意的步骤")
    
    # 启动应用
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=True,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 中文VibeWriting应用已停止")
    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
