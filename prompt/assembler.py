"""分层提示词组装：从各子 Agent 的 ``layers.py`` 按变体键加载（支持 A/B）。"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Literal, Mapping

LayerName = Literal["system", "instruction", "output", "examples"]
LayerVariantOverrides = Mapping[LayerName, str]

PROMPT_ROOT = Path(__file__).resolve().parent

AgentName = Literal[
    "cpp_header",
    "design_document",
    "training",
    "administrative",
]


class PromptAssembler:
    """
    从 ``prompt/<agent>/layers.py`` 读取 ``LAYERS`` 与 ``DEFAULT_VARIANT_KEYS``，
    按层选择变体名（有意义的字符串，如 ``task_decomposition_standard``），再拼接为完整提示词。
    """

    def __init__(self, agent: str) -> None:
        self._agent = agent
        self._layers_mod: Any = importlib.import_module(f"prompt.{agent}.layers")

    def layers_module(self) -> Any:
        """底层 ``layers`` 模块，便于实验脚本直接读 ``LAYERS`` / ``DEFAULT_VARIANT_KEYS``。"""
        return self._layers_mod

    def _variant_key(
        self,
        layer: LayerName,
        overrides: LayerVariantOverrides | None,
    ) -> str:
        defaults: dict[str, str] = self._layers_mod.DEFAULT_VARIANT_KEYS
        if overrides and layer in overrides:
            return overrides[layer]
        return defaults[layer]

    def list_variant_keys(self, layer: LayerName) -> list[str]:
        layers: dict[str, dict[str, str]] = self._layers_mod.LAYERS
        return list(layers[layer].keys())

    def load_layer(
        self,
        layer: LayerName,
        variant: str | None = None,
        *,
        variants: LayerVariantOverrides | None = None,
    ) -> str:
        """加载单层文本。``variant`` 与 ``variants`` 同时存在时，``variant`` 优先。"""
        layers: dict[str, dict[str, str]] = self._layers_mod.LAYERS
        key = variant if variant is not None else self._variant_key(layer, variants)
        table = layers[layer]
        if key not in table:
            raise KeyError(
                f"prompt.{self._agent}.layers: 层 {layer!r} 无变体 {key!r}；"
                f"可用: {list(table.keys())}",
            )
        return table[key].strip()

    def assemble(
        self,
        *,
        variants: LayerVariantOverrides | None = None,
        include_examples: bool = True,
        separator: str = "\n\n---\n\n",
    ) -> str:
        parts: list[str] = []
        for layer in ("system", "instruction", "output"):
            text = self.load_layer(layer, variants=variants)
            if text:
                parts.append(text)
        if include_examples:
            ex = self.load_layer("examples", variants=variants)
            if ex:
                parts.append(ex)
        return separator.join(parts)


class CppHeaderPromptAssembler(PromptAssembler):
    """子 Agent：C++ 头文件声明 / API 语义检索（仅头文件，不涉及实现）。"""

    def __init__(self) -> None:
        super().__init__("cpp_header")


class DesignDocumentPromptAssembler(PromptAssembler):
    """子 Agent：设计文档与技术知识检索。"""

    def __init__(self) -> None:
        super().__init__("design_document")


class TrainingPromptAssembler(PromptAssembler):
    """子 Agent：培训内容检索与答疑。"""

    def __init__(self) -> None:
        super().__init__("training")


class AdministrativePromptAssembler(PromptAssembler):
    """子 Agent：行政制度与组织信息查询。"""

    def __init__(self) -> None:
        super().__init__("administrative")


def get_assembler(agent: AgentName) -> PromptAssembler:
    mapping: dict[str, type[PromptAssembler]] = {
        "cpp_header": CppHeaderPromptAssembler,
        "design_document": DesignDocumentPromptAssembler,
        "training": TrainingPromptAssembler,
        "administrative": AdministrativePromptAssembler,
    }
    return mapping[agent]()
