# AI 服务

## DeepSeek API

使用 DeepSeek-v4-pro 模型，通过 OpenAI 兼容 API（`async openai`）调用。

配置:
- `DEEPSEEK_API_KEY`: API 密钥 (必填)
- `DEEPSEEK_BASE_URL`: API 地址，默认 `https://api.deepseek.com/v1`
- `DEEPSEEK_MODEL`: 模型，默认 `deepseek-v4-pro`
- `AI_STUDY_MAX_TOKENS` / `AI_QB_MAX_TOKENS`: 学习资料/题库生成的 token 上限
- `AI_JSON_MODE`: 是否启用 JSON 输出模式（`response_format={"type":"json_object"}`）

## 健壮性设计

- **`_parse_llm_json`**：去 markdown 围栏 → `json.loads` → 失败时转义 JSON 字符串内的未转义换行 → 再解析 → 仍失败记录原始响应。
- **重试**：`_generate_json` 最多 3 次尝试；若 API 拒绝 JSON 模式则自动回退普通调用。
- 最终失败抛出 `AI 调用失败，请稍后再试`。

## 接口

| 函数 | 说明 |
|------|------|
| `content_diff(new_text, library_texts)` | 新文档与文档库语义对比（返回 new/conflict） |
| `grammar_rewrite(text)` | 拼写/语法修正（grammar 提示词） |
| `style_rewrite(text, style_prompt)` | 按 AI 提示词（rewrite 类型）改写 |
| `generate_study_material(docs, style_prompt)` | 生成结构化学习资料（cover/chapters/pages/end + style CSS） |
| `generate_exam(docs, style_prompt)` | 生成考题（questions 数组，五种题型） |
| `evaluate_exam(...)` / `summarize_exam(...)` | 考试评价/总结 |

## 提示词

提示词存于 `backend/config/prompts.yaml`（grammar/study/exam 三类），运行时经 `PROMPTS_FILE` 可指向自定义路径；`app/prompts_config.py` 提供内置兜底（与 yaml 保持一致）。
