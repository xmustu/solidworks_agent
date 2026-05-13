# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("Nut_M8_Simplified"))

# 2. 参数定义 (单位: m)
width_across_flats_mm = 13.0
thickness_mm = 6.0
hole_diameter_mm = 8.0

width_across_flats_m = width_across_flats_mm / 1000.0
thickness_m = thickness_mm / 1000.0
hole_radius_m = (hole_diameter_mm / 1000.0) / 2.0

# 计算六边形外接圆半径 (用于 create_polygon)
# 对边距离 S = 2 * R_inscribed
# R_inscribed = S / 2
# R_circumscribed = R_inscribed / cos(30deg) = (S/2) / (sqrt(3)/2) = S / sqrt(3)
import math
r_inscribed = width_across_flats_m / 2.0
r_circumscribed = r_inscribed / math.cos(math.radians(30))

print(f"Creating Nut M8: Width={width_across_flats_m}m, Thickness={thickness_m}m, Hole Radius={hole_radius_m}m")

# 3. 建模主体：正六边形拉伸
# 在 XY 平面绘制草图
sketch_hex = sw_doc.insert_sketch_on_plane("XY")

# 创建正六边形
# center_x=0, center_y=0, radius=r_circumscribed, sides=6, inscribed=False (外接圆模式，因为API通常radius指外接圆半径或内切圆半径，需确认。
# 根据KB: "radius: 内接圆半径, inscribed=True表示内接圆, False表示外接圆"
# 这里我们需要对边距离为13mm，即内切圆直径13mm，半径6.5mm。
# 所以如果 inscribed=True, radius 应该是 6.5mm (0.0065m)。
# 如果 inscribed=False, radius 应该是外接圆半径。
# 让我们使用 inscribed=True 并传入内切圆半径，这样更直接对应“对边距离”。
sw_doc.create_polygon(center_x=0, center_y=0, radius=r_inscribed, sides=6, inscribed=True, sketch_ref="XY")

# 退出草图并拉伸
sw_doc.partDoc.SketchManager.InsertSketch(True) # 确保草图关闭
extrude_body = sw_doc.extrude(sketch_hex, depth=thickness_m, single_direction=True, merge=True)

# 4. 切除中心孔
# 在顶面 (Z = thickness_m) 创建草图
# 为了准确选择面，我们可以在 Z=thickness_m 处创建一个参考平面，或者直接在该高度建草图
# 这里直接在 XY 平面偏移或直接利用现有几何。由于是通孔，我们可以直接在底面或顶面画圆然后贯穿切除。
# 为了稳健，我们在顶面位置创建草图。
# 注意：SolidWorks API 中 insert_sketch_on_plane 通常接受基准面名称。
# 我们可以先创建一个位于顶部的参考平面，或者直接使用 "XY" 并在拉伸时指定方向。
# 更简单的方法：在 XY 平面画圆，然后做贯穿切除 (Through All)，但 extrude_cut 需要 depth。
# 我们可以设置 depth 为 -thickness_m (向下切除) 或 +thickness_m (向上切除，如果草图在底面)。
# 让我们在底面 (Z=0) 画圆，然后向上切除厚度。

sketch_hole = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(center_x=0, center_y=0, radius=hole_radius_m, sketch_ref="XY")
sw_doc.partDoc.SketchManager.InsertSketch(True)

# 向上切除，深度等于厚度
cut_hole = sw_doc.extrude_cut(sketch_hole, depth=thickness_m, single_direction=True)

# 5. 创建装配接口
# 5.1 参考轴: nut_axis (沿 Z 轴)
# 从 (0,0,0) 到 (0,0,1)
axis_nut = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 1), axis_name="nut_axis")

# 5.2 参考面: top_face 和 bottom_face
# bottom_face: Z=0 平面
plane_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="bottom_face")

# top_face: Z=thickness_m 平面
plane_top = sw_doc.create_ref_plane(plane="XY", offset_val=thickness_m, target_plane_name="top_face")

# 6. 保存零件
output_path = r"D:\a_src\python\sw_agent\agent_output\Table_Assembly_M8_Fastened-20260429_112407\parts\nut_m8\nut_m8.SLDPRT"
success = sw_doc.save_as(output_path)

if success:
    print(f"Part saved successfully to {output_path}")
else:
    print("Failed to save part.")