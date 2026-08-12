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

按照 AI 提示词（rewrite 类型）的 prompt 改写内容。

### generate_study_material(docs, style_prompt) → dict

根据文档内容和风格提示词生成结构化学习资料。返回包含 cover/chapters/pages/end 的 JSON 字典，后端据此渲染独立 HTML/txt 页面。
