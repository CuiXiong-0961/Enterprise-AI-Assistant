#ifndef TOOLPATH_LINKER_HXX
#define TOOLPATH_LINKER_HXX

#include <vector>

struct Vec3 { double x, y, z; };

/** 单段刀路（简化） */
struct PathSegment {
    Vec3 start;
    Vec3 end;
};
/** 刀路序列 */
typedef std::vector<PathSegment> Toolpath;

/**
 * @brief  对多条刀路进行移刀路径优化，使刀具在段与段之间移动总长尽量短。
 *
 * @param[in]  paths  多条刀路（每条的起点、终点已知）
 * @param[in]  startPoint  刀具初始位置
 *
 * @return     重新排序后的刀路顺序（或带连接段的完整刀路）
 */
std::vector<Toolpath> optimizeLinkingOrder(const std::vector<Toolpath>& paths, const Vec3& startPoint);

/**
 * @brief  在两条刀路之间计算最短安全移刀路径（抬刀、平移、下刀）。
 *
 * @param[in]  endOfPath1  前一段刀路终点
 * @param[in]  startOfPath2  后一段刀路起点
 * @param[in]  safeHeight  安全抬刀高度（Z）
 *
 * @return     移刀路径点序列（含抬刀、平移、下刀）
 */
std::vector<Vec3> computeShortestLink(const Vec3& endOfPath1, const Vec3& startOfPath2, double safeHeight);

/**
 * @brief  检查并保证移刀段满足 G1 连续性（无突变），必要时插入过渡段。
 *
 * @param[in,out]  path  刀路点序列，可能被插入过渡点
 *
 * @return     无（path 原地修改）或返回修正后的路径
 */
void ensureG1Continuity(std::vector<Vec3>& path);

/**
 * @brief  在连接处添加 G2 连续（曲率连续）的圆弧或样条过渡。
 *
 * @param[in]  path  原始刀路点序列
 * @param[in]  cornerRadius  过渡圆弧半径（或等效参数）
 *
 * @return     插入过渡段后的新刀路点序列
 */
std::vector<Vec3> addG2Transitions(const std::vector<Vec3>& path, double cornerRadius);

#endif // TOOLPATH_LINKER_HXX
