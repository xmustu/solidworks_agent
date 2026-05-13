from math import sin, cos, pi
from pysw import SldWorksApp, PartDoc


def polar(r, a):
    return (r * cos(a), r * sin(a))


def radial_quad(r1, r2, a, da_inner, da_outer):
    """
    生成一个带扭转感的径向四边形叶片/齿片
    """
    p1 = polar(r1, a - da_inner)
    p2 = polar(r2, a - da_outer)
    p3 = polar(r2, a + da_outer)
    p4 = polar(r1, a + da_inner)
    return [p1, p2, p3, p4, p1]


app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("SciFi_Arc_Reactor_Turbine_Core"))

# =========================
# 1. 主体底盘
# =========================

s_base = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(0, 0, 0.085, "XY")
sw_doc.extrude(s_base, depth=0.010, single_direction=True, merge=True)

# 中心孔切除
s_center_hole = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(0, 0, 0.016, "XY")
sw_doc.extrude_cut(s_center_hole, depth=0.014, single_direction=True)

# =========================
# 2. 外圈厚重护环
# =========================

p_top = sw_doc.create_workplane_p_d("XY", 0.010)

s_outer_ring = sw_doc.insert_sketch_on_plane(p_top)
sw_doc.create_circle(0, 0, 0.080, "XY")
sw_doc.extrude(s_outer_ring, depth=0.006, single_direction=True, merge=True)

s_outer_ring_cut = sw_doc.insert_sketch_on_plane(p_top)
sw_doc.create_circle(0, 0, 0.064, "XY")
sw_doc.extrude_cut(s_outer_ring_cut, depth=0.008, single_direction=True)

# =========================
# 3. 中央能量核心
# =========================

s_core = sw_doc.insert_sketch_on_plane(p_top)
sw_doc.create_circle(0, 0, 0.026, "XY")
sw_doc.extrude(s_core, depth=0.018, single_direction=True, merge=True)

# 中央小孔，像喷口/灯仓
p_core_top = sw_doc.create_workplane_p_d("XY", 0.028)
s_core_socket = sw_doc.insert_sketch_on_plane(p_core_top)
sw_doc.create_circle(0, 0, 0.010, "XY")
sw_doc.extrude_cut(s_core_socket, depth=-0.014, single_direction=True)

# =========================
# 4. 12 片旋涡叶片
# =========================

p_blade = sw_doc.create_workplane_p_d("XY", 0.012)

blade_count = 12
for i in range(blade_count):
    a = 2 * pi * i / blade_count

    # 叶片从内圈延伸到外圈，并带一点旋转偏移
    pts = radial_quad(
        r1=0.030,
        r2=0.060,
        a=a + 0.10,
        da_inner=0.045,
        da_outer=0.105
    )

    s_blade = sw_doc.insert_sketch_on_plane(p_blade)
    sw_doc.create_lines(pts, "XY")
    sw_doc.extrude(s_blade, depth=0.006, single_direction=True, merge=True)

# =========================
# 5. 24 个外圈散热齿
# =========================

p_teeth = sw_doc.create_workplane_p_d("XY", 0.004)

tooth_count = 24
for i in range(tooth_count):
    a = 2 * pi * i / tooth_count

    pts = radial_quad(
        r1=0.080,
        r2=0.096,
        a=a,
        da_inner=0.030,
        da_outer=0.022
    )

    s_tooth = sw_doc.insert_sketch_on_plane(p_teeth)
    sw_doc.create_lines(pts, "XY")
    sw_doc.extrude(s_tooth, depth=0.010, single_direction=True, merge=True)

# =========================
# 6. 放射状镂空窗
# =========================

p_cut = sw_doc.create_workplane_p_d("XY", 0.020)

window_count = 12
for i in range(window_count):
    a = 2 * pi * i / window_count + pi / window_count

    pts = radial_quad(
        r1=0.035,
        r2=0.056,
        a=a,
        da_inner=0.025,
        da_outer=0.045
    )

    s_window = sw_doc.insert_sketch_on_plane(p_cut)
    sw_doc.create_lines(pts, "XY")
    sw_doc.extrude_cut(s_window, depth=-0.018, single_direction=True)

# =========================
# 7. 内圈装饰螺栓孔
# =========================

bolt_count = 6
for i in range(bolt_count):
    a = 2 * pi * i / bolt_count
    x, y = polar(0.044, a)

    s_bolt = sw_doc.insert_sketch_on_plane(p_top)
    sw_doc.create_circle(x, y, 0.0035, "XY")
    sw_doc.extrude_cut(s_bolt, depth=0.010, single_direction=True)

# =========================
# 8. 倒角/圆角装饰
# =========================
# 这些点需要根据实际模型边的位置微调。
# 如果你的选择器足够稳定，可以保留；否则可以先注释掉，等主体生成后再调点位。

# try:
#     sw_doc.chamfer_edges(
#         on_line_points=[
#             (0.085, 0, 0.010),
#             (-0.085, 0, 0.010),
#             (0, 0.085, 0.010),
#             (0, -0.085, 0.010),
#         ],
#         distance=0.0015,
#         angle=45.0
#     )

#     sw_doc.fillet_edges(
#         on_line_points=[
#             (0.026, 0, 0.028),
#             (-0.026, 0, 0.028),
#             (0, 0.026, 0.028),
#             (0, -0.026, 0.028),
#         ],
#         radius=0.0012
#     )
# except Exception:
#     print("圆角/倒角选择失败，可在主体建成后微调 on_line_points。")

# =========================
# 9. 保存
# =========================
