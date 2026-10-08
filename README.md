# Moyun

A multi-stage framework for long-form Chinese story generation, built on large language models and designed around a structured, sequential generation pipeline.

Moyun decomposes story creation into successive stages—story specification, specification refinement, chapter-level outlining, scene decomposition, and scene-by-scene composition—so that narrative coherence is maintained over full-length works. All prompts and generation logic are designed for the Chinese language, and the framework ships with a Flask-based web interface for interactive use.

The framework is derived from the [GOAT-Storytelling-Agent](https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent) architecture and adapted for Chinese-language fiction with DeepSeek Reasoner as the primary backend.

## Method

Generation proceeds through five stages:

1. **Story specification initialization** — generate genre, setting, characters, and other foundational elements from a topical prompt.
2. **Specification refinement** — enrich the specification with additional detail and consistency constraints.
3. **Chapter outline construction** — organize the story into a three-act chapter structure.
4. **Outline optimization** — refine value shifts and conflict design across chapters.
5. **Scene composition** — split chapters into scenes and generate each scene iteratively.

## Installation

```bash
git clone https://github.com/liujuncheng820/moyun.git
cd moyun
pip install -r requirements.txt
```

## Configuration

API credentials are supplied through environment variables, typically via a `.env` file that is excluded from version control:

```bash
DEEPSEEK_API_KEY=<your-deepseek-key>
```

Refer to `test_api.py` to verify connectivity after configuration.

## Usage

### Full story generation

```python
from src.agents.storytelling_agent import StoryAgent

writer = StoryAgent("deepseek", form="novel")
novel_scenes = writer.generate_story("校园青春恋爱故事")
```

### Stage-by-stage control

```python
msgs, book_spec = writer.init_book_spec("都市悬疑推理")
msgs, enhanced_spec = writer.enhance_book_spec(book_spec)
msgs, plot = writer.create_plot_chapters(enhanced_spec)
msgs, scenes = writer.split_chapters_into_scenes(plot)
```

### Web interface

```bash
python web/web_app.py
```

The interface is served at `http://localhost:5000` and provides real-time, streaming display of generated chapters through Socket.IO.

## Project Structure

```
moyun/
├── src/                     # Core package
│   ├── agents/              # Story generation agents
│   ├── core/                # Planning and prompt templates
│   ├── services/            # Generation service layer
│   ├── utils/               # Utilities and streaming processors
│   └── config/              # Configuration management
├── storytelling_agent/      # Original pipeline engine
├── web/                     # Flask web application
├── tests/                   # Test suite
├── examples/                # Example scripts
└── images/                  # Figures
```

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details. The license notice retains the original copyright of GOAT.AI, from which the underlying architecture is derived.

## Acknowledgements

- [GOAT-AI-lab](https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent) for the underlying multi-stage storytelling architecture.
- The DeepSeek team for the Reasoner model.
