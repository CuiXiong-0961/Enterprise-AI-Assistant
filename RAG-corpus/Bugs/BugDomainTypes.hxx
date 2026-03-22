#ifndef BUG_DOMAIN_TYPES_HXX
#define BUG_DOMAIN_TYPES_HXX

#include <cstdint>

/**
 * @file   BugDomainTypes.hxx
 * @brief  缺陷域常用枚举与类型别名（仅声明，用于检索与 API 契约说明，无实现）。
 */

// ---------------------------------------------------------------------------
// 枚举：缺陷生命周期与定性（供 metadata / 工作流过滤）
// ---------------------------------------------------------------------------

/** 缺陷在跟踪系统中的状态 */
enum class BugStatus : std::uint8_t {
    Open = 0,
    InProgress,
    Resolved,
    Closed,
    Reopened,
    Deferred
};

/** 严重程度（示例分级，可按公司规范替换） */
enum class BugSeverity : std::uint8_t {
    Blocker = 0,
    Critical,
    Major,
    Minor,
    Trivial
};

/** 问题定性大类（与 root_cause / 分类检索对齐） */
enum class BugRootCauseCategory : std::uint16_t {
    Unknown = 0,
    LogicError,
    ConcurrencyRace,
    MemoryLeak,
    NullDereference,
    BoundaryCondition,
    NumericalInstability,
    GeometryRobustness,
    IOOrPersistence,
    Configuration,
    ThirdParty,
    Regression
};

/** 测试侧 / 开发侧描述在向量库中的角色（与 schema text_role 对应） */
enum class BugTextRole : std::uint8_t {
    TestDescription = 0,
    DevAnalysis,
    MergedNarrative
};

// ---------------------------------------------------------------------------
// typedef / using：句柄与回调（不透明指针，仅类型名检索）
// ---------------------------------------------------------------------------

typedef std::uint64_t BugRecordId;
typedef const void* BugAttachmentHandle;

using BugCommentCallback = void (*)(BugRecordId bugId, const char* markdownSnippet);
using BugStatusNotifier = void (*)(BugRecordId bugId, BugStatus newStatus);

#endif // BUG_DOMAIN_TYPES_HXX
