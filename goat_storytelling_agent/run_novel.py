#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键生成小说示例（直接运行即可）
"""
import os
import sys

# 把当前项目加入 Python 路径，避免导入报错
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goat_storytelling_agent.storytelling_agent import StoryAgent

# 1. 动态注入配置（无需手动改 config.py）
os.environ["ENDPOINT"] = "http://localhost:8080/generate"   # 你的 OpenAI 代理地址
os.environ["HF_TOKEN"]   = "hf_your_token"                 # 留空也行，只要 tokenizer 已缓存

# 2. 初始化 Agent
writer = StoryAgent(
    backend_uri="http://localhost:8080/generate",
    form="novel"
)

# 3. 生成小说
print("🚀 开始生成小说，请稍等……")
novel_scenes = writer.generate_story("a haunted library in Prague")

# 4. 保存到文件
out_file = "generated_novel.txt"
with open(out_file, "w", encoding="utf-8") as f:
    for idx, scene in enumerate(novel_scenes, 1):
        f.write(f"\n\n--- Scene {idx} ---\n")
        f.write(scene)

print(f"✅ 小说已生成并保存到 {os.path.abspath(out_file)}")