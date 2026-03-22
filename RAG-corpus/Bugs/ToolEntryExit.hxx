#ifndef TOOL_ENTRY_EXIT_HXX
#define TOOL_ENTRY_EXIT_HXX

#include <vector>

struct Vec3 { double x, y, z; };

/**
 * @brief  生成斜插下刀路径，从安全高度以一定角度斜向切入到切削层。
 *
 * @param[in]  entryPoint  斜面在安全高度侧的起点
 * @param[in]  targetPoint  斜面在切削层的终点（落刀点）
 * @param[in]  angleDeg  斜插角度（与水平面夹角，度）
 *
 * @return     下刀路径点序列
 */
std::vector<Vec3> generateRampEntry(const Vec3& entryPoint, const Vec3& targetPoint, double angleDeg);

/**
 * @brief  生成螺旋下刀路径，在水平面内做圆周运动的同时下降。
 *
 * @param[in]  center  螺旋中心（在切削层上的投影）
 * @param[in]  startZ  起始高度（安全高度）
 * @param[in]  endZ  结束高度（切削层）
 * @param[in]  radius  螺旋半径
 * @param[in]  pitch  每圈下降量
 *
 * @return     螺旋下刀路径点序列
 */
std::vector<Vec3> generateHelixEntry(const Vec3& center, double startZ, double endZ,
    double radius, double pitch);

/**
 * @brief  生成圆弧下刀路径，在垂直平面内以圆弧从外侧切入到落刀点。
 *
 * @param[in]  safePoint  安全高度上的起点
 * @param[in]  tangentPoint  圆弧与切削层的切点
 * @param[in]  radius  圆弧半径
 *
 * @return     圆弧下刀路径点序列
 */
std::vector<Vec3> generateArcEntry(const Vec3& safePoint, const Vec3& tangentPoint, double radius);

/**
 * @brief  根据障碍区域计算避让的进刀路径，避免与夹具或已加工区域干涉。
 *
 * @param[in]  startPoint  期望进刀起点（如安全高度）
 * @param[in]  targetPoint  切削层上的目标落刀点
 * @param[in]  obstaclePoints  障碍物轮廓点（或包围盒顶点）
 *
 * @return     避让后的进刀路径点序列
 */
std::vector<Vec3> generateAvoidingEntry(const Vec3& startPoint, const Vec3& targetPoint,
    const std::vector<Vec3>& obstaclePoints);

/**
 * @brief  生成退刀路径，从切削层抬到安全高度（直线或带过渡）。
 *
 * @param[in]  exitPoint  退刀起点（切削层上最后一点）
 * @param[in]  safeHeight  安全高度 Z 值
 *
 * @return     退刀路径点序列
 */
std::vector<Vec3> generateExitPath(const Vec3& exitPoint, double safeHeight);

#endif // TOOL_ENTRY_EXIT_HXX
