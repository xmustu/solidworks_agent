# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("CrossBeamFrame"))

# 2. 参数定义 (单位: m)
# 外部尺寸: 1120mm x 520mm -> 1.12m x 0.52m
# 管截面: 30mm x 30mm -> 0.03m x 0.03m
# 高度: 30mm -> 0.03m
outer_length = 1.12
outer_width = 0.52
tube_size = 0.03
height = 0.03

# 内部矩形尺寸计算
inner_length = outer_length - 2 * tube_size
inner_width = outer_width - 2 * tube_size

print(f"建模参数: 外长={outer_length}, 外宽={outer_width}, 管厚={tube_size}, 高={height}")

# 3. 建模步骤

# 3.1 在 XY 平面创建草图
sketch1 = sw_doc.insert_sketch_on_plane("XY")

# 3.2 绘制外轮廓矩形 (中心在原点)
sw_doc.create_centre_rectangle(
    center_x=0, 
    center_y=0, 
    width=outer_length, 
    height=outer_width, 
    sketch_ref="XY"
)

# 3.3 绘制内轮廓矩形 (用于形成空心框架)
# 注意：SolidWorks 拉伸时，如果两个封闭轮廓嵌套，默认会生成带孔的实体（即框架形状）
sw_doc.create_centre_rectangle(
    center_x=0, 
    center_y=0, 
    width=inner_length, 
    height=inner_width, 
    sketch_ref="XY"
)

# 3.4 拉伸生成框架主体
# 向 +Z 方向拉伸高度
extrude_feature = sw_doc.extrude(sketch1, depth=height, single_direction=True, merge=True)
print("框架主体拉伸完成")

# 4. 创建装配接口 (参考面和参考轴)

# 4.1 创建端面参考面 (用于与桌腿配合)
# end_face_x_minus: X负方向的端面，位于 X = -outer_length/2
plane_x_minus = sw_doc.create_ref_plane(
    plane="YZ", # 基于 YZ 平面偏移
    offset_val=-outer_length / 2,
    target_plane_name="end_face_x_minus"
)

# end_face_x_plus: X正方向的端面，位于 X = +outer_length/2
plane_x_plus = sw_doc.create_ref_plane(
    plane="YZ",
    offset_val=outer_length / 2,
    target_plane_name="end_face_x_plus"
)

# end_face_y_minus: Y负方向的端面，位于 Y = -outer_width/2
plane_y_minus = sw_doc.create_ref_plane(
    plane="XZ", # 基于 XZ 平面偏移
    offset_val=-outer_width / 2,
    target_plane_name="end_face_y_minus"
)

# end_face_y_plus: Y正方向的端面，位于 Y = +outer_width/2
plane_y_plus = sw_doc.create_ref_plane(
    plane="XZ",
    offset_val=outer_width / 2,
    target_plane_name="end_face_y_plus"
)

print("端面参考面创建完成")

# 4.2 创建中心轴线 (用于对齐)
# axis_x_center: 沿 X 轴的中心线
axis_x = sw_doc.create_axis(
    pt1=(-outer_length/2, 0, height/2),
    pt2=(outer_length/2, 0, height/2),
    axis_name="axis_x_center"
)

# axis_y_center: 沿 Y 轴的中心线
axis_y = sw_doc.create_axis(
    pt1=(0, -outer_width/2, height/2),
    pt2=(0, outer_width/2, height/2),
    axis_name="axis_y_center"
)

print("中心轴线创建完成")

# 5. 保存零件
output_path = r"D:\a_src\python\sw_agent\agent_output\Modern_Square_Table_Assembly-20260429_140925\parts\cross_beam_frame\cross_beam_frame.SLDPRT"
success = sw_doc.save_as(output_path)

if success:
    print(f"零件已成功保存至: {output_path}")
else:
    print("零件保存失败")