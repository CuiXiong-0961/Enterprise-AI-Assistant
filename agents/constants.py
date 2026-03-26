"""Agent 流水线常量：意图标签与关键词表。"""

from __future__ import annotations

# 与 process.md 五类意图对应的内部标签（供路由与 LLM 分类统一使用）
INTENT_DESIGN_DOC = "design_doc"
INTENT_CPP_QUERY = "cpp_query"
INTENT_BUG_QUERY = "bug_query"
INTENT_POLICY_QUERY = "policy_query"
INTENT_SMALLTALK = "smalltalk"

# 关键词分类：命中即加分，分值最高者胜出；平局则交 LLM 或启发式兜底
KEYWORD_WEIGHTS: dict[str, dict[str, int]] = {
    INTENT_CPP_QUERY: {
        "头文件": 3,
        "hpp": 2,
        "hxx": 2,
        "cpp": 2,
        "struct": 2,
        "enum": 2,
        "template": 2,
        "namespace": 2,
        "include": 1,
        "声明": 2,
        "函数": 2,
        "api": 2,
        "类": 1,
    },
    INTENT_DESIGN_DOC: {
        "设计": 2,
        "培训": 3,
        "教程": 2,
        "文档": 1,
        "ppt": 2,
        "课件": 2,
        "cam": 3,
        "加工": 2,
        "刀路": 2,
        "后处理": 2,
        "nc": 2,
        "数控": 2,
        "五轴": 2,
        "铣削": 2,
        "车铣": 2,
        "夹具": 2,
        "装夹": 2,
    },
    INTENT_BUG_QUERY: {
        "bug": 3,
        "缺陷": 3,
        "issue": 2,
        "jira": 2,
        "复现": 2,
    },
    INTENT_POLICY_QUERY: {
        "行政": 2,
        "条例": 3,
        "制度": 2,
        "规章": 2,
        "考勤": 2,
        "请假": 1,
    },
    INTENT_SMALLTALK: {
        "你好": 2,
        "谢谢": 1,
        "再见": 1,
        "聊天": 2,
    },
}

NOT_IMPLEMENTED_REPLY = (
    "该能力暂未开放。当前仅支持 **C++ 头文件 / 实现相关查询**。\n\n"
    "后续将开放：设计或培训资料、Bug、行政条例等。"
)
