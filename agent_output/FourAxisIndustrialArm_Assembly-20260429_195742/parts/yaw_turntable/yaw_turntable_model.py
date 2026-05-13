from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
part_name = "Yaw Turntable"
sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

# 2. 参数定义 (单位: m)
body_diameter = 0.180  # 180 mm
body_height = 0.040    # 40 mm
boss_diameter = 0.100  # 100 mm
boss_height = 0.020    # 20 mm
fillet_radius = 0.002  # R2 mm

print(f"开始建模零件: {part_name}")

# 3. 主体建模 (Body Cylinder D180xH40)
# 在 XY 平面绘制底圆
sketch_body = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(center_x=0, center_y=0, radius=body_diameter / 2, sketch_ref="XY")
sw_doc.partDoc.SketchManager.InsertSketch(True) # 退出草图

# 拉伸主体
extrude_body = sw_doc.extrude(sketch_body, depth=body_height, single_direction=True, merge=True)
print("主体圆柱体创建完成")

# 4. 顶部凸台建模 (Boss Cylinder D100xH20)
# 需要在主体顶面创建草图。由于封装限制，我们通常使用基准面或偏移平面。
# 这里创建一个距离 XY 平面 body_height 的偏移平面作为参考，或者直接在 Z=body_height 处操作。
# 为了稳健性，先创建一个工作平面在 Z = body_height
plane_top = sw_doc.create_workplane_p_d(plane="XY", offset_val=body_height)

# 在该平面上绘制凸台草图
sketch_boss = sw_doc.insert_sketch_on_plane(plane_top)
sw_doc.create_circle(center_x=0, center_y=0, radius=boss_diameter / 2, sketch_ref="XY") # 注意：虽然平面是偏移的，但局部坐标参考仍可能映射到 XY 逻辑，需确保圆心在轴线上
sw_doc.partDoc.SketchManager.InsertSketch(True) # 退出草图

# 拉伸凸台
extrude_boss = sw_doc.extrude(sketch_boss, depth=boss_height, single_direction=True, merge=True)
print("顶部凸台创建完成")

# 5. 圆角处理 (Fillet R2 at base of boss)
# 需要选择凸台与主体交界处的边。
# 边的位置大约在 Z = body_height, Radius = boss_diameter/2
# 使用 fillet_edges，传入边上的一点
edge_point = (0, boss_diameter / 2, body_height) # 圆周上一点
try:
    sw_doc.fillet_edges(on_line_points=[edge_point], radius=fillet_radius)
    print("圆角特征应用完成")
except Exception as e:
    print(f"圆角应用失败，可能是几何选择问题: {e}")

# 6. 创建装配接口 (Interfaces)

# 6.1 面接口
# bottom_face: Z=0 的底面
# top_boss_face: Z=body_height+boss_height 的顶面
# 通过创建命名参考平面来暴露这些面，或者直接依赖几何面。
# 根据要求，优先创建命名参考面。

# 创建 bottom_face 参考平面 (Z=0)
ref_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="bottom_face")

# 创建 top_boss_face 参考平面 (Z = body_height + boss_height)
top_z = body_height + boss_height
ref_top_boss = sw_doc.create_ref_plane(plane="XY", offset_val=top_z, target_plane_name="top_boss_face")

# 6.2 轴接口
# center_axis_z: 沿 Z 轴的中心线
# shoulder_mount_axis_z: 同样沿 Z 轴，因为凸台是同心的
axis_z = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 1), axis_name="center_axis_z")
# shoulder_mount_axis_z 与 center_axis_z 重合，可以复用或创建别名。
# 为了明确语义，创建另一个指向相同的轴，或者在装配时使用同一个。
# 这里创建名为 shoulder_mount_axis_z 的轴，起点和终点相同
axis_shoulder = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 1), axis_name="shoulder_mount_axis_z")

print("装配接口创建完成")

# 7. 保存文件
model_path = r"D:\a_src\python\sw_agent\agent_output\FourAxisIndustrialArm_Assembly-20260429_195742\parts\yaw_turntable\yaw_turntable.SLDPRT"
success = sw_doc.save_as(model_path)

if success:
    print(f"零件已成功保存至: {model_path}")
else:
    print("零件保存失败")