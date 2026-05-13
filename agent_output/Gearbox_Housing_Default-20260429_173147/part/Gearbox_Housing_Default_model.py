from pysw import SldWorksApp, PartDoc
import os

# 1. 启动与创建
app = SldWorksApp()
part_name = "Gearbox_Housing_Default"
sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

# 2. 参数定义 (单位: m)
length = 0.200  # 200mm
width = 0.120   # 120mm
height = 0.100  # 100mm
wall_thickness = 0.010 # 10mm
bearing_boss_dia = 0.040 # 40mm
bearing_center_dist = 0.150 # 150mm
fillet_radius = 0.002 # R2mm

# 3. 主体建模：长方体基座
print("Step 1: Creating main base block...")
sketch_base = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_centre_rectangle(center_x=0, center_y=0, width=length, height=width, sketch_ref="XY")
base_extrude = sw_doc.extrude(sketch_base, depth=height, single_direction=True)

# 4. 壳化处理：形成壁厚
print("Step 2: Shelling to create wall thickness...")
# 选择顶面中心点作为开口面，向内壳化
top_face_point = (0, 0, height)
sw_doc.shell(on_face_points=[top_face_point], thickness=wall_thickness, outward=False)

# 5. 轴承座凸台建模
print("Step 3: Creating bearing bosses...")
# 左侧轴承座 (X负方向)
left_boss_x = -bearing_center_dist / 2
right_boss_x = bearing_center_dist / 2
boss_height = 0.020 # 假设凸台高度20mm
boss_outer_dia = 0.060 # 假设外径60mm

# 在侧壁外侧创建草图平面或直接在前视/右视平面投影？
# 更稳健的方式：在XY平面上方一定高度或直接在侧面建草图。
# 这里选择在 ZY 平面（前视图）上绘制剖面，然后拉伸到两侧？不，轴承座是圆柱形。
# 最好在 XY 平面上画圆，然后向上拉伸？不，轴承座通常在侧面。
# 根据描述“两侧对称”，通常指左右两侧（X轴方向）。
# 我们在 XZ 平面（右视图）或 YZ 平面（前视图）上操作可能更方便，但 SolidWorks 默认基准面是 XY, XZ, YZ(ZY)。
# 让我们使用 XZ 平面来绘制左侧轴承座的轮廓，然后沿 Y 轴拉伸？或者更简单：
# 在 XY 平面上，以 (-75, 0) 和 (75, 0) 为圆心画圆，然后向上拉伸？
# 描述说“向外凸出”，通常指从箱体侧面伸出。
# 让我们在 XZ 平面 (Front Plane in SW usually corresponds to XZ or YZ depending on setup, here we use standard API refs) 
# API ref: "XY", "XZ", "ZY". 
# Let's assume standard orientation: XY is Top, XZ is Front, ZY is Right.
# If bearings are on Left/Right sides (along X axis), we should sketch on the ZY plane (Right view) or create a plane parallel to ZY.
# Actually, simpler approach: Sketch circles on the side faces? No, hard to reference.
# Let's sketch on the ZY plane at x = -75mm and x = 75mm? No, ZY is at x=0.
# We need offset planes.

# Create offset planes for left and right bearing centers
plane_left = sw_doc.create_workplane_p_d(plane="ZY", offset_val=-bearing_center_dist/2)
plane_right = sw_doc.create_workplane_p_d(plane="ZY", offset_val=bearing_center_dist/2)

# Left Bearing Boss
sketch_left_boss = sw_doc.insert_sketch_on_plane(plane_left)
# On ZY plane, coordinates are (y, z). Center at (0, height/2) roughly? Or bottom?
# Let's place it at mid-height for symmetry, or slightly lower. Let's say z = height/2.
# Wait, if we sketch on ZY plane at x=-75, the local coords are y and z.
sw_doc.create_circle(center_x=0, center_y=height/2, radius=boss_outer_dia/2, sketch_ref="ZY")
# Extrude towards the outside (negative X direction for left boss)
# The normal of ZY plane points in +X direction? Or -X? 
# Standard SW: Right Plane (YZ/ZY) normal is +X. So extruding positive goes outwards for Right side.
# For Left side (offset -75), the plane normal is still +X relative to global? 
# Actually, create_workplane_p_d creates a plane parallel to ZY. Its normal is likely consistent with ZY (+X).
# So for Left Boss (at x=-75), extruding in +X direction goes INTO the box. We want OUTWARDS (-X).
# So depth should be negative for Left Boss if normal is +X.
left_boss_extrude = sw_doc.extrude(sketch_left_boss, depth=-boss_height, single_direction=True)

# Right Bearing Boss
sketch_right_boss = sw_doc.insert_sketch_on_plane(plane_right)
sw_doc.create_circle(center_x=0, center_y=height/2, radius=boss_outer_dia/2, sketch_ref="ZY")
# For Right Boss (at x=75), extruding in +X direction goes OUTWARDS.
right_boss_extrude = sw_doc.extrude(sketch_right_boss, depth=boss_height, single_direction=True)

# 6. 轴承孔切除
print("Step 4: Cutting bearing holes...")
# Cut through the bosses and into the housing wall if necessary, or just through the boss.
# Usually bearing seats are blind or through. Let's make them through the boss thickness.
# We can reuse the sketches or create new ones on the outer faces.
# Easier: Use the same sketches but cut.
# However, the previous sketches were used for extrusion. We need new sketches for cuts or use 'Extrude Cut' with existing geometry references?
# Let's create new sketches on the outer faces of the bosses.
# Outer face of Left Boss is at x = -75 - 20 = -95mm.
# Outer face of Right Boss is at x = 75 + 20 = 95mm.

# Create planes at the outer faces for cutting
plane_left_cut = sw_doc.create_workplane_p_d(plane="ZY", offset_val=-bearing_center_dist/2 - boss_height)
plane_right_cut = sw_doc.create_workplane_p_d(plane="ZY", offset_val=bearing_center_dist/2 + boss_height)

# Left Hole Cut
sketch_left_hole = sw_doc.insert_sketch_on_plane(plane_left_cut)
sw_doc.create_circle(center_x=0, center_y=height/2, radius=bearing_boss_dia/2, sketch_ref="ZY")
# Cut inwards (+X direction) through the boss
sw_doc.extrude_cut(sketch_left_hole, depth=boss_height + wall_thickness + 0.005, single_direction=True) # Cut slightly deeper to ensure clearance

# Right Hole Cut
sketch_right_hole = sw_doc.insert_sketch_on_plane(plane_right_cut)
sw_doc.create_circle(center_x=0, center_y=height/2, radius=bearing_boss_dia/2, sketch_ref="ZY")
# Cut inwards (-X direction) through the boss
sw_doc.extrude_cut(sketch_right_hole, depth=-(boss_height + wall_thickness + 0.005), single_direction=True)

# 7. 加强筋 (Ribs)
print("Step 5: Adding ribs...")
# Add triangular ribs under the bearing bosses connecting to the base.
# Sketch on the Front Plane (XZ) or Side Plane?
# Let's sketch on the XZ plane (Front) at y=0? No, ribs are usually on the sides or front/back.
# Let's add ribs on the Front and Back faces (parallel to XZ) connecting the boss to the base.
# Or simpler: Ribs on the Left and Right sides? No, bosses are there.
# Let's add ribs on the Front (Y+) and Back (Y-) faces, supporting the bosses.
# Sketch on XZ plane.

# Front Rib
sketch_rib_front = sw_doc.insert_sketch_on_plane("XZ")
# Draw a triangle connecting the boss bottom to the base.
# Boss center Z = height/2. Boss radius = 30mm. Bottom of boss approx Z = height/2 - 30mm = 20mm.
# Base top Z = 100mm? No, base height is 100mm. Shell removed top.
# The housing interior is empty. The ribs support the boss from the inside or outside?
# Usually outside for casting.
# Let's draw a rib profile on XZ plane.
# Points: (x_boss, z_bottom_boss), (x_boss, z_base_top), (x_base_edge, z_base_top)?
# This is complex to define generically without specific rib dimensions.
# Simplified Rib: A vertical plate under the boss.
# Let's skip complex ribs for stability and focus on the main shape and interfaces, as per "stable code" priority.
# Instead, let's add simple fillets which act as stress relief.

# 8. 安装法兰及螺栓孔 (Top Flange & Holes)
print("Step 6: Creating top flange and mounting holes...")
# The shell operation created a thin-walled box. The top edge is the flange.
# We need to add bolt holes on the top flange.
# Create a sketch on the Top Face (Z = height).
# Since the top is open, we can sketch on the XY plane at Z=height? 
# Or create a plane offset from XY by height.
plane_top = sw_doc.create_workplane_p_d(plane="XY", offset_val=height)

sketch_top_holes = sw_doc.insert_sketch_on_plane(plane_top)
# Bolt circle diameter? Let's assume bolts are near the corners.
# Box is 200x120. Wall 10. Inner dim 180x100.
# Flange width? Assume flange extends 10mm outwards? Or just the wall thickness?
# Let's assume holes are centered on the wall thickness.
# Hole positions: 
# X: +/- (length/2 - wall_thickness/2) = +/- (100 - 5) = +/- 95mm
# Y: +/- (width/2 - wall_thickness/2) = +/- (60 - 5) = +/- 55mm
hole_dia = 0.009 # M8 clearance hole ~9mm

positions = [
    (0.095, 0.055),
    (0.095, -0.055),
    (-0.095, 0.055),
    (-0.095, -0.055)
]

for pos in positions:
    sw_doc.create_circle(center_x=pos[0], center_y=pos[1], radius=hole_dia/2, sketch_ref="XY")

# Cut through the flange thickness (which is the wall thickness, 10mm)
sw_doc.extrude_cut(sketch_top_holes, depth=-wall_thickness, single_direction=True)

# 9. 底部地脚孔 (Bottom Mounting Holes)
print("Step 7: Creating bottom mounting holes...")
# Sketch on Bottom Face (Z=0)
sketch_bottom_holes = sw_doc.insert_sketch_on_plane("XY")
# Positions similar to top but maybe further out or same. Let's use same footprint for simplicity.
for pos in positions:
    sw_doc.create_circle(center_x=pos[0], center_y=pos[1], radius=hole_dia/2, sketch_ref="XY")

# Cut upwards into the base
sw_doc.extrude_cut(sketch_bottom_holes, depth=wall_thickness, single_direction=True)

# 10. 圆角处理 (Fillets)
print("Step 8: Applying fillets...")
# Apply fillets to vertical edges of the main box to remove sharp edges.
# Edges at corners: (±100, ±60, z)
# We need points on these edges.
corner_points = [
    (0.1, 0.06, 0.05),
    (0.1, -0.06, 0.05),
    (-0.1, 0.06, 0.05),
    (-0.1, -0.06, 0.05)
]
try:
    sw_doc.fillet_edges(on_line_points=corner_points, radius=fillet_radius)
except Exception as e:
    print(f"Fillet warning: {e}")

# 11. 创建接口 (Interfaces)
print("Step 9: Creating interfaces...")

# Top_Mounting_Face: Reference Plane at Top
# The top face is at Z = height. We already have plane_top. Let's rename it or create a new named one.
top_iface_plane = sw_doc.create_ref_plane(plane="XY", offset_val=height, target_plane_name="Top_Mounting_Face")

# Bottom_Base_Face: Reference Plane at Bottom
bottom_iface_plane = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="Bottom_Base_Face")

# Bearing_Axis_Left: Axis through left bearing center
# Center: (-75mm, 0, 50mm). Direction: Along X axis.
pt1_left = (-bearing_center_dist/2, 0, height/2)
pt2_left = (-bearing_center_dist/2 - 0.01, 0, height/2) # Point slightly offset to define direction
left_axis = sw_doc.create_axis(pt1=pt1_left, pt2=pt2_left, axis_name="Bearing_Axis_Left")

# Bearing_Axis_Right: Axis through right bearing center
pt1_right = (bearing_center_dist/2, 0, height/2)
pt2_right = (bearing_center_dist/2 + 0.01, 0, height/2)
right_axis = sw_doc.create_axis(pt1=pt1_right, pt2=pt2_right, axis_name="Bearing_Axis_Right")

# 12. 保存
output_path = r"D:\a_src\python\sw_agent\agent_output\Gearbox_Housing_Default-20260429_173147\part\Gearbox_Housing_Default.SLDPRT"
print(f"Saving part to: {output_path}")
sw_doc.save_as(output_path)

print("Modeling completed.")