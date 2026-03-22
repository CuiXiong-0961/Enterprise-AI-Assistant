"""提示词工程：分层变体（layers.py）与各子 Agent 组装。"""

from .assembler import (
    PROMPT_ROOT,
    AdministrativePromptAssembler,
    AgentName,
    CppHeaderPromptAssembler,
    DesignDocumentPromptAssembler,
    LayerName,
    LayerVariantOverrides,
    PromptAssembler,
    TrainingPromptAssembler,
    get_assembler,
)

__all__ = [
    "PROMPT_ROOT",
    "AgentName",
    "LayerName",
    "LayerVariantOverrides",
    "PromptAssembler",
    "CppHeaderPromptAssembler",
    "DesignDocumentPromptAssembler",
    "TrainingPromptAssembler",
    "AdministrativePromptAssembler",
    "get_assembler",
]
