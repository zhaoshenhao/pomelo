# AI 服务

## DeepSeek API

使用 DeepSeek-v4-pro 模型，通过 OpenAI 兼容 API 调用。

配置:
- `DEEPSEEK_API_KEY`: API 密钥 (必填)
- `DEEPSEEK_BASE_URL`: API 地址，默认 `https://api.deepseek.com/v1`

## 接口

### spell_check(text) → list[Suggestion]

拼写和语法检查，返回问题列表。

### semantic_diff(new_text, existing_texts) → DiffReport

新增文档与文档库的语义对比分析。

返回:
- `new_content`: 全新内容
- `conflict_content`: 冲突内容
- `duplicate_content`: 重复内容

### rewrite(text, prompt) → str

按照预定义改写风格的 prompt 改写内容。
