from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "Gearbox_Housing_Closed_Top"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 参数定义 (单位: m)
    # 修正坐标系以容纳轴承中心距：
    # X: Width (120mm) -> Range [-0.06, 0.06]
    # Y: Length (200mm) -> Range [-0.10, 0.10]
    # Z: Height (100mm) -> Range [0, 0.10]
    length_y = 0.200      # 长 200mm (Y轴)
    width_x = 0.120       # 宽 120mm (X轴)
    height_z = 0.100      # 高 100mm (Z轴)
    wall_thickness = 0.010 # 壁厚 10mm
    
    bearing_boss_dia = 0.060 # 轴承座外径 60mm
    bearing_hole_dia = 0.040 # 轴承孔径 40mm
    bearing_center_dist = 0.150 # 轴承中心距 150mm
    bearing_boss_height = 0.020 # 轴承座凸出高度 20mm
    
    rib_thickness = 0.008 # 加强筋厚度 8mm
    fillet_radius = 0.002 # 圆角半径 R2mm
    
    mount_hole_dia = 0.008 # M8地脚孔直径 8mm
    mount_hole_offset_edge = 0.015 # 孔边距 15mm

    print(f"开始建模零件: {part_name}")

    # 2. 主体基座建模 (XY平面拉伸)
    # 在XY平面绘制矩形轮廓
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    # 中心矩形，宽(X)=120mm, 长(Y)=200mm
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=width_x, 
        height=length_y, 
        sketch_ref="XY"
    )
    # 拉伸高度 100mm (+Z)
    extrude_base = sw_doc.extrude(sketch_base, depth=height_z, single_direction=True, merge=True)
    print("主体基座拉伸完成")

    # 3. 内部空腔 (Extrude Cut)
    # 在顶面 (Z=0.1) 创建草图进行切除
    top_plane = sw_doc.create_workplane_p_d("XY", height_z)
    
    sketch_cavity = sw_doc.insert_sketch_on_plane(top_plane)
    # 内腔尺寸：外尺寸减去两倍壁厚
    inner_width_x = width_x - 2 * wall_thickness
    inner_length_y = length_y - 2 * wall_thickness
    
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=inner_width_x,
        height=inner_length_y,
        sketch_ref="XY"
    )
    # 向下切除，深度为 height - wall_thickness (保留底部壁厚)
    cut_depth = height_z - wall_thickness
    sw_doc.extrude_cut(sketch_cavity, depth=-cut_depth, single_direction=True)
    print("内部空腔切除完成")

    # 4. 轴承座凸台
    # 左侧轴承座 (X负方向侧面, X = -width_x/2 = -0.06)
    # 轴承中心位置：Y = +bearing_center_dist/2 = +0.075, Z = height_z/2 = 0.05
    left_face_plane = sw_doc.create_workplane_p_d("ZY", -width_x/2)
    
    bearing_y_pos_left = bearing_center_dist / 2
    bearing_z_pos = height_z / 2

    sketch_bearing_left = sw_doc.insert_sketch_on_plane(left_face_plane)
    # 在 ZY 平面上，create_circle 的 center_x 对应 Global Y, center_y 对应 Global Z
    sw_doc.create_circle(
        center_x=bearing_y_pos_left, 
        center_y=bearing_z_pos,    
        radius=bearing_boss_dia/2,
        sketch_ref="ZY"
    )
    # 向外凸出 (向 X 负方向)。ZY 平面法向通常为 +X。所以 depth 为负。
    sw_doc.extrude(sketch_bearing_left, depth=-bearing_boss_height, single_direction=True, merge=True)
    print("左侧轴承座凸台完成")

    # 右侧轴承座 (X正方向侧面, X = +width_x/2 = 0.06)
    # 轴承中心位置：Y = -bearing_center_dist/2 = -0.075, Z = 0.05
    right_face_plane = sw_doc.create_workplane_p_d("ZY", width_x/2)
    
    bearing_y_pos_right = -bearing_center_dist / 2

    sketch_bearing_right = sw_doc.insert_sketch_on_plane(right_face_plane)
    sw_doc.create_circle(
        center_x=bearing_y_pos_right, 
        center_y=bearing_z_pos,    
        radius=bearing_boss_dia/2,
        sketch_ref="ZY"
    )
    # 向外凸出 (向 X 正方向)。ZY 平面法向为 +X。所以 depth 为正。
    sw_doc.extrude(sketch_bearing_right, depth=bearing_boss_height, single_direction=True, merge=True)
    print("右侧轴承座凸台完成")

    # 5. 轴承孔加工
    # 左侧孔
    left_boss_end_plane = sw_doc.create_workplane_p_d("ZY", -width_x/2 - bearing_boss_height)
    
    sketch_hole_left = sw_doc.insert_sketch_on_plane(left_boss_end_plane)
    sw_doc.create_circle(
        center_x=bearing_y_pos_left,
        center_y=bearing_z_pos,
        radius=bearing_hole_dia/2,
        sketch_ref="ZY"
    )
    # 切除深度：穿过凸台和侧壁，进入内部空腔。
    # 凸台 20mm + 壁厚 10mm = 30mm。切深 40mm 确保通透。
    cut_depth_bearing = 0.040 
    # 方向：向 +X (进入箱体内部)。平面法向 +X。Depth 正。
    sw_doc.extrude_cut(sketch_hole_left, depth=cut_depth_bearing, single_direction=True)
    print("左侧轴承孔完成")

    # 右侧孔
    right_boss_end_plane = sw_doc.create_workplane_p_d("ZY", width_x/2 + bearing_boss_height)
    
    sketch_hole_right = sw_doc.insert_sketch_on_plane(right_boss_end_plane)
    sw_doc.create_circle(
        center_x=bearing_y_pos_right,
        center_y=bearing_z_pos,
        radius=bearing_hole_dia/2,
        sketch_ref="ZY"
    )
    # 方向：向 -X (进入箱体内部)。平面法向 +X。Depth 负。
    sw_doc.extrude_cut(sketch_hole_right, depth=-cut_depth_bearing, single_direction=True)
    print("右侧轴承孔完成")

    # 6. 加强筋 (Ribs)
    # 在侧壁内表面添加三角形加强筋
    # 左侧内壁 X = -width_x/2 + wall_thickness = -0.06 + 0.01 = -0.05
    left_inner_wall_plane = sw_doc.create_workplane_p_d("ZY", -width_x/2 + wall_thickness)
    
    sketch_rib_left = sw_doc.insert_sketch_on_plane(left_inner_wall_plane)
    # 三角形顶点: (Y=0.075, Z=0.05), 底角: (Y=0.075, Z=0), (Y=0.050, Z=0)
    # 注意：在 ZY 平面草图中，X 对应 Global Y, Y 对应 Global Z.
    pts_rib_left = [
        (bearing_y_pos_left, bearing_z_pos), # Top
        (bearing_y_pos_left, 0),             # Bottom Center
        (bearing_y_pos_left - 0.025, 0)      # Bottom Outer (towards center Y=0? No, towards edge? Y=0.075 is close to edge Y=0.1. So 0.05 is towards center.)
    ]
    sw_doc.create_lines(pts_rib_left, sketch_ref="ZY")
    # 闭合轮廓
    sw_doc.create_lines([(bearing_y_pos_left - 0.025, 0), (bearing_y_pos_left, bearing_z_pos)], sketch_ref="ZY")
    
    # 拉伸成筋，厚度 8mm。向 +X 拉伸 (进入箱体内部)
    sw_doc.extrude(sketch_rib_left, depth=rib_thickness, single_direction=True, merge=True)
    print("左侧加强筋完成")

    # 右侧内壁 X = width_x/2 - wall_thickness = 0.06 - 0.01 = 0.05
    right_inner_wall_plane = sw_doc.create_workplane_p_d("ZY", width_x/2 - wall_thickness)
    
    sketch_rib_right = sw_doc.insert_sketch_on_plane(right_inner_wall_plane)
    # 三角形顶点: (Y=-0.075, Z=0.05), 底角: (Y=-0.075, Z=0), (Y=-0.050, Z=0)
    pts_rib_right = [
        (bearing_y_pos_right, bearing_z_pos), 
        (bearing_y_pos_right, 0),             
        (bearing_y_pos_right + 0.025, 0)      # Towards center (Y=0)
    ]
    sw_doc.create_lines(pts_rib_right, sketch_ref="ZY")
    sw_doc.create_lines([(bearing_y_pos_right + 0.025, 0), (bearing_y_pos_right, bearing_z_pos)], sketch_ref="ZY")
    
    # 向 -X 拉伸 (进入箱体内部)
    sw_doc.extrude(sketch_rib_right, depth=-rib_thickness, single_direction=True, merge=True)
    print("右侧加强筋完成")

    # 7. 地脚安装孔 (Bottom)
    # 底部四角 M8 孔。
    bottom_plane = sw_doc.create_workplane_p_d("XY", 0)
    sketch_mount = sw_doc.insert_sketch_on_plane(bottom_plane)
    
    # 孔位置：距离边缘 15mm。
    # X 范围: -0.06 to 0.06. Hole X: +/- (0.06 - 0.015) = +/- 0.045m.
    # Y 范围: -0.10 to 0.10. Hole Y: +/- (0.10 - 0.015) = +/- 0.085m.
    
    hole_x = 0.045
    hole_y = 0.085
    
    sw_doc.create_circle(hole_x, hole_y, mount_hole_dia/2, "XY")
    sw_doc.create_circle(-hole_x, hole_y, mount_hole_dia/2, "XY")
    sw_doc.create_circle(hole_x, -hole_y, mount_hole_dia/2, "XY")
    sw_doc.create_circle(-hole_x, -hole_y, mount_hole_dia/2, "XY")
    
    # 向上切除 (进入箱体)，深度等于壁厚
    sw_doc.extrude_cut(sketch_mount, depth=wall_thickness, single_direction=True)
    print("地脚孔完成")

    # 8. 接口定义
    # Bottom_Base_Face: 底面 (Z=0)
    sw_doc.create_ref_plane("XY", 0, target_plane_name="Bottom_Base_Face")
    
    # Bearing_Axis_Left: 左侧轴承孔轴线
    # 轴通过点 (-0.06, 0.075, 0.05) 和 (-0.10, 0.075, 0.05)
    sw_doc.create_axis(
        pt1=(-width_x/2, bearing_y_pos_left, bearing_z_pos),
        pt2=(-width_x/2 - 0.04, bearing_y_pos_left, bearing_z_pos),
        axis_name="Bearing_Axis_Left"
    )
    
    # Bearing_Axis_Right: 右侧轴承孔轴线
    # 轴通过点 (0.06, -0.075, 0.05) 和 (0.10, -0.075, 0.05)
    sw_doc.create_axis(
        pt1=(width_x/2, bearing_y_pos_right, bearing_z_pos),
        pt2=(width_x/2 + 0.04, bearing_y_pos_right, bearing_z_pos),
        axis_name="Bearing_Axis_Right"
    )

    # 9. 保存
    output_path = r"D:\a_src\python\sw_agent\agent_output\Gearbox_Housing_Closed_Top-20260429_173604\part\Gearbox_Housing_Closed_Top.SLDPRT"
    sw_doc.save_as(output_path)
    print(f"模型已保存至: {output_path}")

if __name__ == "__main__":
    main()
