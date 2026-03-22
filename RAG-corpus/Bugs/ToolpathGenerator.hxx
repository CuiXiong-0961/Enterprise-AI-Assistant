#ifndef TOOLPATH_GENERATOR_HXX
#define TOOLPATH_GENERATOR_HXX

#include <vector>

struct Vec3 { double x, y, z; };
/** 曲面/模型句柄（示例） */
typedef void* ModelHandle;
/** 刀具句柄（直径、圆角等，示例） */
typedef void* ToolHandle;

/** 单段刀路：起点、终点、类型（G0/G1/...）等 */
struct ToolpathSegment {
    Vec3 start;
    Vec3 end;
    int type;  // 0=G0 快移, 1=G1 直线切削, 2=G2/G3 圆弧等
};
/** 一条完整刀路：多段组成 */
struct Toolpath {
    std::vector<ToolpathSegment> segments;
};

/**
 * @brief  生成等高线（层切）刀路，按高度分层切削。
 *
 * @param[in]  model  加工模型/毛坯
 * @param[in]  tool  刀具参数
 * @param[in]  layerHeight  每层切削高度
 * @param[in]  zMin  最低层高度
 * @param[in]  zMax  最高层高度
 *
 * @return     各层的刀路序列（每层一条或多条刀路）
 */
std::vector<Toolpath> generateContourToolpaths(ModelHandle model, ToolHandle tool,
    double layerHeight, double zMin, double zMax);

/**
 * @brief  生成平行截面刀路，用一组平行平面与模型求交得到切削路径。
 *
 * @param[in]  model  加工模型
 * @param[in]  tool  刀具参数
 * @param[in]  planeNormal  截面法向（截面平行于与该法向垂直的平面）
 * @param[in]  sectionSpacing  截面间距
 *
 * @return     各截面上的刀路序列
 */
std::vector<Toolpath> generateParallelSectionToolpaths(ModelHandle model, ToolHandle tool,
    const Vec3& planeNormal, double sectionSpacing);

/**
 * @brief  生成等距偏置路径，将轮廓向内或向外偏置得到刀心轨迹。
 *
 * @param[in]  contour  二维轮廓点序列（或封闭环）
 * @param[in]  offset  偏置距离（正为外偏，负为内偏，视约定）
 * @param[in]  zHeight  该层刀路高度
 *
 * @return     偏置后的刀路（同一高度上的路径）
 */
Toolpath generateOffsetToolpath(const std::vector<Vec3>& contour, double offset, double zHeight);

#endif // TOOLPATH_GENERATOR_HXX
