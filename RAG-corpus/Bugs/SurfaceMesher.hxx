#ifndef SURFACE_MESHER_HXX
#define SURFACE_MESHER_HXX

#include <vector>

struct Vec3 { double x, y, z; };
/** 曲面句柄（示例） */
typedef void* SurfaceHandle;

/** 三角面：三个顶点索引 */
struct Triangle {
    int v0, v1, v2;
};

/** 三角网格：顶点表 + 三角面表 */
struct TriMesh {
    std::vector<Vec3> vertices;
    std::vector<Triangle> triangles;
};

/**
 * @brief  为曲面生成三角网格。
 *
 * @param[in]  surface  输入曲面句柄
 * @param[in]  maxEdgeLength  期望最大边长（或 0 表示自动）
 *
 * @return     三角网格（顶点 + 三角形索引）
 */
TriMesh generateTriMesh(SurfaceHandle surface, double maxEdgeLength);

/**
 * @brief  修正三角网格顶点或面法向，使朝向一致（如均朝外）。
 *
 * @param[in,out]  mesh  待修正的三角网格（可能被原地修改）
 *
 * @return     修正后的网格（或通过引用返回）
 */
void fixNormals(TriMesh& mesh);

/**
 * @brief  设置网格生成时的弦高/误差控制容差。
 *
 * @param[in]  tolerance  最大允许误差（弦高或几何偏差）
 *
 * @return     无；或通过全局/上下文设置影响后续 generateTriMesh 等调用
 */
void setTolerance(double tolerance);

/**
 * @brief  使用 Delaunay 三角化从平面点集生成三角网格。
 *
 * @param[in]  points  平面上的点集（z 可同值或忽略）
 *
 * @return     三角网格
 */
TriMesh delaunayTriangulate(const std::vector<Vec3>& points);

/**
 * @brief  使用 Advancing Front 方法在曲面或区域内生成三角网格。
 *
 * @param[in]  surface  输入曲面或边界
 * @param[in]  targetEdgeLength  目标边长
 *
 * @return     三角网格
 */
TriMesh advancingFrontMesh(SurfaceHandle surface, double targetEdgeLength);

/**
 * @brief  根据弦高误差细化网格，在曲率大的区域加密。
 *
 * @param[in,out]  mesh  输入网格，可能被细化
 * @param[in]  maxChordError  允许的最大弦高误差
 *
 * @return     无（mesh 原地更新）或返回新网格
 */
void refineMeshByError(TriMesh& mesh, double maxChordError);

#endif // SURFACE_MESHER_HXX
