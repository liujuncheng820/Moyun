"""
红楼梦文风生成器
实现多候选生成、重排序和自评回写
"""

import os
import sys
import concurrent.futures
from typing import List, Dict, Optional, Tuple
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.hongloumeng_style import hongloumeng_engine, hongloumeng_scorer
import requests


class HongloumengGenerator:
    """红楼梦文风生成器"""
    
    def __init__(self, api_key: Optional[str] = None, backend_uri: Optional[str] = None):
        """
        初始化生成器
        
        Args:
            api_key: DeepSeek API密钥
            backend_uri: API端点地址
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.backend_uri = backend_uri or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
        self.model = "deepseek-reasoner"
        
        if not self.api_key:
            raise ValueError("需要提供DeepSeek API密钥")
    
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7, 
                  max_tokens: int = 2000, timeout: int = 120) -> Optional[str]:
        """
        调用DeepSeek API
        
        Args:
            messages: 消息列表
            temperature: 采样温度
            max_tokens: 最大token数
            timeout: 超时时间
            
        Returns:
            生成的文本或None
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
            "top_p": 0.9
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
                           temperature_range: Tuple[float, float] = (0.4, 0.8)) -> List[str]:
        """
        生成多个候选文本
        
        Args:
            user_input: 用户输入
            n_candidates: 候选数量
            temperature_range: 温度范围 (min, max)
            
        Returns:
            候选文本列表
        """
        print(f"🎯 开始生成 {n_candidates} 个红楼梦风格候选...")
        
        # 生成不同的temperature值
        temperatures = [
            temperature_range[0] + (temperature_range[1] - temperature_range[0]) * i / (n_candidates - 1)
            for i in range(n_candidates)
        ]
        
        candidates = []
        messages = hongloumeng_engine.get_few_shot_messages(user_input)
        
        # 串行生成（避免并发限制）
        for i, temp in enumerate(temperatures):
            print(f"  📝 生成候选 {i+1}/{n_candidates} (temperature={temp:.2f})...")
            
            candidate = self._call_api(messages, temperature=temp, max_tokens=2000)
            if candidate:
                candidates.append(candidate)
                print(f"     ✅ 候选 {i+1} 生成成功，长度: {len(candidate)} 字符")
            else:
                print(f"     ❌ 候选 {i+1} 生成失败")
            
            # 添加短暂延迟避免API限制
            time.sleep(0.5)
        
        print(f"✅ 成功生成 {len(candidates)} 个候选")
        return candidates
    
    def rank_and_select(self, candidates: List[str], top_k: int = 1) -> List[Tuple[str, float]]:
        """
        对候选进行排序并选择最佳
        
        Args:
            candidates: 候选文本列表
            top_k: 返回前k个
            
        Returns:
            (文本, 分数) 元组列表
        """
        print(f"📊 开始对 {len(candidates)} 个候选进行风格评分...")
        
        ranked = hongloumeng_scorer.rank_candidates(candidates)
        
        # 打印评分详情
        for i, (text, score) in enumerate(ranked):
            print(f"  候选 {i+1}: 风格得分 = {score:.3f}")
            if i < top_k:
                detailed_scores = hongloumeng_scorer.calculate_score(text)
                print(f"    详细评分: {detailed_scores}")
        
        return ranked[:top_k]
    
    def self_evaluate_and_rewrite(self, content: str, max_iterations: int = 1) -> str:
        """
        自评回写
        
        Args:
            content: 原始内容
            max_iterations: 最大迭代次数
            
        Returns:
            优化后的内容
        """
        current_content = content
        
        for iteration in range(max_iterations):
            print(f"🔄 自评回写迭代 {iteration + 1}/{max_iterations}...")
            
            # 1. 自评
            eval_messages = hongloumeng_engine.get_self_evaluation_prompt(current_content)
            evaluation = self._call_api(eval_messages, temperature=0.3, max_tokens=1000)
            
            if not evaluation:
                print("  ⚠️ 自评失败，跳过回写")
                break
            
            print(f"  📋 自评结果:\n{evaluation[:200]}...")
            
            # 2. 回写
            rewrite_messages = hongloumeng_engine.get_rewrite_prompt(current_content, evaluation)
            rewritten = self._call_api(rewrite_messages, temperature=0.6, max_tokens=2000)
            
            if rewritten:
                # 比较分数
                old_score = hongloumeng_scorer.calculate_score(current_content)["总分"]
                new_score = hongloumeng_scorer.calculate_score(rewritten)["总分"]
                
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
        完整的红楼梦风格生成流程
        
        Args:
            user_input: 用户输入
            use_multi_candidate: 是否使用多候选
            n_candidates: 候选数量
            use_self_rewrite: 是否使用自评回写
            
        Returns:
            包含生成结果的字典
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
            messages = hongloumeng_engine.get_few_shot_messages(user_input)
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
            final_score = hongloumeng_scorer.calculate_score(final_content)["总分"]
            result["scores"]["final"] = final_score
            print(f"✨ 最终内容风格得分: {final_score:.3f}")
        else:
            result["final"] = selected_text
        
        return result
    
    def refine_content(self, content: str) -> str:
        """
        将任意内容改写成红楼梦风格
        
        Args:
            content: 原始内容
            
        Returns:
            改写后的内容
        """
        print("🎨 开始将内容改写成红楼梦风格...")
        
        # 使用多候选+重排序+回写的完整流程
        messages = hongloumeng_engine.get_style_refinement_prompt(content)
        
        # 生成3个改写版本
        candidates = []
        for i in range(3):
            temp = 0.5 + i * 0.15  # 0.5, 0.65, 0.8
            candidate = self._call_api(messages, temperature=temp, max_tokens=2500)
            if candidate:
                candidates.append(candidate)
            time.sleep(0.3)
        
        if not candidates:
            return content  # 改写失败，返回原文
        
        # 选择最佳
        ranked = self.rank_and_select(candidates, top_k=1)
        if ranked:
            best_text, best_score = ranked[0]
            print(f"✅ 改写完成，最佳风格得分: {best_score:.3f}")
            
            # 自评回写优化
            final = self.self_evaluate_and_rewrite(best_text)
            return final
        
        return candidates[0] if candidates else content


# 全局实例
def get_hongloumeng_generator() -> HongloumengGenerator:
    """获取红楼梦生成器实例"""
    return HongloumengGenerator()


if __name__ == "__main__":
    # 测试
    generator = get_hongloumeng_generator()
    
    test_input = "描述一个女子在花园中赏花的情景"
    result = generator.generate(test_input, use_multi_candidate=True, n_candidates=3, use_self_rewrite=True)
    
    print("\n" + "="*50)
    print("最终生成结果:")
    print("="*50)
    print(result.get("final", "生成失败"))
