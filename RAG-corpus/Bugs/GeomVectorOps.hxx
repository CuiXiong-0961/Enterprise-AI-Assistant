#ifndef GEOM_VECTOR_OPS_HXX
#define GEOM_VECTOR_OPS_HXX

/** 三维向量/点类型（示例，可替换为公司内部类型） */
struct Vec3 {
    double x, y, z;
};

/** 4x4 变换矩阵（行主序，示例） */
struct Mat4 {
    double m[4][4];
};

/**
 * @brief  计算两个三维向量的逐分量加法，返回结果向量。
 *
 * @param[in]  lhs  第一个输入向量（被加数）
 * @param[in]  rhs  第二个输入向量（加数）
 *
 * @return     返回一个新的三维向量，其结果为 result = (lhs.x + rhs.x, lhs.y + rhs.y, lhs.z + rhs.z)
 */
Vec3 add(const Vec3& lhs, const Vec3& rhs);

/**
 * @brief  计算两个三维向量的逐分量减法。
 *
 * @param[in]  lhs  被减向量
 * @param[in]  rhs  减数向量
 *
 * @return     结果向量 result = lhs - rhs
 */
Vec3 subtract(const Vec3& lhs, const Vec3& rhs);

/**
 * @brief  计算两个三维向量的点乘（内积）。
 *
 * @param[in]  a  第一个向量
 * @param[in]  b  第二个向量
 *
 * @return     标量 a.x*b.x + a.y*b.y + a.z*b.z
 */
double dot(const Vec3& a, const Vec3& b);

/**
 * @brief  计算两个三维向量的叉乘，得到与两向量均垂直的向量。
 *
 * @param[in]  a  第一个向量
 * @param[in]  b  第二个向量
 *
 * @return     叉乘结果向量，方向服从右手系
 */
Vec3 cross(const Vec3& a, const Vec3& b);

/**
 * @brief  计算向量的欧氏长度（模长）。
 *
 * @param[in]  v  输入向量
 *
 * @return     标量 sqrt(v.x^2 + v.y^2 + v.z^2)
 */
double length(const Vec3& v);

/**
 * @brief  将向量单位化，保持方向不变。
 *
 * @param[in]  v  输入向量（非零）
 *
 * @return     单位向量；若输入为零向量则行为由实现定义
 */
Vec3 normalize(const Vec3& v);

/**
 * @brief  使用 4x4 变换矩阵对三维点/向量进行坐标变换。
 *
 * @param[in]  p  输入点或向量
 * @param[in]  mat  4x4 变换矩阵
 *
 * @return     变换后的三维点/向量
 */
Vec3 transform(const Vec3& p, const Mat4& mat);

/**
 * @brief  将向量 a 投影到向量 b 方向上，得到标量投影长度。
 *
 * @param[in]  a  被投影向量
 * @param[in]  b  投影方向向量（建议单位化）
 *
 * @return     标量投影长度（带符号）
 */
double projectScalar(const Vec3& a, const Vec3& b);

/**
 * @brief  将向量 a 投影到向量 b 方向上，得到投影向量。
 *
 * @param[in]  a  被投影向量
 * @param[in]  b  投影方向向量（建议单位化）
 *
 * @return     沿 b 方向的投影向量
 */
Vec3 projectVector(const Vec3& a, const Vec3& b);

/**
 * @brief  计算三维空间中两点之间的欧氏距离。
 *
 * @param[in]  a  第一个点
 * @param[in]  b  第二个点
 *
 * @return     两点间距离（非负标量）
 */
double distance(const Vec3& a, const Vec3& b);

/**
 * @brief  根据三点计算平面法向（右手系，由 p1->p2 与 p1->p3 叉乘得到）。
 *
 * @param[in]  p1  平面上第一个点
 * @param[in]  p2  平面上第二个点
 * @param[in]  p3  平面上第三个点
 *
 * @return     单位法向量；若三点共线则行为由实现定义
 */
Vec3 computeFaceNormal(const Vec3& p1, const Vec3& p2, const Vec3& p3);

#endif // GEOM_VECTOR_OPS_HXX
