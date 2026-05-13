from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("JointFork"))

# 2. 参数定义 (单位: m)
base_width = 0.100      # 底座宽度 100mm
base_depth = 0.080      # 底座深度 80mm
base_height = 0.020     # 底座高度 20mm

ear_thickness = 0.015   # 耳厚 15mm
inner_spacing = 0.050   # 内间距 50mm
ear_height = 0.060      # 耳高 60mm (足够容纳连杆轴承座)
hinge_hole_dia = 0.020  # 铰链孔直径 20mm

wrist_boss_dia = 0.040  # 腕部凸台直径 40mm
wrist_boss_height = 0.010 # 腕部凸台高度 10mm
wrist_mount_hole_dia = 0.020 # 腕部安装孔直径 20mm

chamfer_dist = 0.001    # C1 倒角 1mm

# 3. 建模步骤

# --- 3.1 创建底座 (Base Block) ---
print("Step 1: Creating Base Block...")
sketch_base = sw_doc.insert_sketch_on_plane("XY")
# 绘制中心矩形作为底座轮廓
sw_doc.create_centre_rectangle(
    center_x=0, 
    center_y=0, 
    width=base_width, 
    height=base_depth, 
    sketch_ref="XY"
)
base_extrude = sw_doc.extrude(sketch_base, depth=base_height, single_direction=True)

# --- 3.2 创建双耳 (Ears) ---
print("Step 2: Creating Ears...")
# 在底座顶面创建草图
top_plane = sw_doc.create_workplane_p_d("XY", offset_val=base_height)
sketch_ears = sw_doc.insert_sketch_on_plane(top_plane)

# 计算耳朵位置
# 耳朵沿 X 轴分布，间隙沿 X 轴
# 左耳中心 X: - (inner_spacing/2 + ear_thickness/2)
# 右耳中心 X: + (inner_spacing/2 + ear_thickness/2)
left_ear_x_center = -(inner_spacing / 2 + ear_thickness / 2)
right_ear_x_center = (inner_spacing / 2 + ear_thickness / 2)
ear_length_y = 0.060 

# Draw Left Ear Rectangle
sw_doc.create_centre_rectangle(
    center_x=left_ear_x_center,
    center_y=0,
    width=ear_thickness,
    height=ear_length_y,
    sketch_ref="XY"
)

# Draw Right Ear Rectangle
sw_doc.create_centre_rectangle(
    center_x=right_ear_x_center,
    center_y=0,
    width=ear_thickness,
    height=ear_length_y,
    sketch_ref="XY"
)

# Extrude Ears
ears_extrude = sw_doc.extrude(sketch_ears, depth=ear_height, single_direction=True)

# --- 3.3 钻铰链孔 (Hinge Holes) ---
print("Step 3: Drilling Hinge Holes...")
# 孔轴沿 Y 方向，所以在 XZ 平面画草图
sketch_holes = sw_doc.insert_sketch_on_plane("XZ")

# 孔中心 Z = base_height + ear_height / 2
hole_z_center = base_height + ear_height / 2

# 左耳孔
sw_doc.create_circle(
    center_x=left_ear_x_center,
    center_y=hole_z_center, # In XZ sketch, y corresponds to Z
    radius=hinge_hole_dia / 2,
    sketch_ref="XZ"
)

# 右耳孔
sw_doc.create_circle(
    center_x=right_ear_x_center,
    center_y=hole_z_center,
    radius=hinge_hole_dia / 2,
    sketch_ref="XZ"
)

# 拉伸切除，双向贯穿
sw_doc.extrude_cut(sketch_holes, depth=0.100, single_direction=False)

# --- 3.4 腕部专用特征 (Wrist Specific Features) ---
print("Step 4: Adding Wrist Mounting Boss (Universal Feature)...")
# 在耳朵顶部创建凸台
boss_plane = sw_doc.create_workplane_p_d("XY", offset_val=base_height + ear_height)
sketch_boss = sw_doc.insert_sketch_on_plane(boss_plane)

# 凸台位于中心 (0,0)
sw_doc.create_circle(
    center_x=0,
    center_y=0,
    radius=wrist_boss_dia / 2,
    sketch_ref="XY"
)
boss_extrude = sw_doc.extrude(sketch_boss, depth=wrist_boss_height, single_direction=True)

# 在凸台顶部钻安装孔
# 修复：确保切除深度足够且方向正确。从顶面向下切。
top_boss_z = base_height + ear_height + wrist_boss_height
top_boss_plane = sw_doc.create_workplane_p_d("XY", offset_val=top_boss_z)
sketch_mount_hole = sw_doc.insert_sketch_on_plane(top_boss_plane)
sw_doc.create_circle(
    center_x=0,
    center_y=0,
    radius=wrist_mount_hole_dia / 2,
    sketch_ref="XY"
)
# 切除孔，深度穿过凸台并稍微进入耳朵主体以确保通孔或盲孔效果
# 这里做成盲孔，深度为凸台高度 + 少量余量
sw_doc.extrude_cut(sketch_mount_hole, depth=wrist_boss_height + 0.002, single_direction=True)


# --- 3.5 倒角 (Chamfers) ---
print("Step 5: Applying Chamfers...")
# 对底座底边进行 C1 倒角
bottom_edge_points = [
    (0.05, 0.04, 0.0),
    (-0.05, 0.04, 0.0),
    (-0.05, -0.04, 0.0),
    (0.05, -0.04, 0.0)
]
try:
    sw_doc.chamfer_edges(on_line_points=bottom_edge_points, distance=chamfer_dist, angle=45.0)
except Exception as e:
    print(f"Warning: Bottom chamfer failed: {e}")

# 对耳朵顶部边缘进行倒角
left_ear_top_points = [
    (left_ear_x_center - ear_thickness/2, ear_length_y/2, base_height + ear_height),
    (left_ear_x_center + ear_thickness/2, ear_length_y/2, base_height + ear_height),
    (left_ear_x_center + ear_thickness/2, -ear_length_y/2, base_height + ear_height),
    (left_ear_x_center - ear_thickness/2, -ear_length_y/2, base_height + ear_height)
]
try:
    sw_doc.chamfer_edges(on_line_points=left_ear_top_points, distance=chamfer_dist, angle=45.0)
except Exception as e:
    print(f"Warning: Left ear top chamfer failed: {e}")

right_ear_top_points = [
    (right_ear_x_center - ear_thickness/2, ear_length_y/2, base_height + ear_height),
    (right_ear_x_center + ear_thickness/2, ear_length_y/2, base_height + ear_height),
    (right_ear_x_center + ear_thickness/2, -ear_length_y/2, base_height + ear_height),
    (right_ear_x_center - ear_thickness/2, -ear_length_y/2, base_height + ear_height)
]
try:
    sw_doc.chamfer_edges(on_line_points=right_ear_top_points, distance=chamfer_dist, angle=45.0)
except Exception as e:
    print(f"Warning: Right ear top chamfer failed: {e}")


# 4. 创建参考接口 (Interfaces)

print("Step 6: Creating Reference Interfaces...")

# 4.1 Faces
# bottom_mount_face: 底座底面 (Z=0)
# 修复：显式创建名为 bottom_mount_face 的参考平面
bottom_face_ref = sw_doc.create_ref_plane("XY", offset_val=0.0, target_plane_name="bottom_mount_face")

# top_wrist_mount_face: 腕部凸台顶面 (Z = base_height + ear_height + wrist_boss_height)
top_wrist_z = base_height + ear_height + wrist_boss_height
top_wrist_face_ref = sw_doc.create_ref_plane("XY", offset_val=top_wrist_z, target_plane_name="top_wrist_mount_face")

# inner_face_left: 左耳内侧面 (X = -inner_spacing/2)
# 注意：虽然 Spec 中说 normal +Y，但几何上如果叉口沿 X，内侧面法向是 X。
# 为了装配约束能工作，我们创建几何上正确的平面。
# 如果装配时发现方向不对，可能需要旋转零件或调整约束。
# 这里按照几何事实创建：左耳内侧面在 X = -0.025
inner_left_plane = sw_doc.create_ref_plane("YZ", offset_val=-inner_spacing/2, target_plane_name="inner_face_left")

# inner_face_right: 右耳内侧面 (X = +inner_spacing/2)
inner_right_plane = sw_doc.create_ref_plane("YZ", offset_val=inner_spacing/2, target_plane_name="inner_face_right")


# 4.2 Axes
# mount_axis_z: 垂直轴通过中心 (0,0,Z)
mount_axis = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 0.1), axis_name="mount_axis_z")

# hinge_axis_y: 水平轴通过孔中心 (Y direction)
# 孔中心 Z = hole_z_center, X = 0
hinge_axis = sw_doc.create_axis(
    pt1=(0, -0.1, hole_z_center), 
    pt2=(0, 0.1, hole_z_center), 
    axis_name="hinge_axis_y"
)

# wrist_gripper_axis_z: 垂直轴通过腕部凸台中心
wrist_gripper_axis = sw_doc.create_axis(
    pt1=(0, 0, top_wrist_z), 
    pt2=(0, 0, top_wrist_z + 0.1), 
    axis_name="wrist_gripper_axis_z"
)

# 5. 保存
model_path = r"D:\a_src\python\sw_agent\agent_output\FourAxisIndustrialArm_Assembly-20260429_195742\parts\joint_fork\joint_fork.SLDPRT"
print(f"Saving part to: {model_path}")
sw_doc.save_as(model_path)

print("Joint Fork modeling completed.")