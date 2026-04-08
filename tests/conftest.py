import os

# 确保测试不需要真实 API key（集成测试除外）
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
