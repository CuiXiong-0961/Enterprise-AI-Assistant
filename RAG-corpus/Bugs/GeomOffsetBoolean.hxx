#ifndef GEOM_OFFSET_BOOLEAN_HXX
#define GEOM_OFFSET_BOOLEAN_HXX

#include <vector>

struct Vec3 { double x, y, z; };
/** 二维轮廓（同一高度上的点） */
typedef std::vector<Vec3> Contour2D;
/** 曲面/实体句柄（示例） */
typedef void* SolidHandle;
typedef void* SurfaceHandle;

/**
 * @brief  对二维轮廓进行等距偏置，得到向内或向外偏移后的轮廓环。
 *
 * @param[in]  contour  输入封闭轮廓（逆时针/顺时针约定由实现定义）
 * @param[in]  offset  偏置距离（正为外偏，负为内偏）
 *
 * @return     偏置后的一个或多个轮廓（可能自交需裁剪）
 */
std::vector<Contour2D> offsetContour(const Contour2D& contour, double offset);

/**
 * @brief  对曲面沿法向进行等距偏置，得到新曲面。
 *
 * @param[in]  surface  输入曲面
 * @param[in]  offset  偏置距离（正为法向正侧，负为负侧）
 *
 * @return     偏置后的曲面句柄
 */
SurfaceHandle offsetSurface(SurfaceHandle surface, double offset);

/**
 * @brief  对轮廓做布尔并集，合并多个封闭轮廓的外边界。
 *
 * @param[in]  contours  多个输入轮廓
 *
 * @return     合并后的轮廓集合（可能含多个外环）
 */
std::vector<Contour2D> contourUnion(const std::vector<Contour2D>& contours);

/**
 * @brief  对轮廓做布尔差集，从第一个轮廓中减去后续轮廓所围区域。
 *
 * @param[in]  base  被减轮廓
 * @param[in]  subtract  要减去的轮廓集合
 *
 * @return     差集后的轮廓集合
 */
std::vector<Contour2D> contourDifference(const Contour2D& base, const std::vector<Contour2D>& subtract);

/**
 * @brief  对两个实体做布尔并集（CAD 布尔加）。
 *
 * @param[in]  a  第一个实体
 * @param[in]  b  第二个实体
 *
 * @return     并集实体句柄
 */
SolidHandle solidUnion(SolidHandle a, SolidHandle b);

/**
 * @brief  对两个实体做布尔差集（CAD 布尔减）。
 *
 * @param[in]  a  被减实体
 * @param[in]  b  减去的实体
 *
 * @return     差集实体句柄
 */
SolidHandle solidDifference(SolidHandle a, SolidHandle b);

/**
 * @brief  对两个实体做布尔交集。
 *
 * @param[in]  a  第一个实体
 * @param[in]  b  第二个实体
 *
 * @return     交集实体句柄
 */
SolidHandle solidIntersection(SolidHandle a, SolidHandle b);

#endif // GEOM_OFFSET_BOOLEAN_HXX
