#ifndef TOOLPATH_OPAQUE_TYPES_HXX
#define TOOLPATH_OPAQUE_TYPES_HXX

#include <cstddef>
#include <cstdint>

/**
 * @file   ToolpathOpaqueTypes.hxx
 * @brief  刀轨 / CAM 侧不透明句柄与枚举（仅类型定义，无实现，用于 RAG）。
 */

enum class ToolpathLinkStrategy : std::uint8_t {
    ShortestJump = 0,
    AlongSafetyPlane,
    AlongFeedPlane,
    SpiralReorder,
    UserDefined
};

enum class LeadInOutStyle : std::uint8_t {
    None = 0,
    VerticalRamp,
    HelicalRamp,
    ProfileTangent,
    BlendArc
};

enum class CollisionCheckMode : std::uint8_t {
    Off = 0,
    HolderOnly,
    HolderAndArbor,
    FullAssembly
};

typedef void* ToolpathSessionHandle;
typedef void* CuttingToolHandle;
typedef void* StockModelHandle;

using ToolDiameterMm = double;
using SpindleSpeedRpm = std::uint32_t;
using FeedRateMmPerMin = double;

/** 刀轨段索引（文档化用别名） */
typedef std::size_t ToolpathSegmentIndex;

#endif // TOOLPATH_OPAQUE_TYPES_HXX
