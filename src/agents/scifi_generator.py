"""
科幻文风生成器
实现多候选生成、重排序和自评回写
"""

import os
import sys
import time
from typing import List, Dict, Optional, Tuple
import requests

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.scifi_style import scifi_engine, scifi_scorer


class SciFiGenerator:
    """科幻文风生成器"""
    
    def __init__(self, api_key: Optional[str] = None, backend_uri: Optional[str] = None, model: str = "deepseek-reasoner"):
        """
        初始化生成器
        
        Args:
            api_key: API密钥
            backend_uri: API端点地址
            model: 模型名称
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.backend_uri = backend_uri or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        self.model = model
        
        # 如果是 OpenAI，自动调整默认 URL
        if "openai.com" in self.backend_uri or model.startswith("gpt"):
             if not self.api_key:
                 self.api_key = os.getenv("OPENAI_API_KEY")
             if "openai.com" not in self.backend_uri:
                 self.backend_uri = "https://api.openai.com/v1/chat/completions"
        
        # 如果是 Qwen，自动调整
        elif "aliyuncs.com" in self.backend_uri or "qwen" in model:
             if not self.api_key:
                 self.api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")

        if not self.api_key:
            print("⚠️ 警告: 未检测到 API Key，科幻生成器可能无法工作")
    
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7, 
                  max_tokens: int = 2000, timeout: int = 120) -> Optional[str]:
        """
        调用 API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # "top_p": 0.9 # 部分模型可能对 top_p 敏感，暂时移除默认值
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
                    
                    # 处理DeepSeek Reasoner的reasoning_content字段
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
        """
        生成多个候选文本
        """
        print(f"🎯 开始生成 {n_candidates} 个科幻风格候选...")
        
        # 生成不同的temperature值
        temperatures = [
            temperature_range[0] + (temperature_range[1] - temperature_range[0]) * i / max(1, n_candidates - 1)
            for i in range(n_candidates)
        ]
        
        candidates = []
        messages = scifi_engine.get_few_shot_messages(user_input)
        
        # 串行生成
        for i, temp in enumerate(temperatures):
            print(f"  📝 生成候选 {i+1}/{n_candidates} (temperature={temp:.2f})...")
            
            candidate = self._call_api(messages, temperature=temp, max_tokens=2000)
            if candidate:
                candidates.append(candidate)
                print(f"     ✅ 候选 {i+1} 生成成功，长度: {len(candidate)} 字符")
            else:
                print(f"     ❌ 候选 {i+1} 生成失败")
            
            time.sleep(0.5)
        
        print(f"✅ 成功生成 {len(candidates)} 个候选")
        return candidates
    
    def rank_and_select(self, candidates: List[str], top_k: int = 1) -> List[Tuple[str, float]]:
        """
        对候选进行排序并选择最佳
        """
        print(f"📊 开始对 {len(candidates)} 个候选进行风格评分...")
        
        ranked = scifi_scorer.rank_candidates(candidates)
        
        # 打印评分详情
        for i, (text, score) in enumerate(ranked):
            print(f"  候选 {i+1} (长度{len(text)}): 风格得分 = {score:.3f}")
            if i < top_k:
                detailed_scores = scifi_scorer.calculate_score(text)
                print(f"    详细评分: {detailed_scores}")
        
        return ranked[:top_k]
    
    def self_evaluate_and_rewrite(self, content: str, max_iterations: int = 1) -> str:
        """
        自评回写
        """
        current_content = content
        
        for iteration in range(max_iterations):
            print(f"🔄 自评回写迭代 {iteration + 1}/{max_iterations}...")
            
            # 1. 自评
            eval_messages = scifi_engine.get_self_evaluation_prompt(current_content)
            evaluation = self._call_api(eval_messages, temperature=0.3, max_tokens=1000)
            
            if not evaluation:
                print("  ⚠️ 自评失败，跳过回写")
                break
            
            print(f"  📋 自评结果:\n{evaluation[:200]}...")
            
            # 2. 回写
            rewrite_messages = scifi_engine.get_rewrite_prompt(current_content, evaluation)
            rewritten = self._call_api(rewrite_messages, temperature=0.6, max_tokens=2000)
            
            if rewritten:
                # 比较分数
                old_score = scifi_scorer.calculate_score(current_content)["总分"]
                new_score = scifi_scorer.calculate_score(rewritten)["总分"]
                
                if new_score > old_score:
                    print(f"  ✅ 回写成功，风格得分: {old_score:.3f} -> {new_score:.3f}")
                    current_content = rewritten
                else:
                    print(f"  ⚠️ 回写未提升，保持原内容 (得分: {old_score:.3f} vs {new_score:.3f})")
                    break
            else:
                print("  ⚠️ 回写失败")
                break
        
        return current_content
    
    def generate(self, user_input: str, use_multi_candidate: bool = True,
                 n_candidates: int = 3, use_self_rewrite: bool = True) -> Dict:
        """
        完整的科幻风格生成流程
        """
        result = {
            "input": user_input,
            "candidates": [],
            "selected": None,
            "final": None,
            "scores": {}
        }
        
        # 1. 生成候选
        if use_multi_candidate:
            candidates = self.generate_candidates(user_input, n_candidates=n_candidates)
        else:
            # 单候选生成
            messages = scifi_engine.get_few_shot_messages(user_input)
            candidate = self._call_api(messages, temperature=0.6, max_tokens=2000)
            candidates = [candidate] if candidate else []
        
        if not candidates:
            return {"error": "生成失败，未获得任何候选"}
        
        result["candidates"] = candidates
        
        # 2. 重排序选择
        ranked = self.rank_and_select(candidates, top_k=1)
        if ranked:
            selected_text, selected_score = ranked[0]
            result["selected"] = selected_text
            result["scores"]["selected"] = selected_score
            print(f"🏆 最佳候选风格得分: {selected_score:.3f}")
        else:
            return {"error": "评分失败"}
        
        # 3. 自评回写
        if use_self_rewrite:
            final_content = self.self_evaluate_and_rewrite(selected_text)
            result["final"] = final_content
            final_score = scifi_scorer.calculate_score(final_content)["总分"]
            result["scores"]["final"] = final_score
            print(f"✨ 最终内容风格得分: {final_score:.3f}")
        else:
            result["final"] = selected_text
        
        return result


def get_scifi_generator(api_key=None, backend_uri=None, model="deepseek-reasoner"):
    """获取生成器实例"""
    return SciFiGenerator(api_key, backend_uri, model)
