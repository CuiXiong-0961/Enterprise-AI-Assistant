"""
示例脚本：演示如何按**变体键**加载各子 Agent 的分层提示词并组装。

运行方式（在项目根目录 Enterprise-AI-Assistant 下）::

    python prompt/test.py

或::

    python -m prompt.test
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from prompt.assembler import (  # noqa: E402
    PROMPT_ROOT,
    CppHeaderPromptAssembler,
    TrainingPromptAssembler,
    get_assembler,
)
from prompt.design_document import layers as design_document_layers  # noqa: E402


def _preview(text: str, max_chars: int = 400) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [已截断]"


def example_factory_default_variants() -> None:
    """默认变体：由各 ``layers.DEFAULT_VARIANT_KEYS`` 决定。"""
    print("=== 示例 1：默认变体 assemble() ===\n")
    asm = get_assembler("cpp_header")
    print(_preview(asm.assemble()))
    print()


def example_ab_partial_layer_override() -> None:
    """A/B：只替换某一层的变体键（其余层走默认）。"""
    print("=== 示例 2：A/B — 仅替换 instruction 为 task_decomposition_light ===\n")
    asm = CppHeaderPromptAssembler()
    text = asm.assemble(
        variants={"instruction": "task_decomposition_light"},
        include_examples=False,
    )
    print(_preview(text, max_chars=500))
    print()


def example_load_layer_explicit_variant() -> None:
    """直接按变体名读取单层。"""
    print("=== 示例 3：load_layer(..., variant='json_minimal_fields') ===\n")
    asm = CppHeaderPromptAssembler()
    print(_preview(asm.load_layer("output", variant="json_minimal_fields")))
    print()


def example_list_keys_for_experiment() -> None:
    """实验前枚举某层全部变体名。"""
    print("=== 示例 4：list_variant_keys('instruction') — cpp_header ===\n")
    asm = CppHeaderPromptAssembler()
    print(asm.list_variant_keys("instruction"))
    print()


def example_direct_layers_dict_access() -> None:
    """与组装器等价：直接从 ``layers`` 模块读 ``LAYERS`` 字典。"""
    print("=== 示例 5：prompt.design_document.layers.LAYERS['system'] ===\n")
    for key, text in design_document_layers.LAYERS["system"].items():
        print(f"[{key}] {_preview(text, max_chars=120)}")
    print()


def example_custom_separator() -> None:
    print("=== 示例 6：自定义 separator ===\n")
    asm = TrainingPromptAssembler()
    merged = asm.assemble(separator="\n\n<<<NEXT>>>\n\n", include_examples=False)
    print(_preview(merged, max_chars=350))
    print()


def example_prompt_root() -> None:
    print("=== 示例 7：PROMPT_ROOT ===\n")
    print(PROMPT_ROOT)
    print()


def main() -> None:
    example_factory_default_variants()
    example_ab_partial_layer_override()
    example_load_layer_explicit_variant()
    example_list_keys_for_experiment()
    example_direct_layers_dict_access()
    example_custom_separator()
    example_prompt_root()


if __name__ == "__main__":
    main()
