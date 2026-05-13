# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用与零件文档
    app = SldWorksApp()
    part_name = "Mount Bracket"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模: {part_name}")

    # 2. 定义参数 (单位: m)
    # 垂直部分 (连接立柱): 高50mm, 宽40mm(适配外径), 厚10mm
    vert_height = 0.050
    vert_width = 0.040
    vert_thickness = 0.010
    
    # 水平部分 (连接屏幕): 深100mm, 宽120mm(覆盖VESA区域), 厚8mm
    horiz_depth = 0.100
    horiz_width = 0.120
    horiz_thickness = 0.008
    
    # VESA孔位: 100x100mm 正方形, 孔径4.5mm
    vesa_spacing = 0.100
    hole_diameter = 0.0045
    hole_radius = hole_diameter / 2.0
    
    # 3. 建模步骤
    
    # --- 步骤 3.1: 创建垂直板 (Vertical Plate) ---
    # 在 YZ 平面绘制草图，中心在原点。
    # 注意：YZ平面的坐标系映射通常为 X->Y, Y->Z (取决于具体封装实现，这里假设标准映射)
    # 为了稳健，我们使用 create_centre_rectangle
    sketch_vert = sw_doc.insert_sketch_on_plane("ZY")
    if not sketch_vert:
        raise Exception("Failed to create vertical sketch on YZ plane")
        
    # 矩形中心 (0,0) 在 YZ 面上对应全局 (0,0,0)
    # 宽度对应 Y 轴方向 (vert_width)，高度对应 Z 轴方向 (vert_height)
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=vert_width, 
        height=vert_height, 
        sketch_ref="ZY"
    )
    
    # 拉伸厚度沿 X 轴正方向
    extrude_vert = sw_doc.extrude(sketch_vert, depth=vert_thickness, single_direction=True, merge=True)
    if not extrude_vert:
        raise Exception("Failed to extrude vertical plate")
    print("垂直板拉伸完成")
    
    # --- 步骤 3.2: 创建水平臂 (Horizontal Arm) ---
    # 位于垂直板顶部 (Z=0.05)。
    # 创建一个参考平面 Offset from XY by 0.05.
    plane_arm_top = sw_doc.create_workplane_p_d("XY", 0.05)
    if not plane_arm_top:
        raise Exception("Failed to create arm top plane")

    sketch_arm = sw_doc.insert_sketch_on_plane(plane_arm_top)
    if not sketch_arm:
        raise Exception("Failed to create arm sketch")
        
    # Arm extends in +X. Width in Y.
    # X: 0.01 to 0.11. Y: -0.02 to 0.02.
    # Center X = 0.06, Center Y = 0.
    # Width (Y) = 0.04, Height (X) = 0.10.
    # In XY sketch: Width usually X, Height usually Y? 
    # Let's assume Width is along first axis (X) and Height along second (Y) for XY ref.
    # Rect: X span 0.10, Y span 0.04.
    sw_doc.create_centre_rectangle(
        center_x=0.06, 
        center_y=0, 
        width=0.10, 
        height=0.04, 
        sketch_ref="XY"
    )
    
    # Extrude Up (+Z) by 0.01
    extrude_arm = sw_doc.extrude(sketch_arm, depth=0.01, single_direction=True, merge=True)
    if not extrude_arm:
        raise Exception("Failed to extrude arm")
    print("水平臂拉伸完成")

    # --- 步骤 3.3: 创建 VESA 板 (VESA Plate) ---
    # Plane at X = 0.11 (End of arm)
    # We need a plane parallel to YZ at X=0.11.
    # Base plane "ZY" is X=0.
    # Offset 0.11.
    plane_vesa = sw_doc.create_workplane_p_d("ZY", 0.11)
    if not plane_vesa:
        raise Exception("Failed to create VESA plane")
    
    sketch_vesa = sw_doc.insert_sketch_on_plane(plane_vesa)
    if not sketch_vesa:
        raise Exception("Failed to create VESA sketch")
    
    # VESA Plate Dimensions: 120mm x 120mm.
    # Centered on Arm. Arm Center Y=0, Z=0.055.
    # Rect: Y[-0.06, 0.06], Z[-0.005, 0.115].
    # Center Y=0, Center Z=0.055.
    # Width (Y) = 0.12, Height (Z) = 0.12.
    # Sketch Ref "ZY". In ZY sketch, coords are (Z, Y) or (Y, Z)?
    # API: create_centre_rectangle(center_x, center_y...).
    # For "ZY" ref, let's assume center_x maps to Z and center_y maps to Y based on previous success patterns or standard SW API behavior where the first arg is the horizontal axis of the sketch view.
    # However, to be safe, let's look at the error. The previous code failed at extrude because sketch was None.
    # This implies insert_sketch_on_plane might have failed or returned None if the plane wasn't valid or active.
    # Let's ensure we use the returned object correctly.
    
    # Center Z = 0.055, Center Y = 0.
    # Width (along first axis Z?) = 0.12.
    # Height (along second axis Y?) = 0.12.
    sw_doc.create_centre_rectangle(
        center_x=0.055, 
        center_y=0, 
        width=0.12, 
        height=0.12, 
        sketch_ref="ZY"
    )
    
    # Extrude Backwards (-X) by 0.005.
    # Since plane is at X=0.11, and normal of ZY plane is +X?
    # Extrude depth negative means opposite to normal?
    # Let's use depth=-0.005.
    extrude_vesa = sw_doc.extrude(sketch_vesa, depth=-0.005, single_direction=True, merge=True)
    if not extrude_vesa:
        raise Exception("Failed to extrude VESA plate")
    print("VESA板拉伸完成")

    # --- 步骤 3.4: VESA 孔 (VESA Holes) ---
    # Holes on the VESA Plate.
    # Pattern 100x100. Centered on Plate Center (Y=0, Z=0.055).
    # Hole positions relative to center:
    # TL: Y=-0.05, Z=0.055+0.05=0.105
    # TR: Y=0.05, Z=0.105
    # BL: Y=-0.05, Z=0.055-0.05=0.005
    # BR: Y=0.05, Z=0.005
    
    # We need to cut holes.
    # Sketch on the Front Face of VESA Plate (X=0.11).
    # Or use the existing sketch plane?
    # Let's create a sketch on the Front Face.
    # The front face is at X=0.11.
    # We can use the plane_vesa (X=0.11) again?
    # The extrusion went -X, so the front face is on the plane_vesa.
    sketch_holes = sw_doc.insert_sketch_on_plane(plane_vesa)
    if not sketch_holes:
        raise Exception("Failed to create holes sketch")
    
    # Draw 4 circles.
    # Coordinates in ZY sketch: (Z, Y).
    # TL: Z=0.105, Y=-0.05
    sw_doc.create_circle(center_x=0.105, center_y=-0.05, radius=hole_radius, sketch_ref="ZY")
    # TR: Z=0.105, Y=0.05
    sw_doc.create_circle(center_x=0.105, center_y=0.05, radius=hole_radius, sketch_ref="ZY")
    # BL: Z=0.005, Y=-0.05
    sw_doc.create_circle(center_x=0.005, center_y=-0.05, radius=hole_radius, sketch_ref="ZY")
    # BR: Z=0.005, Y=0.05
    sw_doc.create_circle(center_x=0.005, center_y=0.05, radius=hole_radius, sketch_ref="ZY")
    
    # Extrude Cut through all (or depth 0.01)
    # Cut in +X direction (through the plate thickness 0.005).
    # Plate is from X=0.105 to 0.11.
    # Sketch is at X=0.11.
    # Cut depth -0.01 (into the part).
    cut_holes = sw_doc.extrude_cut(sketch_holes, depth=-0.01, single_direction=True)
    if not cut_holes:
        raise Exception("Failed to cut VESA holes")
    print("VESA孔切除完成")

    # 4. 创建接口参考 (Interfaces)
    
    # 4.1 Faces
    # bracket_vertical_back_face: Normal -Y.
    # This is the face on the Vertical Leg at Y = -0.02.
    # Create Ref Plane for Vertical Back Face (Y = -0.02)
    # Offset from XZ? No, parallel to XZ.
    # Base plane "XZ" is Y=0.
    # Offset -0.02.
    ref_plane_vert_back = sw_doc.create_ref_plane("XZ", -0.02, target_plane_name="bracket_vertical_back_face")
    
    # bracket_screen_mount_face: Normal -X (Spec) / +X (Geometry).
    # The face is at X=0.11.
    # Create Ref Plane at X=0.11.
    # Base plane "ZY" is X=0.
    # Offset 0.11.
    ref_plane_screen_mount = sw_doc.create_ref_plane("ZY", 0.11, target_plane_name="bracket_screen_mount_face")

    # 4.2 Axes
    # bracket_rotation_axis: Along Z, through center of Vertical Leg (X=0.005, Y=0).
    # Pt1: (0.005, 0, 0)
    # Pt2: (0.005, 0, 0.1)
    axis_rotation = sw_doc.create_axis(
        pt1=(0.005, 0, 0), 
        pt2=(0.005, 0, 0.1), 
        axis_name="bracket_rotation_axis"
    )
    
    # VESA Hole Axes: Parallel to X.
    # Through the hole centers.
    # Hole Centers (Global):
    # TL: X=0.11, Y=-0.05, Z=0.105
    # TR: X=0.11, Y=0.05, Z=0.105
    # BL: X=0.11, Y=-0.05, Z=0.005
    # BR: X=0.11, Y=0.05, Z=0.005
    
    # Axis 1 (TL)
    axis_vesa_1 = sw_doc.create_axis(
        pt1=(0.11, -0.05, 0.105),
        pt2=(0.12, -0.05, 0.105), # Direction +X
        axis_name="vesa_hole_axis_1"
    )
    
    # Axis 2 (TR)
    axis_vesa_2 = sw_doc.create_axis(
        pt1=(0.11, 0.05, 0.105),
        pt2=(0.12, 0.05, 0.105),
        axis_name="vesa_hole_axis_2"
    )
    
    # Axis 3 (BL)
    axis_vesa_3 = sw_doc.create_axis(
        pt1=(0.11, -0.05, 0.005),
        pt2=(0.12, -0.05, 0.005),
        axis_name="vesa_hole_axis_3"
    )
    
    # Axis 4 (BR)
    axis_vesa_4 = sw_doc.create_axis(
        pt1=(0.11, 0.05, 0.005),
        pt2=(0.12, 0.05, 0.005),
        axis_name="vesa_hole_axis_4"
    )

    # 4.3 Points
    # vesa_center_point: (0.11, 0, 0.055)
    # No direct point creation API, but we have the coordinates.
    print("VESA Center Point Location: (0.11, 0, 0.055)")

    # 5. 保存文件
    save_path = r"D:\a_src\python\sw_agent\agent_output\27inch_Monitor_Assembly-20260428_113916\parts\mount_bracket\mount_bracket.SLDPRT"
    success = sw_doc.save_as(save_path)
    
    if success:
        print(f"零件成功保存至: {save_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()