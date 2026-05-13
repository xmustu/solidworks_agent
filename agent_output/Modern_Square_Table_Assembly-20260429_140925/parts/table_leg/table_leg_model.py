# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
part_name = "Table Leg"
sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

# 2. 参数定义 (单位: m)
leg_width = 0.040  # 40 mm
leg_depth = 0.040  # 40 mm
leg_height = 0.720 # 720 mm

print(f"开始建模零件: {part_name}")
print(f"尺寸: {leg_width*1000}mm x {leg_depth*1000}mm x {leg_height*1000}mm")

# 3. 建模步骤

# 3.1 在 XY 平面创建草图
sketch_plane = "XY"
sketch1 = sw_doc.insert_sketch_on_plane(sketch_plane)

# 3.2 绘制中心矩形 (40mm x 40mm)
# create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
sw_doc.create_centre_rectangle(
    center_x=0, 
    center_y=0, 
    width=leg_width, 
    height=leg_depth, 
    sketch_ref=sketch_plane
)

# 3.3 拉伸凸台 (高度 720mm, +Z 方向)
# extrude(sketch, depth, single_direction=True, merge=True)
extrude_feat = sw_doc.extrude(
    sketch=sketch1, 
    depth=leg_height, 
    single_direction=True, 
    merge=True
)
print("主体拉伸完成")

# 4. 创建装配接口 (参考面/轴)

# 4.1 顶面接口 (top_face): Z = leg_height
# 用于与桌面底部配合
top_face_plane = sw_doc.create_ref_plane(
    plane="XY", 
    offset_val=leg_height, 
    target_plane_name="top_face"
)
print("创建接口: top_face")

# 4.2 内侧面接口 X+ (inner_face_x_plus): X = leg_width / 2
# 假设局部坐标系中，+X 指向桌子中心的一侧。
# 由于桌腿是正方形截面且对称，我们定义 +X 侧为 inner_face_x_plus
inner_x_plus_plane = sw_doc.create_ref_plane(
    plane="ZY", 
    offset_val=leg_width / 2, 
    target_plane_name="inner_face_x_plus"
)
print("创建接口: inner_face_x_plus")

# 4.3 内侧面接口 Y+ (inner_face_y_plus): Y = leg_depth / 2
# 同理，定义 +Y 侧为 inner_face_y_plus
inner_y_plus_plane = sw_doc.create_ref_plane(
    plane="XZ", 
    offset_val=leg_depth / 2, 
    target_plane_name="inner_face_y_plus"
)
print("创建接口: inner_face_y_plus")

# 4.4 中心轴接口 (center_axis_z)
# 沿 Z 轴的中心线，用于同心配合
center_axis = sw_doc.create_axis(
    pt1=(0, 0, 0), 
    pt2=(0, 0, leg_height), 
    axis_name="center_axis_z"
)
print("创建接口: center_axis_z")

# 5. 保存零件
model_path = r"D:\a_src\python\sw_agent\agent_output\Modern_Square_Table_Assembly-20260429_140925\parts\table_leg\table_leg.SLDPRT"
save_success = sw_doc.save_as(model_path)

if save_success:
    print(f"零件成功保存至: {model_path}")
else:
    print("零件保存失败")