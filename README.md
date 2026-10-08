# 中文VibeWriting - 基于DeepSeek Reasoner的智能小说生成器

🚀 **由DeepSeek Reasoner驱动的中文小说创作助手**

一个专为中文小说创作设计的智能写作工具，采用DeepSeek Reasoner作为核心AI引擎，提供专业级的故事生成能力和现代化的Web界面。

## ✨ 核心特性

- **🧠 DeepSeek Reasoner驱动**：采用最新的DeepSeek Reasoner模型，具备强大的中文理解和创作能力
- **📚 智能故事架构**：从主题到章节，从大纲到场景，层层递进的故事构建
- **🎨 现代化界面**：专业的Web界面，支持实时交互和内容展示
- **⚡ 实时生成**：WebSocket技术支持，实时对话和内容流式生成
- **📱 响应式设计**：完美适配桌面和移动设备

## 🎯 项目亮点

本项目基于GOAT-Storytelling-Agent架构，专门针对中文小说创作进行了深度优化：

- **中文优化**：所有提示词和生成逻辑专为中文语境设计
- **DeepSeek集成**：深度集成DeepSeek Reasoner API，发挥其推理优势
- **故事连贯性**：多阶段生成流程确保长篇小说的逻辑一致性
- **用户友好**：简洁直观的操作界面，支持多种创作模式

## 🚀 快速开始

### 环境配置
```bash
# 克隆项目
git clone https://github.com/your-username/chinese-vibewriting.git
cd chinese-vibewriting

# 安装依赖
pip install -r requirements_web.txt

# 配置DeepSeek API
# 在 goat_storytelling_agent/config.py 中设置您的DeepSeek API密钥
```

### 启动应用
```bash
# 启动Web应用
python web_app.py
```

访问 http://localhost:5000 开始您的创作之旅！

## 🔧 DeepSeek Reasoner配置

本项目专门为DeepSeek Reasoner进行了优化配置：

1. **API配置**：在`config.py`中设置DeepSeek API端点
2. **推理优化**：利用DeepSeek的推理能力进行故事逻辑构建
3. **中文特化**：针对中文语境的提示词工程

---

## 📖 技术架构说明

基于GOAT-Storytelling-Agent的多阶段生成架构，结合DeepSeek Reasoner的强大推理能力：

### 🎯 DeepSeek Reasoner生成流程

本项目采用DeepSeek Reasoner的强大推理能力，实现多阶段智能创作：

1. **📋 故事规格初始化** - 基于主题生成类型、背景、人物等基础设定
2. **🔍 规格增强优化** - 利用DeepSeek的推理能力丰富故事细节
3. **📖 章节大纲创建** - 构建三幕式故事结构
4. **✨ 大纲深度优化** - 优化故事价值变化和冲突设计
5. **🎬 场景细分规划** - 将章节分解为具体可执行的场景
6. **✍️ 逐场景创作** - 生成高质量的场景内容

### 💻 使用示例

#### 完整故事生成（推荐）
```python
from src.agents.storytelling_agent import StoryAgent

# 初始化DeepSeek Reasoner驱动的故事代理
writer = StoryAgent('deepseek', form='novel')
novel_scenes = writer.generate_story('校园青春恋爱故事')
```

#### 分步骤创作控制
```python
# 1. 初始化故事设定
msgs, book_spec = writer.init_book_spec('都市悬疑推理')

# 2. DeepSeek增强故事规格
msgs, enhanced_spec = writer.enhance_book_spec(book_spec)

# 3. 创建章节大纲
msgs, plot = writer.create_plot_chapters(enhanced_spec)

# 4. 生成具体场景
msgs, scenes = writer.split_chapters_into_scenes(plot)
```

## 🌟 DeepSeek Reasoner优势

相比传统的故事生成工具，本项目充分发挥了DeepSeek Reasoner的独特优势：

- **🧠 强大推理能力**：DeepSeek Reasoner在逻辑推理方面表现卓越，能够构建更加连贯的故事情节
- **🎯 中文语境理解**：针对中文文学创作的语言特点进行了深度优化
- **📈 质量一致性**：多阶段验证确保长篇作品的质量稳定性
- **⚡ 高效生成**：优化的API调用策略，提供流畅的创作体验

## 📁 项目结构

```
chinese-vibewriting/
├── goat_storytelling_agent/     # 核心AI引擎
│   ├── config.py               # DeepSeek API配置
│   ├── storytelling_agent.py   # 主要生成逻辑
│   ├── prompts.py              # 中文提示词模板
│   └── ...
├── templates/                   # Web界面模板
├── static/                     # 前端资源
├── web_app.py                  # Flask Web应用
└── requirements_web.txt        # 项目依赖
```

## 🤝 贡献指南

欢迎为中文VibeWriting项目贡献代码！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目基于MIT许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 感谢 [GOAT-AI-lab](https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent) 提供的优秀基础架构
- 感谢 DeepSeek 团队开发的强大Reasoner模型
- 感谢所有为中文AI创作工具发展做出贡献的开发者们

---

**开始您的AI创作之旅，让DeepSeek Reasoner成为您的写作伙伴！** ✨
