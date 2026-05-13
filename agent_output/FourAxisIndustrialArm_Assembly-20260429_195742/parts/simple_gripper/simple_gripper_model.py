from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "SimpleGripper"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"[INFO] 开始建模零件: {part_name}")

    # 定义尺寸 (单位: m)
    overall_width = 0.060   # 60mm
    overall_height = 0.040  # 40mm
    depth = 0.030           # 30mm
    opening_width = 0.020   # 20mm
    mount_hole_dia = 0.020  # 20mm
    chamfer_dist = 0.001    # C1
    
    # 计算几何参数
    half_width = overall_width / 2
    half_opening = opening_width / 2
    
    # U型结构参数
    base_height = 0.010     # 底板厚度 10mm
    side_height = overall_height # 侧板高度 40mm
    
    print("[INFO] 步骤 1/5: 创建U型主体")
    # 2. 主体建模：U型支架
    # 在 XZ 平面绘制 U 型轮廓
    sketch_profile = sw_doc.insert_sketch_on_plane("XZ")
    
    # 轮廓点 (X, Z):
    # 从左下角开始，逆时针绘制封闭轮廓
    points = [
        (-half_width, 0),                  # 左下外角
        (-half_width, side_height),        # 左上外角
        (-half_opening, side_height),      # 左上内角
        (-half_opening, base_height),      # 左内底角
        (half_opening, base_height),       # 右内底角
        (half_opening, side_height),       # 右上内角
        (half_width, side_height),         # 右上外角
        (half_width, 0),                   # 右下外角
        (-half_width, 0)                   # 闭合回起点
    ]
    
    sw_doc.create_lines(points, "XZ")
    
    # 拉伸生成实体 (沿 Y 轴正向)
    body = sw_doc.extrude(sketch_profile, depth=depth, single_direction=True)
    print("[INFO] 主体拉伸完成")

    print("[INFO] 步骤 2/5: 创建安装凸台")
    # 3. 安装特征：底部凸台
    boss_dia = 0.040
    boss_height = 0.005
    
    # 在底面 (XY 平面, Z=0) 创建草图
    sketch_boss = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(center_x=0, center_y=0, radius=boss_dia/2, sketch_ref="XY")
    
    # 向上拉伸凸台 (Z+)
    boss_feat = sw_doc.extrude(sketch_boss, depth=boss_height, single_direction=True)
    print("[INFO] 安装凸台创建完成")

    print("[INFO] 步骤 3/5: 创建安装孔")
    # 在安装凸台和底板上打孔
    # 策略：在 XY 平面 (Z=0) 画圆，然后向 +Z 方向切除，穿透凸台和底板
    # 总厚度 = boss_height (0.005) + base_height (0.010) = 0.015m
    # 切除深度设为 0.020m 以确保完全穿透
    
    sketch_hole = sw_doc.insert_sketch_on_plane("XY") 
    sw_doc.create_circle(center_x=0, center_y=0, radius=mount_hole_dia/2, sketch_ref="XY")
    
    # 关键修正：之前使用负深度向下切，但实体在 Z>0 区域，所以必须向 +Z 切
    cut_depth = 0.020 
    hole_feat = sw_doc.extrude_cut(sketch_hole, depth=cut_depth, single_direction=True)
    print("[INFO] 安装孔创建完成")

    print("[INFO] 步骤 4/5: 定义装配接口")
    # 4. 接口定义 (Reference Geometry)
    
    # 4.1 面接口
    # mount_bottom_face: 底面 (Z=0)
    ref_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="mount_bottom_face")
    
    # jaw_inner_face_left/right: 用于装配参考的平面
    ref_jaw_left = sw_doc.create_ref_plane(plane="YZ", offset_val=-half_opening, target_plane_name="jaw_inner_face_left_ref")
    ref_jaw_right = sw_doc.create_ref_plane(plane="YZ", offset_val=half_opening, target_plane_name="jaw_inner_face_right_ref")

    # 4.2 轴接口
    # mount_axis_z: 穿过中心 (0,0) 沿 Z 轴的轴
    axis_mount = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 0.1), axis_name="mount_axis_z")
    
    print("[INFO] 接口定义完成")

    print("[INFO] 步骤 5/5: 应用倒角")
    # 5. 倒角处理 (C1)
    # 选取顶部边缘和外部垂直边缘的中点进行倒角
    
    # 顶部四条边中点
    top_edges_points = [
        (-half_width, depth/2, side_height), 
        (half_width, depth/2, side_height),  
        (0, 0, side_height),                 
        (0, depth, side_height)              
    ]
    
    # 外部垂直棱边中点
    vert_edges_points = [
        (-half_width, 0, side_height/2),     
        (-half_width, depth, side_height/2), 
        (half_width, 0, side_height/2),      
        (half_width, depth, side_height/2)   
    ]
    
    try:
        sw_doc.chamfer_edges(on_line_points=top_edges_points + vert_edges_points, distance=chamfer_dist, angle=45.0)
        print("[INFO] 倒角应用完成")
    except Exception as e:
        print(f"[WARN] 倒角应用可能部分失败: {e}")

    # 6. 保存
    output_path = r"D:\a_src\python\sw_agent\agent_output\FourAxisIndustrialArm_Assembly-20260429_195742\parts\simple_gripper\simple_gripper.SLDPRT"
    print(f"[INFO] 正在保存零件至: {output_path}")
    success = sw_doc.save_as(output_path)
    
    if success:
        print(f"[SUCCESS] 零件 {part_name} 成功保存")
    else:
        print(f"[ERROR] 零件 {part_name} 保存失败")

if __name__ == "__main__":
    main()