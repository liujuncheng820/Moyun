# 项目结构说明

## 目录结构

```
GOAT-Storytelling-Agent/
├── src/                    # 核心源代码
│   ├── agents/            # 智能代理模块
│   │   ├── storytelling_agent.py    # 主要故事生成代理
│   │   └── refactored_agent.py      # 重构版代理
│   ├── core/              # 核心组件
│   │   ├── plan.py        # 故事规划数据结构
│   │   └── prompts.py     # 提示词模板
│   ├── services/          # 服务层
│   │   └── services.py    # 故事生成服务
│   ├── utils/             # 工具模块
│   │   ├── utils.py       # 通用工具函数
│   │   └── streaming_processor.py  # 流式处理器
│   └── config/            # 配置模块
│       └── config.py      # 配置管理
├── web/                   # Web应用
│   ├── web_app.py         # Flask主应用
│   ├── templates/         # HTML模板
│   └── static/            # 静态资源
├── tests/                 # 测试代码
│   ├── test_deepseek_api.py        # API连接测试
│   └── test_optimized_agent.py     # 代理功能测试
├── examples/              # 使用示例
│   ├── run_novel.py       # 小说生成示例
│   ├── run_openai_proxy.py         # OpenAI代理示例
│   └── run_optimized_demo.py       # 优化版演示
├── docs/                  # 文档和配置
│   ├── requirements.txt   # 核心依赖
│   └── requirements_web.txt        # Web依赖
└── images/                # 图片资源
```

## 模块说明

### src/ - 核心源代码
- **agents/**: 包含各种智能故事生成代理的实现
- **core/**: 核心数据结构和组件，如故事规划、提示词等
- **services/**: 业务逻辑服务层，处理故事生成的具体流程
- **utils/**: 通用工具和辅助功能
- **config/**: 配置管理模块

### web/ - Web应用
- Flask应用和前端资源，提供Web界面交互

### tests/ - 测试代码
- 包含API测试和功能测试用例

### examples/ - 使用示例
- 各种使用场景的示例代码和演示程序

### docs/ - 文档
- 项目文档和依赖配置文件

## 导入规范

使用新的模块结构时，请按以下方式导入：

```python
# 导入核心代理
from src.agents.storytelling_agent import StoryAgent
from src.agents.refactored_agent import RefactoredStoryAgent

# 导入核心组件
from src.core.plan import Plan
from src.core import prompts

# 导入服务
from src.services.services import StoryGenerationService

# 导入工具
from src.utils.utils import *
from src.utils.streaming_processor import StreamingProcessor
```

## 重构优势

1. **清晰的模块分离**: 按功能将代码组织到不同目录
2. **更好的可维护性**: 每个模块职责单一，便于维护和扩展
3. **标准化结构**: 遵循Python项目的最佳实践
4. **易于测试**: 测试代码与业务代码分离
5. **文档完善**: 每个模块都有清晰的说明和示例