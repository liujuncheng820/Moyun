"""
中文VibeWriting - 基于DeepSeek Reasoner的智能故事生成引擎

核心模块：StoryAgent
采用DeepSeek Reasoner作为底层AI引擎，提供专业级的中文小说创作能力

主要功能：
- 多阶段故事生成流程（规格初始化→增强→章节大纲→场景细分→逐场景创作）
- DeepSeek Reasoner推理能力优化的提示词工程
- 支持多种后端（HuggingFace、llama.cpp、DeepSeek）
- 专为中文语境设计的故事架构
"""

import sys
import time
import re
import json
import requests
import traceback

from src import utils
from src.core.plan import Plan


SUPPORTED_BACKENDS = ["hf", "llama.cpp", "deepseek", "qwen", "volcano", "openai"]  # DeepSeek Reasoner为推荐后端


def generate_prompt_parts(
        messages, include_roles=set(('user', 'assistant', 'system'))):
    last_role = None
    messages = [m for m in messages if m['role'] in include_roles]
    for idx, message in enumerate(messages):
        nl = "\n" if idx > 0 else ""
        if message['role'] == 'system':
            if idx > 0 and last_role not in (None, "system"):
                raise ValueError("system message not at start")
            yield f"{message['content']}"
        elif message['role'] == 'user':
            yield f"{nl}### USER: {message['content']}"
        elif message['role'] == 'assistant':
            yield f"{nl}### ASSISTANT: {message['content']}"
        last_role = message['role']
    if last_role != 'assistant':
        yield '\n### ASSISTANT:'


def _query_chat_hf(endpoint, messages, tokenizer, retries=3,
                   request_timeout=120, max_tokens=4096,
                   extra_options={'do_sample': True}):
    endpoint = endpoint.rstrip('/')
    prompt = ''.join(generate_prompt_parts(messages))
    
    # 简单的token估算，避免使用tokenizer
    if tokenizer is None:
        # 粗略估算：1个token约等于4个字符
        estimated_tokens = len(prompt) // 4
    else:
        tokens = tokenizer(prompt, add_special_tokens=True,
                           truncation=False)['input_ids']
        estimated_tokens = len(tokens)
    
    # 检查是否能连接到后端服务器
    try:
        import requests
        test_response = requests.get(f"{endpoint.replace('/generate', '')}/health", timeout=2)
        server_available = test_response.status_code == 200
    except:
        server_available = False
    
    # 如果服务器不可用，直接返回失败
    if not server_available:
        print(f"❌ 后端服务器 {endpoint} 不可用，API调用失败")
        return None
    
    data = {
        "inputs": prompt,
        "parameters": {
            'max_new_tokens': max_tokens - estimated_tokens,
            **extra_options
        }
    }
    headers = {'Content-Type': 'application/json'}

    while retries > 0:
        try:
            response = requests.post(
                f"{endpoint}/generate", headers=headers, data=json.dumps(data),
                timeout=request_timeout)
            if messages and messages[-1]["role"] == "assistant":
                result_prefix = messages[-1]["content"]
            else:
                result_prefix = ''
            generated_text = result_prefix + json.loads(
                response.text)['generated_text']
            return generated_text
        except Exception:
            traceback.print_exc()
            print('Timeout error, retrying...')
            retries -= 1
            time.sleep(5)
    else:
        # 如果所有重试都失败，直接返回失败
        print("❌ 所有HuggingFace API重试都失败，API调用失败")
        return None


def _query_chat_deepseek(endpoint, messages, retries=3, request_timeout=120,
                         max_tokens=4096, extra_options={}):
    """DeepSeek API 查询函数"""
    import os
    
    # 获取API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 未找到DEEPSEEK_API_KEY环境变量，API调用失败")
        return None
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 转换消息格式为DeepSeek API格式
    if not endpoint or endpoint.strip() == "":
        endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    print(f"🔗 [Qwen] Endpoint: {endpoint}")

    api_messages = []
    for msg in messages:
        if msg['role'] in ['system', 'user', 'assistant']:
            api_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
    
    data = {
        'model': 'deepseek-reasoner',  # 使用DeepSeek Reasoner模型获得更强的推理能力
        'messages': api_messages,
        'max_tokens': max_tokens,
        'temperature': 0.7,
        'stream': False,
        **extra_options
    }
    
    for attempt in range(retries):
        try:
            print(f"\n🔄 正在调用DeepSeek API (尝试 {attempt + 1}/{retries})...")
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=data,
                timeout=request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0]['message']
                    content = message.get('content', '')
                    
                    # DeepSeek Reasoner 模型可能返回 reasoning_content 而不是 content
                    if not content and 'reasoning_content' in message:
                        content = message['reasoning_content']
                        print(f"📝 使用 reasoning_content 作为返回内容")
                    
                    print(f"✅ DeepSeek API 调用成功，返回内容长度: {len(content)}")
                    return content
                else:
                    print(f"⚠️ DeepSeek API 返回格式异常: {result}")
            else:
                print(f"❌ DeepSeek API 调用失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                
        except Exception as e:
            print(f"❌ DeepSeek API 调用异常: {e}")
            
        if attempt < retries - 1:
            print(f"⏳ 等待5秒后重试...")
            time.sleep(5)
    
    print("❌ 所有DeepSeek API调用都失败，API调用失败")
    return None

def _query_chat_qwen(endpoint, messages, retries=3, request_timeout=120,
                     max_tokens=4096, extra_options={}):
    import os

    # 尝试获取多种可能的环境变量名
    api_key = os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    
    if not api_key:
        print("❌ [Qwen] 未找到 QWEN_API_KEY 或 DASHSCOPE_API_KEY 环境变量")
        return None
        
    api_key = api_key.strip()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    api_messages = []
    for msg in messages:
        if msg['role'] in ['system', 'user', 'assistant']:
            api_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    # 确保 model 参数被正确设置
    model = extra_options.get('model', 'qwen-plus')
    
    # 移除 max_tokens 和 stream 等可能导致问题的参数
    # 千问某些模型对 max_tokens 有限制，或者默认行为不同
    # 保留 messages, model, temperature
    clean_data = {
        'model': model,
        'messages': api_messages,
        'temperature': 0.7
    }
    
    # 仅当明确指定 max_tokens 且不是极大值时才传递
    if max_tokens and max_tokens < 6000:
        clean_data['max_tokens'] = max_tokens
        
    # 合并其他选项，但要小心冲突
    for k, v in extra_options.items():
        if k not in ['messages', 'model', 'stream']:
            clean_data[k] = v

    print(f"\n🚀 [Qwen] 准备调用 API...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Model: {model}")
    print(f"   Messages: {len(api_messages)} 条")

    for attempt in range(retries):
        try:
            print(f"🔄 [Qwen] 发送请求 (尝试 {attempt + 1}/{retries})...")
            # 使用更长的超时时间，千问处理有时较慢
            response = requests.post(
                endpoint,
                headers=headers,
                json=clean_data,
                timeout=max(request_timeout, 180) 
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0].get('message', {}) or {}
                    content = message.get('content', '')
                    print(f"✅ [Qwen] 调用成功，返回内容长度: {len(content)}")
                    return content
                else:
                    print(f"⚠️ [Qwen] 返回格式异常: {result}")
            else:
                print(f"❌ [Qwen] 调用失败，状态码: {response.status_code}")
                print(f"   错误信息: {response.text}")

        except Exception as e:
            print(f"❌ [Qwen] 调用异常: {e}")
            import traceback
            traceback.print_exc()

        if attempt < retries - 1:
            print(f"⏳ [Qwen] 等待5秒后重试...")
            time.sleep(5)

    print("❌ [Qwen] 所有重试均失败")
    return None

def _query_chat_volcano(endpoint, messages, retries=3, request_timeout=120,
                        max_tokens=4096, extra_options={}):
    import os

    api_key = os.environ.get("VOLCANO_API_KEY")
    if not api_key:
        print("❌ [Volcano] 未找到 VOLCANO_API_KEY 环境变量，API调用失败")
        return None
    
    api_key = api_key.strip()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    api_messages = []
    for msg in messages:
        if msg['role'] in ['system', 'user', 'assistant']:
            api_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    # Volcano 引擎通常需要具体的 Endpoint ID 作为 model 参数
    # 如果用户在界面选择了具体的 Endpoint ID，这里直接使用
    # 如果是通用模型名称，可能需要用户自己替换为 Endpoint ID
    model = extra_options.get('model', 'ep-20240604123456-abcde')
    
    data = {
        'model': model,
        'messages': api_messages,
        'max_tokens': max_tokens,
        'temperature': 0.7,
        'stream': False,
        **extra_options
    }

    print(f"\n🚀 [Volcano] 准备调用 API...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Model (Endpoint ID): {model}")
    print(f"   Messages: {len(api_messages)} 条")

    for attempt in range(retries):
        try:
            print(f"🔄 [Volcano] 发送请求 (尝试 {attempt + 1}/{retries})...")
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=request_timeout
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0].get('message', {}) or {}
                    content = message.get('content', '')
                    print(f"✅ [Volcano] 调用成功，返回内容长度: {len(content)}")
                    return content
                else:
                    print(f"⚠️ [Volcano] 返回格式异常: {result}")
            else:
                print(f"❌ [Volcano] 调用失败，状态码: {response.status_code}")
                print(f"   错误信息: {response.text}")

        except Exception as e:
            print(f"❌ [Volcano] 调用异常: {e}")
            import traceback
            traceback.print_exc()

        if attempt < retries - 1:
            print(f"⏳ [Volcano] 等待5秒后重试...")
            time.sleep(5)

    print("❌ [Volcano] 所有重试均失败")
    return None

def _query_chat_openai(endpoint, messages, retries=3, request_timeout=120,
                       max_tokens=4096, extra_options={}):
    import os

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ [OpenAI] 未找到 OPENAI_API_KEY 环境变量，API调用失败")
        return None
    
    api_key = api_key.strip()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    # 如果未提供 endpoint，使用 OpenAI 官方默认地址
    if not endpoint or endpoint.strip() == "":
        endpoint = "https://api.openai.com/v1/chat/completions"

    api_messages = []
    for msg in messages:
        if msg['role'] in ['system', 'user', 'assistant']:
            api_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    model = extra_options.get('model', 'gpt-3.5-turbo')
    
    data = {
        'model': model,
        'messages': api_messages,
        'temperature': 0.7,
        **extra_options
    }
    
    # 某些模型可能对 max_tokens 有不同处理，这里简单透传
    if max_tokens:
        data['max_tokens'] = max_tokens

    print(f"\n🚀 [OpenAI] 准备调用 API...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Model: {model}")
    print(f"   Messages: {len(api_messages)} 条")

    for attempt in range(retries):
        try:
            print(f"🔄 [OpenAI] 发送请求 (尝试 {attempt + 1}/{retries})...")
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=request_timeout
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0].get('message', {}) or {}
                    content = message.get('content', '')
                    print(f"✅ [OpenAI] 调用成功，返回内容长度: {len(content)}")
                    return content
                else:
                    print(f"⚠️ [OpenAI] 返回格式异常: {result}")
            else:
                print(f"❌ [OpenAI] 调用失败，状态码: {response.status_code}")
                print(f"   错误信息: {response.text}")

        except Exception as e:
            print(f"❌ [OpenAI] 调用异常: {e}")
            import traceback
            traceback.print_exc()

        if attempt < retries - 1:
            print(f"⏳ [OpenAI] 等待5秒后重试...")
            time.sleep(5)

    print("❌ [OpenAI] 所有重试均失败")
    return None

def _query_chat_llamacpp(endpoint, messages, retries=3, request_timeout=120,
                         max_tokens=4096, extra_options={}):
    endpoint = endpoint.rstrip('/')
    headers = {'Content-Type': 'application/json'}
    prompt = ''.join(generate_prompt_parts(messages))
    print(f"\n\n========== Submitting prompt: >>\n{prompt}", end="")
    sys.stdout.flush()
    response = requests.post(
        f"{endpoint}/tokenize", headers=headers,
        data=json.dumps({"content": prompt}),
        timeout=request_timeout, stream=False)
    tokens = [1, *response.json()["tokens"]]
    data = {
        "prompt": tokens,
        "stream": True,
        "n_predict": max_tokens - len(tokens),
        **extra_options,
    }
    jdata = json.dumps(data)
    request_kwargs = dict(headers=headers, data=jdata,
                          timeout=request_timeout, stream=True)
    response = requests.post(f"{endpoint}/completion", **request_kwargs)
    result = bytearray()
    if messages and messages[-1]["role"] == "assistant":
        result += messages[-1]["content"].encode("utf-8")
    is_first = True
    for line in response.iter_lines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(b"error:"):
            retries -= 1
            print(f"\nError(retry={retries}): {line!r}")
            if retries < 0:
                break
            del response
            time.sleep(5)
            response = requests.post(f"{endpoint}/completion", **request_kwargs)
            is_first = True
            result.clear()
            continue
        if not line.startswith(b"data: "):
            raise ValueError(f"Got unexpected response: {line!r}")
        parsed = json.loads(line[6:])
        content = parsed.get("content", b"")
        result += bytes(content, encoding="utf-8")
        if is_first:
            is_first = False
            print("<<|", end="")
            sys.stdout.flush()
        print(content, end="")
        sys.stdout.flush()
        if parsed.get("stop") is True:
            break
    print("\nDone reading response.")
    return str(result, encoding="utf-8").strip()


class StoryAgent:
    """中文VibeWriting核心故事生成代理
    
    基于DeepSeek Reasoner的智能故事创作引擎，提供多阶段故事生成能力：
    1. 故事规格初始化和增强
    2. 章节大纲创建和优化
    3. 场景细分和逐场景生成
    
    推荐使用DeepSeek后端以获得最佳的中文创作效果和推理能力
    """
    
    def __init__(self, backend_uri, backend="deepseek", request_timeout=120,
                 max_tokens=4096, n_crop_previous=400,
                 prompt_engine=None, form='novel',
                 extra_options={}, scene_extra_options={}):
        """初始化故事生成代理
        
        Args:
            backend_uri: API端点地址
            backend: 后端类型，推荐使用"deepseek"以获得最佳DeepSeek Reasoner体验
            request_timeout: 请求超时时间
            max_tokens: 最大生成token数
            n_crop_previous: 上下文裁剪长度
            prompt_engine: 提示词引擎，默认使用中文优化的提示词
            form: 生成形式，默认为'novel'
            extra_options: 额外选项
            scene_extra_options: 场景生成额外选项
        """

        self.backend = backend.lower()
        if self.backend not in SUPPORTED_BACKENDS:
            raise ValueError("Unknown backend")

        if self.backend == "hf":
            # 跳过tokenizer下载，避免SSL连接问题
            # from transformers import LlamaTokenizerFast
            # self.tokenizer = LlamaTokenizerFast.from_pretrained(
            #     "GOAT-AI/GOAT-70B-Storytelling")
            self.tokenizer = None  # 暂时设为None，后续会创建简单的token计数器

        if prompt_engine is None:
            from src.core import prompts
            self.prompt_engine = prompts  # 使用中文优化的提示词引擎
        else:
            self.prompt_engine = prompt_engine

        self.form = form
        self.max_tokens = max_tokens
        self.extra_options = extra_options
        self.scene_extra_options = extra_options.copy()
        self.scene_extra_options.update(scene_extra_options)
        self.backend_uri = backend_uri
        self.n_crop_previous = n_crop_previous
        self.request_timeout = request_timeout

    def query_chat(self, messages, retries=3, max_tokens=None):
        """调用后端AI进行对话生成
        
        优先使用DeepSeek Reasoner后端以获得最佳的推理和中文生成效果
        
        Parameters
        ----------
        messages : List[Dict]
            Chat messages
        retries : int
            Number of retries
        max_tokens : int, optional
            Maximum tokens to generate, defaults to self.max_tokens
            
        Returns
        -------
        str
            Response text
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
            
        if self.backend == "hf":
            result = _query_chat_hf(
                self.backend_uri, messages, self.tokenizer, retries=retries,
                request_timeout=self.request_timeout,
                max_tokens=max_tokens, extra_options=self.extra_options)
        elif self.backend == "llama.cpp":
            result = _query_chat_llamacpp(
                self.backend_uri, messages, retries=retries,
                request_timeout=self.request_timeout,
                max_tokens=max_tokens, extra_options=self.extra_options)
        elif self.backend == "deepseek":
            # 使用DeepSeek Reasoner进行智能推理和生成
            result = _query_chat_deepseek(
                self.backend_uri, messages, retries=retries,
                request_timeout=self.request_timeout,
                max_tokens=max_tokens, extra_options=self.extra_options)
        elif self.backend == "qwen":
            result = _query_chat_qwen(
                self.backend_uri, messages, retries=retries,
                request_timeout=self.request_timeout,
                max_tokens=max_tokens, extra_options=self.extra_options)
        elif self.backend == "volcano":
            result = _query_chat_volcano(
                self.backend_uri, messages, retries=retries,
                request_timeout=self.request_timeout,
                max_tokens=max_tokens, extra_options=self.extra_options)
        elif self.backend == "openai":
            result = _query_chat_openai(
                self.backend_uri, messages, retries=retries,
                request_timeout=self.request_timeout,
                max_tokens=max_tokens, extra_options=self.extra_options)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
        return result

    def parse_book_spec(self, text_spec):
        # Initialize book spec dict with empty fields
        fields = self.prompt_engine.book_spec_fields
        spec_dict = {field: '' for field in fields}
        
        # 增加对 None 或非字符串类型的处理
        if not text_spec:
            print("⚠️ parse_book_spec 收到空输入")
            return spec_dict
            
        if not isinstance(text_spec, str):
            print(f"⚠️ parse_book_spec 收到非字符串输入: {type(text_spec)}")
            text_spec = str(text_spec)

        last_field = None
        if "\"\"\"" in text_spec[:int(len(text_spec)/2)]:
            header, sep, text_spec = text_spec.partition("\"\"\"")
        text_spec = text_spec.strip()

        # Process raw spec into dict
        for line in text_spec.split('\n'):
            pseudokey, sep, value = line.partition(':')
            pseudokey = pseudokey.lower().strip()
            matched_key = [key for key in fields
                           if (key.lower().strip() in pseudokey)
                           and (len(pseudokey) < (2 * len(key.strip())))]
            if (':' in line) and (len(matched_key) == 1):
                last_field = matched_key[0]
                if last_field in spec_dict:
                    spec_dict[last_field] += value.strip()
            elif ':' in line:
                last_field = 'other'
                spec_dict[last_field] = ''
            else:
                if last_field:
                    # If line does not contain ':' it should be
                    # the continuation of the last field's value
                    spec_dict[last_field] += ' ' + line.strip()
        spec_dict.pop('other', None)
        return spec_dict

    def init_book_spec(self, topic):
        """Creates initial book specification

        Parameters
        ----------
        topic : str
            Short initial topic

        Returns
        -------
        List[Dict]
            Used messages for logging
        str
            Book specification text
        """
        messages = self.prompt_engine.init_book_spec_messages(topic, self.form)
        text_spec = self.query_chat(messages)
        
        # 严格检查返回结果
        if not text_spec:
            print("❌ init_book_spec: 无法从 LLM 获取响应")
            return messages, None
            
        spec_dict = self.parse_book_spec(text_spec)

        text_spec = "\n".join(f"{key}: {value}"
                              for key, value in spec_dict.items())
        # Check and fill in missing fields
        max_retries = 3  # 最多重试3次
        for field in self.prompt_engine.book_spec_fields:
            if not spec_dict.get(field):  # 如果字段为空
                retry_count = 0
                while not spec_dict.get(field) and retry_count < max_retries:
                    print(f"🔄 尝试补充缺失字段: {field} (尝试 {retry_count+1}/{max_retries})")
                    messages = self.prompt_engine.missing_book_spec_messages(
                        field, text_spec)
                    missing_part = self.query_chat(messages)
                    
                    if not missing_part:
                        retry_count += 1
                        continue
                        
                    key, sep, value = missing_part.partition(':')
                    # 如果解析失败，直接使用整个内容作为值
                    if not sep:
                        spec_dict[field] = missing_part.strip()
                    elif key.lower().strip() == field.lower().strip():
                        spec_dict[field] = value.strip()
                    else:
                        # 如果键不匹配，也使用整个内容
                        spec_dict[field] = missing_part.strip()
                    retry_count += 1
                    
        text_spec = "\n".join(f"{key}: {value}"
                              for key, value in spec_dict.items())
        return messages, text_spec

    def enhance_book_spec(self, book_spec):
        """Make book specification more detailed

        Parameters
        ----------
        book_spec : str
            Book specification

        Returns
        -------
        List[Dict]
            Used messages for logging
        str
            Book specification text
        """
        messages = self.prompt_engine.enhance_book_spec_messages(
            book_spec, self.form)
        text_spec = self.query_chat(messages)
        if not text_spec:
            return messages, None
            
        spec_dict_old = self.parse_book_spec(book_spec)
        spec_dict_new = self.parse_book_spec(text_spec)

        # Check and fill in missing fields
        for field in self.prompt_engine.book_spec_fields:
            if not spec_dict_new[field]:
                spec_dict_new[field] = spec_dict_old[field]

        text_spec = "\n".join(f"{key}: {value}"
                              for key, value in spec_dict_new.items())
        return messages, text_spec

    def create_plot_chapters(self, book_spec):
        """Create initial by-plot outline of form

        Parameters
        ----------
        book_spec : str
            Book specification

        Returns
        -------
        List[Dict]
            Used messages for logging
        str
            Raw text plan from DeepSeek (不再解析，直接使用)
        """
        messages = self.prompt_engine.create_plot_chapters_messages(book_spec, self.form)
        
        # 直接获取DeepSeek的输出，不再进行复杂的解析
        text_plan = self.query_chat(messages)
        print(f"✅ DeepSeek返回的章节计划:")
        print(f"'{text_plan}' (长度: {len(text_plan) if text_plan else 0})")
        
        if not text_plan:
            print("❌ DeepSeek API调用失败，无法生成章节计划")
            return messages, None
        
        return messages, text_plan

    def enhance_plot_chapters(self, book_spec, plan):
        """Enhances the outline to make the flow more engaging

        Parameters
        ----------
        book_spec : str
            Book specification
        plan : Dict
            Dict with book plan

        Returns
        -------
        List[Dict]
            Used messages for logging
        dict
            Dict with updated book plan
        """
        text_plan = Plan.plan_2_str(plan)
        all_messages = []
        for act_num in range(3):
            messages = self.prompt_engine.enhance_plot_chapters_messages(
                act_num, text_plan, book_spec, self.form)
            act = self.query_chat(messages)
            if not act:
                print(f"❌ 第{act_num+1}幕增强失败，跳过此幕")
                all_messages.append(messages)
                continue
                
            act_dict = Plan.parse_act(act)
            while len(act_dict['chapters']) < 2:
                act = self.query_chat(messages)
                if not act:
                    print(f"❌ 第{act_num+1}幕重试失败，跳过此幕")
                    break
                act_dict = Plan.parse_act(act)
            else:
                if act_num < len(plan):
                    plan[act_num] = act_dict
                else:
                    plan.extend([{}] * (act_num - len(plan) + 1))
                    plan[act_num] = act_dict
                text_plan = Plan.plan_2_str(plan)
            all_messages.append(messages)
        return all_messages, plan

    def split_chapters_into_scenes(self, plan):
        """Creates a by-scene breakdown of all chapters

        Parameters
        ----------
        plan : Dict
            Dict with book plan

        Returns
        -------
        List[Dict]
            Used messages for logging
        dict
            Dict with updated book plan
        """
        all_messages = []
        act_chapters = {}
        for i, act in enumerate(plan, start=1):
            text_act, chs = Plan.act_2_str(plan, i)
            act_chapters[i] = chs
            messages = self.prompt_engine.split_chapters_into_scenes_messages(
                i, text_act, self.form)
            act_scenes = self.query_chat(messages)
            if not act_scenes:
                print(f"❌ 第{i}幕场景分割失败，跳过此幕")
                act['act_scenes'] = ""
            else:
                act['act_scenes'] = act_scenes
            all_messages.append(messages)

        for i, act in enumerate(plan, start=1):
            act_scenes = act['act_scenes']
            act_scenes = re.split(r'Chapter (\d+)', act_scenes.strip())

            act['chapter_scenes'] = {}
            chapters = [text.strip() for text in act_scenes[:]
                        if (text and text.strip())]
            current_ch = None
            merged_chapters = {}
            for snippet in chapters:
                if snippet.isnumeric():
                    ch_num = int(snippet)
                    if ch_num != current_ch:
                        current_ch = snippet
                        merged_chapters[ch_num] = ''
                    continue
                if merged_chapters:
                    merged_chapters[ch_num] += snippet
            ch_nums = list(merged_chapters.keys()) if len(
                merged_chapters) <= len(act_chapters[i]) else act_chapters[i]
            merged_chapters = {ch_num: merged_chapters[ch_num]
                               for ch_num in ch_nums}
            for ch_num, chapter in merged_chapters.items():
                scenes = re.split(r'Scene \d+.{0,10}?:', chapter)
                scenes = [text.strip() for text in scenes[1:]
                          if (text and (len(text.split()) > 3))]
                if not scenes:
                    continue
                act['chapter_scenes'][ch_num] = scenes
        return all_messages, plan

    @staticmethod
    def prepare_scene_text(text):
        lines = text.split('\n')
        ch_ids = [i for i in range(min(5, len(lines)))
                  if 'Chapter ' in lines[i]]
        if ch_ids:
            lines = lines[ch_ids[-1]+1:]
        sc_ids = [i for i in range(min(5, len(lines)))
                  if 'Scene ' in lines[i]]
        if sc_ids:
            lines = lines[sc_ids[-1]+1:]

        placeholder_i = None
        for i in range(len(lines)):
            if lines[i].startswith('Chapter ') or lines[i].startswith('Scene '):
                placeholder_i = i
                break
        if placeholder_i is not None:
            lines = lines[:i]

        text = '\n'.join(lines)
        return text

    def write_a_scene(
            self, scene, sc_num, ch_num, plan, previous_scene=None):
        """Generates a scene text for a form

        Parameters
        ----------
        scene : str
            Scene description
        sc_num : int
            Scene number
        ch_num : int
            Chapter number
        plan : Dict
            Dict with book plan
        previous_scene : str, optional
            Previous scene text, by default None

        Returns
        -------
        List[Dict]
            Used messages for logging
        str
            Generated scene text
        """
        text_plan = Plan.plan_2_str(plan)
        messages = self.prompt_engine.scene_messages(
            scene, sc_num, ch_num, text_plan, self.form)
        if previous_scene:
            previous_scene = utils.keep_last_n_words(previous_scene,
                                                     n=self.n_crop_previous)
            messages[1]['content'] += f'{self.prompt_engine.prev_scene_intro}\"\"\"{previous_scene}\"\"\"'
        generated_scene = self.query_chat(messages)
        if not generated_scene:
            print(f"❌ 第{ch_num}章第{sc_num}场景生成失败")
            return messages, None
        generated_scene = self.prepare_scene_text(generated_scene)
        return messages, generated_scene

    def continue_a_scene(self, scene, sc_num, ch_num,
                         plan, current_scene=None):
        """Continues a scene text for a form

        Parameters
        ----------
        scene : str
            Scene description
        sc_num : int
            Scene number
        ch_num : int
            Chapter number
        plan : Dict
            Dict with book plan
        current_scene : str, optional
            Text of the current scene so far, by default None

        Returns
        -------
        List[Dict]
            Used messages for logging
        str
            Generated scene continuation text
        """
        text_plan = Plan.plan_2_str(plan)
        messages = self.prompt_engine.scene_messages(
            scene, sc_num, ch_num, text_plan, self.form)
        if current_scene:
            current_scene = utils.keep_last_n_words(current_scene,
                                                    n=self.n_crop_previous)
            messages[1]['content'] += f'{self.prompt_engine.cur_scene_intro}\"\"\"{current_scene}\"\"\"'
        generated_scene = self.query_chat(messages)
        if not generated_scene:
            print(f"❌ 第{ch_num}章第{sc_num}场景续写失败")
            return messages, None
        generated_scene = self.prepare_scene_text(generated_scene)
        return messages, generated_scene

    def generate_story(self, topic):
        """中文VibeWriting完整故事生成流程
        
        使用DeepSeek Reasoner的强大推理能力，执行8阶段智能创作：
        1. 故事规格初始化 - 基于主题生成基础设定
        2. 故事规格增强 - 利用DeepSeek推理能力丰富细节
        3. 角色深度设计 - 创建立体鲜明的角色形象
        4. 章节大纲创建 - 构建三幕式故事结构
        5. 章节结构优化 - 优化故事结构和节奏
        6. 文学风格定调 - 确定叙述风格和语言特色
        7. 高质量内容生成 - 生成完整小说内容
        8. 内容质量优化 - 对生成内容进行润色和完善
        
        Args:
            topic: 故事主题或创作要求
            
        Returns:
            list: 生成的场景文本列表
        """
        print(f"🔄 中文VibeWriting开始使用DeepSeek Reasoner生成故事，主题: {topic}")
        
        print("📝 步骤1: DeepSeek初始化书籍规格...")
        _, book_spec = self.init_book_spec(topic)
        if not book_spec:
            print("❌ 书籍规格初始化失败，无法继续生成故事")
            return ["❌ 故事生成失败：DeepSeek API调用失败，请检查网络连接和API密钥配置"]
        print(f"✅ 书籍规格完成: {book_spec[:100]}...")
        
        print("📝 步骤2: DeepSeek增强书籍规格...")
        _, book_spec = self.enhance_book_spec(book_spec)
        if not book_spec:
            print("❌ 书籍规格增强失败，无法继续生成故事")
            return ["❌ 故事生成失败：DeepSeek API调用失败，请检查网络连接和API密钥配置"]
        print(f"✅ 增强规格完成: {book_spec[:100]}...")
        
        print("📝 步骤3: 深度角色设计...")
        # 创建立体的角色形象
        character_messages = [
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
        
        print("🔄 正在设计角色...")
        character_profiles = self.query_chat(character_messages)
        if character_profiles:
            print(f"✅ 角色设计完成: {character_profiles[:100]}...")
        else:
            character_profiles = "角色设计失败，使用默认设置"
            print("⚠️ 角色设计失败")
        
        print("📝 步骤4: DeepSeek创建章节计划...")
        _, text_plan = self.create_plot_chapters(book_spec)
        if not text_plan:
            print("❌ 章节计划创建失败，无法继续生成故事")
            return ["❌ 故事生成失败：DeepSeek API调用失败，请检查网络连接和API密钥配置"]
        print(f"✅ 章节计划完成: {text_plan[:100]}...")
        
        print("📝 步骤5: 优化章节计划结构...")
        # 对章节计划进行结构化处理和优化
        structure_messages = [
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
        
        print("🔄 正在优化章节结构...")
        enhanced_plan = self.query_chat(structure_messages)
        if enhanced_plan:
            print(f"✅ 章节结构优化完成: {enhanced_plan[:100]}...")
        else:
            enhanced_plan = text_plan
            print("⚠️ 结构优化失败，使用原始计划")
        
        print("📝 步骤6: 文学风格定调...")
        # 确定文学风格和语言特色
        style_messages = [
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
        
        print("🔄 正在确定文学风格...")
        style_guide = self.query_chat(style_messages)
        if style_guide:
            print(f"✅ 风格定调完成: {style_guide[:100]}...")
        else:
            style_guide = "使用通用文学风格"
            print("⚠️ 风格定调失败")
        
        
        print("📝 步骤7: 开始生成高质量小说内容...")
        
        # 使用所有优化信息生成小说内容
        messages = [
            {"role": "system", "content": """你是一位资深的中文小说作家，具有以下特质：
1. 文笔优美，语言生动有力
2. 善于刻画人物心理和情感变化
3. 擅长营造氛围和场景描写
4. 对话自然流畅，符合人物性格
5. 情节紧凑有趣，富有张力
6. 适应各种文学体裁和风格
7. 注重细节描写和情感渲染
8. 善于运用修辞手法增强表现力"""},
            {"role": "user", "content": f"""请根据以下完整的创作资料创作一部高质量的中文小说：

【书籍规格】
{book_spec}

【角色档案】
{character_profiles}

【优化后的章节计划】
{enhanced_plan}

【文学风格指导】
{style_guide}

【创作要求】
1. 文学性：语言优美，富有感染力，运用恰当的修辞手法
2. 可读性：情节引人入胜，节奏把握得当，悬念设置巧妙
3. 人物塑造：角色立体鲜明，性格一致，发展合理
4. 对话质量：自然流畅，符合人物身份，推动情节发展
5. 场景描写：生动细腻，营造沉浸感，调动五感体验
6. 情感深度：触动人心，引发共鸣，层次丰富
7. 结构完整：开头吸引人，中间有起伏，结尾有回味
8. 细节丰富：注重环境描写、心理描写、动作描写的平衡
9. 语言特色：根据风格指导确定的特色进行创作
10. 文化内涵：体现中文文学的深度和美感

请创作一部完整的、高质量的文章，确保每个段落都精心雕琢，每个对话都恰到好处。"""}
        ]
        
        print("🔄 正在调用DeepSeek生成高质量小说...")
        novel_content = self.query_chat(messages)
        
        if not novel_content:
            print("❌ 小说内容生成失败")
            return ["❌ 故事生成失败：DeepSeek API调用失败，请检查网络连接和API密钥配置"]
        
        print("📝 步骤8: 内容质量优化...")
        # 对生成的内容进行质量优化
        optimization_messages = [
            {"role": "system", "content": "你是一位专业的文学编辑，擅长润色和完善文学作品。"},
            {"role": "user", "content": f"""请对以下小说内容进行质量优化：

【原始内容】
{novel_content}

【优化要求】
1. 语言润色：提升文字的优美度和流畅性
2. 情感深化：加强情感表达的深度和感染力
3. 细节完善：补充必要的细节描写
4. 逻辑检查：确保情节逻辑合理
5. 节奏调整：优化叙述节奏
6. 文学性提升：增强文学价值和艺术性

请返回优化后的完整内容。"""}
        ]
        
        print("🔄 正在优化内容质量...")
        optimized_content = self.query_chat(optimization_messages)
        
        if optimized_content:
            print(f"🎉 中文VibeWriting故事生成完成！优化后内容长度: {len(optimized_content)} 字符，由DeepSeek Reasoner智能创作并优化")
            return [optimized_content]
        else:
            print(f"🎉 中文VibeWriting故事生成完成！内容长度: {len(novel_content)} 字符，由DeepSeek Reasoner智能创作")
        return [novel_content]

    def character_design(self, book_spec):
        """角色深度设计
        
        Parameters
        ----------
        book_spec : str
            书籍规格
            
        Returns
        -------
        str
            角色设计结果
        """
        messages = [
            {"role": "system", "content": "你是一位资深的角色设计师，擅长创造立体鲜明的小说角色。"},
            {"role": "user", "content": f"""基于以下书籍规格，请设计主要角色：

【书籍规格】
{book_spec}

【角色设计要求】
1. 主角设计：
   - 基本信息：姓名、年龄、职业、外貌特征
   - 性格特点：核心性格、优缺点、行为习惯
   - 背景故事：成长经历、重要事件、动机目标
   - 能力特长：专业技能、天赋才能、学习能力

2. 重要配角设计（2-3个）：
   - 与主角的关系定位
   - 各自的性格特色和背景
   - 在故事中的作用和价值

3. 角色关系网络：
   - 角色间的互动模式
   - 冲突与合作关系
   - 情感纽带和利益关系

4. 角色成长轨迹：
   - 初始状态描述
   - 预期的变化和成长
   - 关键转折点设计

请创建详细的角色档案，确保每个角色都有独特的个性和深度。"""}
        ]
        
        result = self.query_chat(messages)
        return result if result else "角色设计生成失败"

    def optimize_chapter_plan(self, chapter_plan, book_spec="", character_profiles=""):
        """章节计划优化
        
        Parameters
        ----------
        chapter_plan : str
            初始章节计划
        book_spec : str
            书籍规格
        character_profiles : str
            角色设计
            
        Returns
        -------
        str
            优化后的章节计划
        """
        context = f"""【书籍规格】
{book_spec}

【角色设计】
{character_profiles}

【初始章节计划】
{chapter_plan}"""
        
        messages = [
            {"role": "system", "content": "你是一位资深的故事结构师，擅长优化小说的章节安排和情节结构。"},
            {"role": "user", "content": f"""{context}

请优化章节计划：

【优化要求】
1. 结构调整：
   - 检查三幕式结构的完整性
   - 调整章节间的逻辑关系
   - 确保情节发展的合理性

2. 节奏优化：
   - 平衡紧张与缓和的节奏
   - 合理安排高潮和转折点
   - 优化悬念和伏笔的设置

3. 角色发展：
   - 确保角色成长轨迹清晰
   - 安排角色间的互动和冲突
   - 突出角色的个性特征

4. 情节完善：
   - 补充必要的情节细节
   - 加强章节间的连贯性
   - 完善冲突解决方案

请提供优化后的详细章节安排。"""}
        ]
        
        result = self.query_chat(messages)
        return result if result else "章节计划优化失败"

    def set_literary_style(self, book_spec="", character_profiles="", chapter_plan=""):
        """文学风格定调
        
        Parameters
        ----------
        book_spec : str
            书籍规格
        character_profiles : str
            角色设计
        chapter_plan : str
            章节计划
            
        Returns
        -------
        str
            文学风格指导
        """
        context = f"""【书籍规格】
{book_spec}

【角色设计】
{character_profiles}

【章节计划】
{chapter_plan}"""
        
        messages = [
            {"role": "system", "content": "你是一位文学风格顾问，擅长为不同类型的小说确定最适合的写作风格。"},
            {"role": "user", "content": f"""{context}

请确定小说的文学风格：

【风格定调要求】
1. 叙述视角：
   - 选择最适合的叙述视角（第一人称/第三人称/多视角）
   - 说明选择理由和优势

2. 语言风格：
   - 确定整体语言特色（现代/古典/诗意/朴实/幽默等）
   - 词汇选择倾向和句式特点

3. 描写重点：
   - 心理描写、环境描写、动作描写的比重
   - 各类描写的具体技巧和要求

4. 对话风格：
   - 对话的正式程度和特色
   - 不同角色的语言特点

5. 节奏控制：
   - 整体节奏的快慢安排
   - 不同场景的节奏变化

6. 情感基调：
   - 作品的主要情感色彩
   - 情感表达的深度和方式

请提供详细的文学风格指导方案。"""}
        ]
        
        result = self.query_chat(messages)
        return result if result else "文学风格定调失败"

    def generate_novel(self, book_spec="", character_profiles="", chapter_plan="", style_guide=""):
        """高质量内容生成
        
        Parameters
        ----------
        book_spec : str
            书籍规格
        character_profiles : str
            角色设计
        chapter_plan : str
            章节计划
        style_guide : str
            文学风格指导
            
        Returns
        -------
        str
            生成的小说内容
        """
        context = f"""【书籍规格】
{book_spec}

【角色设计】
{character_profiles}

【章节计划】
{chapter_plan}

【文学风格指导】
{style_guide}"""
        
        messages = [
            {"role": "system", "content": "你是一位资深的中文小说作家，擅长创作高质量的文学作品。"},
            {"role": "user", "content": f"""{context}

【创作要求】
基于以上所有设定，请开始撰写小说内容：

1. 文学性：语言优美，富有感染力，运用恰当的修辞手法
2. 可读性：情节引人入胜，节奏把握得当，悬念设置巧妙
3. 人物塑造：角色立体鲜明，性格一致，发展合理
4. 对话质量：自然流畅，符合人物身份，推动情节发展
5. 场景描写：生动细腻，营造沉浸感，调动五感体验
6. 情感深度：触动人心，引发共鸣，层次丰富
7. 结构完整：开头吸引人，中间有起伏，结尾有回味
8. 细节丰富：注重环境描写、心理描写、动作描写的平衡

请创作一部完整的、高质量的小说内容。"""}
        ]
        
        result = self.query_chat(messages)
        return result if result else "小说内容生成失败"

    def optimize_content(self, novel_content):
        """内容质量优化
        
        Parameters
        ----------
        novel_content : str
            原始小说内容
            
        Returns
        -------
        str
            优化后的内容
        """
        messages = [
            {"role": "system", "content": "你是一位专业的文学编辑，擅长润色和完善文学作品。"},
            {"role": "user", "content": f"""请对以下小说内容进行质量优化：

【原始内容】
{novel_content}

【优化要求】
1. 语言润色：提升文字的优美度和流畅性
2. 情感深化：加强情感表达的深度和感染力
3. 细节完善：补充必要的细节描写
4. 逻辑检查：确保情节逻辑合理
5. 节奏调整：优化叙述节奏
6. 文学性提升：增强文学价值和艺术性

请返回优化后的完整内容。"""}
        ]
        
        result = self.query_chat(messages)
        return result if result else novel_content  # 如果优化失败，返回原内容
