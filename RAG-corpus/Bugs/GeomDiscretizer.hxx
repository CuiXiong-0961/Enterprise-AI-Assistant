#ifndef GEOM_DISCRETIZER_HXX
#define GEOM_DISCRETIZER_HXX

#include <vector>

struct Vec3 { double x, y, z; };

/** 曲线句柄（示例，可替换为公司内部类型） */
typedef void* CurveHandle;
/** 曲面句柄（示例） */
typedef void* SurfaceHandle;

/**
 * @brief  对曲线进行等参数离散，按参数 u 均匀采样得到点列。
 *
 * @param[in]  curve  曲线对象句柄
 * @param[in]  numPoints  采样点数量（≥2）
 *
 * @return     离散点序列，顺序沿曲线参数增加方向
 */
std::vector<Vec3> discretizeCurveByParam(CurveHandle curve, int numPoints);

/**
 * @brief  对曲面进行等参数离散，在 u、v 方向均匀划分网格。
 *
 * @param[in]  surface  曲面对象句柄
 * @param[in]  numU  u 方向采样数（≥2）
 * @param[in]  numV  v 方向采样数（≥2）
 *
 * @return     离散点序列，按 (u,v) 顺序排列（如先行 u 再行 v）
 */
std::vector<Vec3> discretizeSurfaceByParam(SurfaceHandle surface, int numU, int numV);

/**
 * @brief  在曲线参数区间 [u0, u1] 内按等参数步长采样。
 *
 * @param[in]  curve  曲线对象句柄
 * @param[in]  u0  起始参数
 * @param[in]  u1  结束参数
 * @param[in]  numPoints  采样点数量
 *
 * @return     离散点序列
 */
std::vector<Vec3> sampleCurveByParam(CurveHandle curve, double u0, double u1, int numPoints);

/**
 * @brief  根据曲率或弦高误差自适应步长对曲线离散，在弯曲大处加密。
 *
 * @param[in]  curve  曲线对象句柄
 * @param[in]  maxChordError  允许的最大弦高误差（或等效容差）
 *
 * @return     自适应离散后的点序列
 */
std::vector<Vec3> discretizeCurveAdaptive(CurveHandle curve, double maxChordError);

/**
 * @brief  按弧长等分曲线，使相邻离散点间弧长近似相等。
 *
 * @param[in]  curve  曲线对象句柄
 * @param[in]  numSegments  弧长分段数（得到的点数为 numSegments+1）
 *
 * @return     沿弧长均匀分布的离散点序列
 */
std::vector<Vec3> discretizeCurveByArcLength(CurveHandle curve, int numSegments);

/**
 * @brief  对曲面按给定弧长或弦高控制进行自适应离散。
 *
 * @param[in]  surface  曲面对象句柄
 * @param[in]  maxError  最大弦高或弧长误差容差
 *
 * @return     离散点序列（可能为三角或四边形网格顶点）
 */
std::vector<Vec3> discretizeSurfaceAdaptive(SurfaceHandle surface, double maxError);

#endif // GEOM_DISCRETIZER_HXX
