#ifndef GEOM_FITTING_HXX
#define GEOM_FITTING_HXX

#include <vector>

struct Vec3 { double x, y, z; };

/** 直线拟合结果：点 + 方向（单位向量） */
struct LineFitResult {
    Vec3 point;
    Vec3 direction;
};
/** 圆/圆弧拟合结果：圆心、法向、半径 */
struct CircleFitResult {
    Vec3 center;
    Vec3 normal;
    double radius;
};
/** NURBS 曲线句柄（示例） */
typedef void* NURBSCurveHandle;

/**
 * @brief  用最小二乘法将点云拟合成一条直线。
 *
 * @param[in]  points  输入点云
 *
 * @return     拟合直线上的点和单位方向向量
 */
LineFitResult fitLine(const std::vector<Vec3>& points);

/**
 * @brief  用最小二乘法将点云拟合成圆（三维空间中的圆，带法向）。
 *
 * @param[in]  points  输入点云（应近似共面）
 *
 * @return     圆心、圆所在平面法向和半径
 */
CircleFitResult fitCircle(const std::vector<Vec3>& points);

/**
 * @brief  将点云拟合成圆弧段（圆 + 起始/结束角度或参数范围）。
 *
 * @param[in]  points  输入点云
 *
 * @return     圆心、法向、半径；若需弧段范围可由扩展结构或出参提供
 */
CircleFitResult fitArc(const std::vector<Vec3>& points);

/**
 * @brief  用最小二乘将点云拟合成 NURBS 曲线。
 *
 * @param[in]  points  输入点云
 * @param[in]  degree  曲线次数
 * @param[in]  numControlPoints  控制点数量
 *
 * @return     拟合得到的 NURBS 曲线句柄
 */
NURBSCurveHandle fitNURBS(const std::vector<Vec3>& points, int degree, int numControlPoints);

/**
 * @brief  通用最小二乘拟合接口，用于平面等几何的拟合。
 *
 * @param[in]  points  输入点云
 *
 * @return     拟合残差平方和（或 0 表示成功）；具体几何结果通过其他接口或扩展返回
 */
double leastSquaresFit(const std::vector<Vec3>& points);

/**
 * @brief  使用 RANSAC 从点云中鲁棒拟合直线，抑制离群点。
 *
 * @param[in]  points  输入点云（可能含大量离群点）
 * @param[in]  distanceThreshold  RANSAC 内点判定距离阈值
 * @param[in]  maxIterations  最大迭代次数
 *
 * @return     拟合直线（点 + 方向）
 */
LineFitResult ransacFitLine(const std::vector<Vec3>& points, double distanceThreshold, int maxIterations);

/**
 * @brief  使用 RANSAC 从点云中鲁棒拟合圆。
 *
 * @param[in]  points  输入点云
 * @param[in]  distanceThreshold  内点判定距离阈值
 * @param[in]  maxIterations  最大迭代次数
 *
 * @return     拟合圆（圆心、法向、半径）
 */
CircleFitResult ransacFitCircle(const std::vector<Vec3>& points, double distanceThreshold, int maxIterations);

#endif // GEOM_FITTING_HXX
