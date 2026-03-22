# `prompt` 包说明

各子 Agent 的提示词存放在 **`prompt/<子Agent>/layers.py`** 中，不再使用分散的 `.md` 文件。每个 `layers.py` 暴露：

| 名称 | 含义 |
|------|------|
| `LAYERS` | 嵌套字典：`"system"` / `"instruction"` / `"output"` / `"examples"` → **变体键**（语义化字符串）→ 提示词正文 |
| `DEFAULT_VARIANT_KEYS` | 每一层默认选用的变体键，供常规线上流量与基线实验 |

变体键使用**功能描述**命名（例如 `task_decomposition_light`、`json_minimal_fields`），避免 `v1` / `v2` 这类无含义编号。

---

## A/B 实验用法

- **只改某一层**：`PromptAssembler(...).assemble(variants={"instruction": "task_decomposition_light"})`，未出现的层仍用 `DEFAULT_VARIANT_KEYS`。
- **枚举可选变体**：`assembler.list_variant_keys("output")`。
- **直接访问字典**（脚本或配置）：`from prompt.cpp_header.layers import LAYERS` → `LAYERS["instruction"]["task_decomposition_standard"]`。

若某层变体正文为空字符串（如 `few_shot_empty_placeholder`），`assemble(include_examples=True)` 时仍会跳过该层拼接，不占位。

---

## `prompt/test.py`

演示默认组装、单层变体覆盖、列出变体键、直接读 `LAYERS`。在项目根目录执行：

```bash
python prompt/test.py
```

或 `python -m prompt.test`。

---

## 与 `assembler` 的对应关系

| 能力 | API |
|------|-----|
| 选子 Agent | `get_assembler("cpp_header" \| …)` 或各 `*PromptAssembler()` |
| 默认全量拼接 | `assemble()` |
| A/B 覆盖部分层 | `assemble(variants={"instruction": "…", "output": "…"})` |
| 单层 | `load_layer("instruction")` 或 `load_layer("output", variant="json_minimal_fields")` |
| 根路径 | `PROMPT_ROOT`（`prompt` 目录，用于日志或资源定位） |

子 Agent 目录：`cpp_header`、`design_document`、`training`、`administrative`。
