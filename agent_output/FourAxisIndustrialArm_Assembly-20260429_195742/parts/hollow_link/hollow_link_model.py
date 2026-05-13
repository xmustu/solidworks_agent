from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    sw_doc = PartDoc(app.createAndActivate_sw_part("HollowLink"))

    # 2. 参数定义 (单位: m)
    # 根据 review_comments，宽度调整为 48mm 以匹配 50mm 叉耳间距
    width = 0.048      # 48 mm
    thickness = 0.020  # 20 mm
    length = 0.300     # 300 mm (通用模板取最大长度)
    
    bearing_seat_od = 0.040 # 40 mm
    bearing_seat_radius = bearing_seat_od / 2
    hinge_hole_dia = 0.020  # 20 mm
    hinge_hole_radius = hinge_hole_dia / 2
    
    # 轴承座长度：设为 48mm (与连杆同宽)，居中分布
    # 这样轴承座端面与连杆侧面平齐或略内缩，取决于具体设计。
    # 这里设总长 48mm，双向拉伸各 24mm。
    bearing_seat_half_len = width / 2 

    # 3. 建模步骤

    # Step 1: 创建连杆主体 (Rectangular Beam)
    # 在 ZY 平面绘制矩形 (KB规定平面名为 "ZY", "XY", "XZ")
    # ZY 平面的法向是 X 轴，符合沿 X 轴拉伸的要求
    print("Step 1: Creating main beam body...")
    sketch_body = sw_doc.insert_sketch_on_plane("ZY")
    # 中心在原点 (0,0,0) 的矩形
    # 在 ZY 草图中，x 对应全局 Y，y 对应全局 Z (根据 KB 坐标修正提示，但 create_centre_rectangle 使用 center_x, center_y)
    # KB 提示: ZY 可能对 x 做反号处理。我们只需传入正确的几何尺寸。
    # 宽 48mm (Y方向), 高 20mm (Z方向)
    # 在 ZY 草图里，center_x 对应 Y 轴位置，center_y 对应 Z 轴位置? 
    # 通常 SW API 中，草图坐标系是局部的。
    # 让我们假设 create_centre_rectangle 的 width/height 对应草图平面的两个轴。
    # ZY 平面：第一轴通常是 Z 或 Y。
    # 为了安全，我们依赖 extrude 的方向。
    sw_doc.create_centre_rectangle(center_x=0, center_y=0, width=width, height=thickness, sketch_ref="ZY")
    # 拉伸长度 300mm，沿 X 轴 (ZY 的法向)
    body_extrude = sw_doc.extrude(sketch_body, depth=length, single_direction=True, merge=True)
    
    # Step 2: 创建起始端轴承座 (Start End Bearing Seat)
    # 位置: X = 0 处
    # 轴线沿 Y 轴。
    # 草图平面：XZ 平面 (法向为 Y)
    print("Step 2: Creating start bearing seat...")
    sketch_seat_start = sw_doc.insert_sketch_on_plane("XZ")
    # 在 XZ 平面画圆，圆心 (0,0) 对应全局 (X=0, Z=0). 
    # XZ 草图中，x 对应全局 X，y 对应全局 Z。
    sw_doc.create_circle(center_x=0, center_y=0, radius=bearing_seat_radius, sketch_ref="XZ")
    # 沿 Y 轴双向拉伸，总长 48mm (单边 24mm)
    seat_start_extrude = sw_doc.extrude(sketch_seat_start, depth=bearing_seat_half_len, single_direction=False, merge=True)
    
    # Step 3: 创建结束端轴承座 (End End Bearing Seat)
    # 位置: X = length (0.3m)
    print("Step 3: Creating end bearing seat...")
    sketch_seat_end = sw_doc.insert_sketch_on_plane("XZ")
    # 圆心 X = length, Z = 0
    sw_doc.create_circle(center_x=length, center_y=0, radius=bearing_seat_radius, sketch_ref="XZ")
    seat_end_extrude = sw_doc.extrude(sketch_seat_end, depth=bearing_seat_half_len, single_direction=False, merge=True)

    # Step 4: 钻铰链孔 (Hinge Holes)
    # 沿 Y 轴，穿过轴承座。
    print("Step 4: Drilling hinge holes...")
    # 起始端孔
    sketch_hole_start = sw_doc.insert_sketch_on_plane("XZ")
    sw_doc.create_circle(center_x=0, center_y=0, radius=hinge_hole_radius, sketch_ref="XZ")
    # 双向切除，确保穿透
    sw_doc.extrude_cut(sketch_hole_start, depth=0.05, single_direction=False)
    
    # 结束端孔
    sketch_hole_end = sw_doc.insert_sketch_on_plane("XZ")
    sw_doc.create_circle(center_x=length, center_y=0, radius=hinge_hole_radius, sketch_ref="XZ")
    sw_doc.extrude_cut(sketch_hole_end, depth=0.05, single_direction=False)

    # Step 5: 中空减重 (Hollowing)
    # 使用 Shell 命令，选择顶面 (Z+ face)
    print("Step 5: Hollowing the link...")
    try:
        # 顶面中心点附近
        sw_doc.shell(on_face_points=[(length/2, 0, thickness/2)], thickness=0.004, outward=False)
    except Exception as e:
        print(f"Shell operation failed or skipped: {e}")

    # Step 6: 倒角 (Chamfers)
    print("Step 6: Applying chamfers...")
    chamfer_dist = 0.001 # 1mm
    
    # 选取连杆主体长边的中点附近的边
    pt1 = (length/2, width/2, thickness/2)
    pt2 = (length/2, -width/2, thickness/2)
    pt3 = (length/2, width/2, -thickness/2)
    pt4 = (length/2, -width/2, -thickness/2)
    
    try:
        sw_doc.chamfer_edges(on_line_points=[pt1, pt2, pt3, pt4], distance=chamfer_dist, angle=45.0)
    except Exception as e:
        print(f"Chamfer operation warning: {e}")

    # 7. 创建接口 (Interfaces)
    print("Step 7: Creating reference axes and planes for interfaces...")
    
    # Start Hinge Axis (Y-axis at X=0)
    sw_doc.create_axis(pt1=(0, -0.1, 0), pt2=(0, 0.1, 0), axis_name="start_hinge_axis_y")
    
    # End Hinge Axis (Y-axis at X=length)
    sw_doc.create_axis(pt1=(length, -0.1, 0), pt2=(length, 0.1, 0), axis_name="end_hinge_axis_y")
    
    # Longitudinal Axis (X-axis)
    sw_doc.create_axis(pt1=(0, 0, 0), pt2=(length, 0, 0), axis_name="longitudinal_axis_x")
    
    # Reference Planes
    # Plane at X=0 (Start Face) - Use "ZY" plane offset by 0
    sw_doc.create_ref_plane(plane="ZY", offset_val=0, target_plane_name="ref_plane_start_face")
    # Plane at X=length (End Face)
    sw_doc.create_ref_plane(plane="ZY", offset_val=length, target_plane_name="ref_plane_end_face")
    # Plane at Y=width/2 (Side +Y) - Use "XZ" plane offset by width/2
    sw_doc.create_ref_plane(plane="XZ", offset_val=width/2, target_plane_name="ref_plane_side_y_plus")
    # Plane at Y=-width/2 (Side -Y)
    sw_doc.create_ref_plane(plane="XZ", offset_val=-width/2, target_plane_name="ref_plane_side_y_minus")

    # 8. 保存
    model_path = r"D:\a_src\python\sw_agent\agent_output\FourAxisIndustrialArm_Assembly-20260429_195742\parts\hollow_link\hollow_link.SLDPRT"
    print(f"Saving part to: {model_path}")
    sw_doc.save_as(model_path)

if __name__ == "__main__":
    main()