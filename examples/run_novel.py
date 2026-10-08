#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
中文VibeWriting - 基于DeepSeek Reasoner的智能小说生成器
一键生成小说示例（直接运行即可）
"""
import os
import sys

# 把当前项目加入 Python 路径，避免导入报错
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.storytelling_agent import StoryAgent

# 1. 动态注入配置（推荐使用DeepSeek Reasoner）
os.environ["ENDPOINT"] = "https://api.deepseek.com/chat/completions"  # DeepSeek API地址
os.environ["HF_TOKEN"]   = "hf_your_token"                            # 留空也行，只要 tokenizer 已缓存

# 2. 初始化 DeepSeek Reasoner Agent
writer = StoryAgent(
    backend_uri="https://api.deepseek.com/chat/completions",
    backend="deepseek",  # 使用DeepSeek Reasoner后端
    form="novel"
)

# 3. 使用DeepSeek Reasoner生成小说
print("🚀 开始使用DeepSeek Reasoner生成中文VibeWriting小说，请稍等……")
novel_scenes = writer.generate_story("请用中文写一篇都市情感小说，故事发生在现代都市里")

# 4. 保存到文件
out_file = "generated_novel.txt"
with open(out_file, "w", encoding="utf-8") as f:
    for idx, scene in enumerate(novel_scenes, 1):
        f.write(f"\n\n--- Scene {idx} ---\n")
        f.write(scene)

print(f"✅ 小说已生成并保存到 {os.path.abspath(out_file)}")