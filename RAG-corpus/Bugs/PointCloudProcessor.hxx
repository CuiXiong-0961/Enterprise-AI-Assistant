#ifndef POINT_CLOUD_PROCESSOR_HXX
#define POINT_CLOUD_PROCESSOR_HXX

#include <vector>

struct Vec3 { double x, y, z; };
/** 带法向的点 */
struct PointNormal {
    Vec3 point;
    Vec3 normal;
};

/**
 * @brief  对点云进行滤波，去除离群点或平滑噪声。
 *
 * @param[in]  points  输入点云
 * @param[in]  radius  邻域半径（或 K 近邻的 K）
 * @param[in]  minNeighbors  保留点所需的最小邻域点数
 *
 * @return     滤波后的点云
 */
std::vector<Vec3> filterPointCloud(const std::vector<Vec3>& points, double radius, int minNeighbors);

/**
 * @brief  估计点云中每点的法向量（基于局部平面拟合或 PCA）。
 *
 * @param[in]  points  输入点云
 * @param[in]  kNeighbors  每点使用的邻域点数
 *
 * @return     带法向的点序列（与输入顺序一致）
 */
std::vector<PointNormal> estimateNormals(const std::vector<Vec3>& points, int kNeighbors);

/**
 * @brief  对点云进行重采样，使点分布更均匀（如体素下采样或均匀网格采样）。
 *
 * @param[in]  points  输入点云
 * @param[in]  voxelSize  体素边长（或采样网格间距）
 *
 * @return     重采样后的点云
 */
std::vector<Vec3> resamplePointCloud(const std::vector<Vec3>& points, double voxelSize);

/**
 * @brief  从离散点云重建三角网格（如 Poisson 或 Ball Pivoting）。
 *
 * @param[in]  points  输入点云
 * @param[in]  normals  与 points 对应的法向（可为空，则内部估计）
 *
 * @return     三角网格顶点与三角形索引（可用与 SurfaceMesher 兼容的结构返回，此处简化为顶点+索引对）
 */
struct ReconstructedMesh {
    std::vector<Vec3> vertices;
    std::vector<int> triangleIndices;  // 每 3 个为一三角形
};
ReconstructedMesh reconstructFromPoints(const std::vector<Vec3>& points,
    const std::vector<Vec3>& normals);

/**
 * @brief  按距离阈值下采样，使任意两点距离不小于给定值。
 *
 * @param[in]  points  输入点云
 * @param[in]  minDistance  最小保留点间距
 *
 * @return     下采样后的点云
 */
std::vector<Vec3> downsampleByDistance(const std::vector<Vec3>& points, double minDistance);

/**
 * @brief  对点云进行平滑，使每个点向其邻域重心或拟合平面投影。
 *
 * @param[in]  points  输入点云
 * @param[in]  radius  邻域半径
 * @param[in]  iterations  平滑迭代次数
 *
 * @return     平滑后的点云
 */
std::vector<Vec3> smoothPointCloud(const std::vector<Vec3>& points, double radius, int iterations);

#endif // POINT_CLOUD_PROCESSOR_HXX
