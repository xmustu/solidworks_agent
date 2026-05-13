# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("Stand Column Inner Tube"))

# 2. 参数定义 (单位: m)
outer_diameter_m = 0.030  # 30mm
radius_m = outer_diameter_m / 2
height_m = 0.150          # 150mm

print(f"开始建模 Stand Column Inner Tube: OD={outer_diameter_m}m, H={height_m}m")

# 3. 建模步骤

# 3.1 在 XY 平面绘制圆形草图
sketch_circle = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(center_x=0, center_y=0, radius=radius_m, sketch_ref="XY")
print("草图绘制完成: 中心圆")

# 3.2 拉伸生成圆柱体
extrude_feature = sw_doc.extrude(sketch_circle, depth=height_m, single_direction=True, merge=True)
print(f"拉伸特征完成: 高度 {height_m}m")

# 4. 创建装配接口 (参考面/轴)

# 4.1 创建中心轴 (inner_tube_center_axis)
# 从底部中心 (0,0,0) 到顶部中心 (0,0,height)
axis_obj = sw_doc.create_axis(
    pt1=(0, 0, 0), 
    pt2=(0, 0, height_m), 
    axis_name="inner_tube_center_axis"
)
print("接口创建完成: inner_tube_center_axis")

# 4.2 创建底面参考 (inner_tube_bottom_face)
# 基于 XY 平面偏移 0，命名为 bottom face
bottom_plane = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="inner_tube_bottom_face")
print("接口创建完成: inner_tube_bottom_face")

# 4.3 创建顶面参考 (inner_tube_top_face)
# 基于 XY 平面偏移 height，命名为 top face
top_plane = sw_doc.create_ref_plane(plane="XY", offset_val=height_m, target_plane_name="inner_tube_top_face")
print("接口创建完成: inner_tube_top_face")

# 5. 保存文件
model_path = r"D:\a_src\python\sw_agent\agent_output\27inch_Monitor_Assembly-20260428_113916\parts\stand_column_inner\stand_column_inner.SLDPRT"
success = sw_doc.save_as(model_path)

if success:
    print(f"零件已成功保存至: {model_path}")
else:
    print("零件保存失败，请检查路径或 SolidWorks 状态。")