#ifndef GEOMETRY_ENUMS_HXX
#define GEOMETRY_ENUMS_HXX

#include <cstdint>

/**
 * @file   GeometryEnums.hxx
 * @brief  几何与网格相关枚举、类型别名（仅声明，供语义检索，无实现）。
 */

/** 参数曲线/曲面的参数域方向 */
enum class ParamDirection : std::uint8_t {
    U = 0,
    V,
    UV
};

/** 曲线绕向（用于布尔、偏移方向约定） */
enum class CurveWinding : std::uint8_t {
    Unknown = 0,
    Clockwise,
    CounterClockwise
};

/** 几何连续性阶次（CAD/CAE 常用表述） */
enum class GeometricContinuity : std::uint8_t {
    CNeg1_Discontinuous = 0,
    C0_Positional,
    C1_Tangential,
    C2_Curvature,
    G1_Geometric,
    G2_Geometric
};

/** 网格单元类型（体/面） */
enum class MeshElementKind : std::uint8_t {
    Triangle = 0,
    Quad,
    Tetra,
    Hexa,
    Pyramid,
    Wedge,
    Mixed
};

/** 离散质量标记（用于 Bug 复现与回归场景检索） */
enum class DiscretizationQualityFlag : std::uint16_t {
    None = 0,
    SelfIntersectionSuspected = 1 << 0,
    InvertedElement = 1 << 1,
    SliverElement = 1 << 2,
    ParamSingularity = 1 << 3,
    ToleranceExceeded = 1 << 4
};

typedef std::uint32_t MeshFaceId;
typedef std::uint32_t MeshSolidId;

using ScalarParam = double;

/** 曲面参数对（仅聚合字段，无成员函数实现） */
struct ParameterPair {
    ScalarParam u;
    ScalarParam v;
};

#endif // GEOMETRY_ENUMS_HXX
