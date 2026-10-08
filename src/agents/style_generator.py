"""
通用风格生成器
支持不同风格引擎的注入，避免重复代码
"""

import os
import sys
import time
from typing import List, Dict, Optional, Tuple, Any
import requests

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class StyleGenerator:
    """通用风格生成器"""
    
    def __init__(self, style_engine, scorer, style_name: str, api_key: Optional[str] = None, backend_uri: Optional[str] = None, model: str = "deepseek-reasoner"):
        """
        初始化生成器
        
        Args:
            style_engine: 风格引擎实例 (需实现 get_few_shot_messages, get_self_evaluation_prompt, get_rewrite_prompt)
            scorer: 评分器实例 (需实现 rank_candidates, calculate_score)
            style_name: 风格名称（用于日志）
            api_key: API密钥
            backend_uri: API端点地址
            model: 模型名称
        """
        self.style_engine = style_engine
        self.scorer = scorer
        self.style_name = style_name
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.backend_uri = backend_uri or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        self.model = model
        
        # 自动适配 OpenAI / Qwen
        if "openai.com" in self.backend_uri or model.startswith("gpt"):
             if not self.api_key:
                 self.api_key = os.getenv("OPENAI_API_KEY")
             if "openai.com" not in self.backend_uri:
                 self.backend_uri = "https://api.openai.com/v1/chat/completions"
        elif "aliyuncs.com" in self.backend_uri or "qwen" in model:
             if not self.api_key:
                 self.api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")

        if not self.api_key:
            print(f"⚠️ 警告: 未检测到 API Key，{style_name}生成器可能无法工作")
    
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7, 
                  max_tokens: int = 2000, timeout: int = 120) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.backend_uri,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0]['message']
                    content = message.get('content', '')
                    if not content and 'reasoning_content' in message:
                        content = message['reasoning_content']
                    return content
            else:
                print(f"API调用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"API调用异常: {e}")
            return None
    
    def generate_candidates(self, user_input: str, n_candidates: int = 3,
                           temperature_range: Tuple[float, float] = (0.5, 0.9)) -> List[str]:
        print(f"🎯 [{self.style_name}] 开始生成 {n_candidates} 个候选...")
        
        temperatures = [
            temperature_range[0] + (temperature_range[1] - temperature_range[0]) * i / max(1, n_candidates - 1)
            for i in range(n_candidates)
        ]
        
        candidates = []
        messages = self.style_engine.get_few_shot_messages(user_input)
        
        for i, temp in enumerate(temperatures):
            print(f"  📝 生成候选 {i+1}/{n_candidates} (temperature={temp:.2f})...")
            candidate = self._call_api(messages, temperature=temp, max_tokens=2000)
            if candidate:
                candidates.append(candidate)
                print(f"     ✅ 候选 {i+1} 生成成功，长度: {len(candidate)}")
            else:
                print(f"     ❌ 候选 {i+1} 生成失败")
            time.sleep(0.5)
        
        return candidates
    
    def rank_and_select(self, candidates: List[str], top_k: int = 1) -> List[Tuple[str, float]]:
        print(f"📊 [{self.style_name}] 开始对 {len(candidates)} 个候选进行评分...")
        ranked = self.scorer.rank_candidates(candidates)
        
        for i, (text, score) in enumerate(ranked):
            print(f"  候选 {i+1}: 得分 = {score:.3f}")
            if i < top_k:
                print(f"    详细评分: {self.scorer.calculate_score(text)}")
        
        return ranked[:top_k]
    
    def self_evaluate_and_rewrite(self, content: str, max_iterations: int = 1) -> str:
        current_content = content
        for iteration in range(max_iterations):
            print(f"🔄 [{self.style_name}] 自评回写迭代 {iteration + 1}/{max_iterations}...")
            
            eval_messages = self.style_engine.get_self_evaluation_prompt(current_content)
            evaluation = self._call_api(eval_messages, temperature=0.3, max_tokens=1000)
            
            if not evaluation:
                break
            
            rewrite_messages = self.style_engine.get_rewrite_prompt(current_content, evaluation)
            rewritten = self._call_api(rewrite_messages, temperature=0.6, max_tokens=2000)
            
            if rewritten:
                old_score = self.scorer.calculate_score(current_content)["总分"]
                new_score = self.scorer.calculate_score(rewritten)["总分"]
                
                if new_score > old_score:
                    print(f"  ✅ 回写成功，得分: {old_score:.3f} -> {new_score:.3f}")
                    current_content = rewritten
                else:
                    print(f"  ⚠️ 回写未提升 (得分: {old_score:.3f} vs {new_score:.3f})")
                    break
            else:
                break
        
        return current_content
    
    def generate(self, user_input: str, use_multi_candidate: bool = True,
                 n_candidates: int = 3, use_self_rewrite: bool = True) -> Dict:
        result = {"input": user_input, "candidates": [], "selected": None, "final": None, "scores": {}}
        
        # 1. 生成
        if use_multi_candidate:
            candidates = self.generate_candidates(user_input, n_candidates=n_candidates)
        else:
            messages = self.style_engine.get_few_shot_messages(user_input)
            candidate = self._call_api(messages, temperature=0.6, max_tokens=2000)
            candidates = [candidate] if candidate else []
        
        if not candidates:
            return {"error": "生成失败"}
        
        result["candidates"] = candidates
        
        # 2. 排序
        ranked = self.rank_and_select(candidates, top_k=1)
        if ranked:
            selected_text, selected_score = ranked[0]
            result["selected"] = selected_text
            result["scores"]["selected"] = selected_score
        else:
            return {"error": "评分失败"}
        
        # 3. 回写
        if use_self_rewrite:
            final_content = self.self_evaluate_and_rewrite(selected_text)
            result["final"] = final_content
            result["scores"]["final"] = self.scorer.calculate_score(final_content)["总分"]
        else:
            result["final"] = selected_text
        
        return result

# 工厂函数
def get_style_generator(style_type: str, api_key=None, backend_uri=None, model="deepseek-reasoner"):
    if style_type == "romance":
        from src.core.romance_style import romance_engine, romance_scorer
        return StyleGenerator(romance_engine, romance_scorer, "言情文风", api_key, backend_uri, model)
    elif style_type == "mystery":
        from src.core.mystery_style import mystery_engine, mystery_scorer
        return StyleGenerator(mystery_engine, mystery_scorer, "悬疑文风", api_key, backend_uri, model)
    else:
        raise ValueError(f"Unknown style type: {style_type}")
