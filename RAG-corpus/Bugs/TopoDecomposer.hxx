#ifndef TOPO_DECOMPOSER_HXX
#define TOPO_DECOMPOSER_HXX

#include <vector>

/** 拓扑形状句柄（示例，可替换为 OpenCASCADE 等 TopoDS_Shape） */
typedef void* ShapeHandle;
/** 面句柄 */
typedef void* FaceHandle;
/** 边句柄 */
typedef void* EdgeHandle;
/** 顶点句柄 */
typedef void* VertexHandle;

/**
 * @brief  将复合 Shape 分解为若干子形状（体、壳、面、边、顶点等）。
 *
 * @param[in]  shape  待分解的拓扑形状
 *
 * @return     子形状句柄序列（类型可由调用方根据 shape 类型区分）
 */
std::vector<ShapeHandle> decomposeShape(ShapeHandle shape);

/**
 * @brief  从 Shape 中提取所有面（Face）。
 *
 * @param[in]  shape  输入拓扑形状
 *
 * @return     面句柄数组
 */
std::vector<FaceHandle> getFaces(ShapeHandle shape);

/**
 * @brief  从 Shape 中提取所有边（Edge）。
 *
 * @param[in]  shape  输入拓扑形状
 *
 * @return     边句柄数组
 */
std::vector<EdgeHandle> getEdges(ShapeHandle shape);

/**
 * @brief  从 Shape 中提取所有顶点（Vertex）。
 *
 * @param[in]  shape  输入拓扑形状
 *
 * @return     顶点句柄数组
 */
std::vector<VertexHandle> getVertices(ShapeHandle shape);

/**
 * @brief  对形状中的面或边进行连通域分析，得到互不连通的若干组。
 *
 * @param[in]  shape  输入拓扑形状
 *
 * @return     每组为同一连通域内的面/边句柄列表，外层为连通域列表
 */
std::vector<std::vector<FaceHandle>> findConnectedComponents(ShapeHandle shape);

/**
 * @brief  识别形状的边界（如壳的外轮廓边、面的边界环）。
 *
 * @param[in]  shape  输入拓扑形状（或面/壳）
 *
 * @return     边界边句柄序列，顺序沿边界走向
 */
std::vector<EdgeHandle> getBoundary(ShapeHandle shape);

/**
 * @brief  从面中提取其外环与内环（孔）的边序列。
 *
 * @param[in]  face  输入面
 *
 * @return     第一个为外环边序列，后续为各内环边序列
 */
std::vector<std::vector<EdgeHandle>> getFaceWires(FaceHandle face);

#endif // TOPO_DECOMPOSER_HXX
