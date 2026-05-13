# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("Screw_M8_Simplified"))

# 2. 参数定义 (单位: m)
head_diam = 0.016  # 16 mm
head_thick = 0.005 # 5 mm
shank_diam = 0.008 # 8 mm
shank_len = 0.030  # 30 mm

print("开始建模 M8 简化螺丝...")

# 3. 建模步骤

# 3.1 创建螺丝头部
# 在 XY 平面绘制头部草图
sketch_head = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(center_x=0, center_y=0, radius=head_diam/2, sketch_ref="XY")
# 拉伸生成头部实体
extrude_head = sw_doc.extrude(sketch_head, depth=head_thick, single_direction=True, merge=True)
print("螺丝头部创建完成。")

# 3.2 创建螺丝杆部
# 需要在头部顶面创建草图。头部顶面位于 Z = head_thick 处。
# 我们可以创建一个偏移平面，或者直接在 XY 平面画圆然后拉伸到指定高度？
# 更稳健的方法是：在头部顶面（Z=0.005）上创建草图。
# 由于 API 限制，我们通常使用基准面。这里我们创建一个平行于 XY 的平面，偏移量为 head_thick。
plane_top_of_head = sw_doc.create_workplane_p_d(plane="XY", offset_val=head_thick)

# 在该平面上绘制杆部草图
sketch_shank = sw_doc.insert_sketch_on_plane(plane_top_of_head)
sw_doc.create_circle(center_x=0, center_y=0, radius=shank_diam/2, sketch_ref="XY") # sketch_ref 仍用 XY 表示局部坐标系方向
# 拉伸生成杆部，向上拉伸 shank_len
extrude_shank = sw_doc.extrude(sketch_shank, depth=shank_len, single_direction=True, merge=True)
print("螺丝杆部创建完成。")

# 4. 创建装配接口

# 4.1 参考轴: screw_axis
# 沿 Z 轴，从原点指向顶部
axis_screw = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, head_thick + shank_len), axis_name="screw_axis")
print("参考轴 screw_axis 创建完成。")

# 4.2 参考面: head_bottom_face
# 螺丝头底面，即 Z=0 的平面 (XY 平面)
# 注意：SolidWorks 中原始 XY 平面可能被隐藏或不可直接重命名，最好创建一个新的参考面并命名
ref_plane_head_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="head_bottom_face")
print("参考面 head_bottom_face 创建完成。")

# 4.3 参考面: shank_end_face
# 螺丝杆末端面，位于 Z = head_thick + shank_len
z_end = head_thick + shank_len
ref_plane_shank_end = sw_doc.create_ref_plane(plane="XY", offset_val=z_end, target_plane_name="shank_end_face")
print("参考面 shank_end_face 创建完成。")

# 5. 保存文件
model_path = r"D:\a_src\python\sw_agent\agent_output\Table_Assembly_M8_Fastened-20260429_112407\parts\screw_m8\screw_m8.SLDPRT"
success = sw_doc.save_as(model_path)

if success:
    print(f"零件模型已保存至: {model_path}")
else:
    print("零件保存失败。")