from storytelling_agent.storytelling_agent import StoryAgent
from storytelling_agent import config

agent = StoryAgent(
    backend_uri=config.BACKEND_URI,
    backend="deepseek",
    request_timeout=60,
    max_tokens=500,
    extra_options={"temperature": 0.8}
)

topic = "一个孤独的宇航员在外太空旅行，发现了外星文明。"
story = agent.generate_story(topic)

print("\n".join(story))
