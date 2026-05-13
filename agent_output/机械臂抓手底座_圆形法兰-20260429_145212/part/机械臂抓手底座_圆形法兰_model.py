# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc
import math

def main():
    # 1. 初始化应用与零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "机械臂抓手底座_圆形法兰"
    print(f"创建并激活零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 定义参数 (单位: mm -> m)
    # 主体尺寸
    outer_diameter_mm = 80.0
    thickness_mm = 10.0
    
    # 中心止口尺寸
    center_bore_dia_mm = 30.0
    center_bore_depth_mm = 5.0
    
    # 安装孔尺寸
    hole_dia_mm = 5.0
    pcd_mm = 50.0  # Pitch Circle Diameter
    num_holes = 4
    
    # 倒角尺寸
    chamfer_dist_mm = 1.0
    
    # 转换为米
    outer_radius_m = outer_diameter_mm / 2000.0
    thickness_m = thickness_mm / 1000.0
    center_bore_radius_m = center_bore_dia_mm / 2000.0
    center_bore_depth_m = center_bore_depth_mm / 1000.0
    hole_radius_m = hole_dia_mm / 2000.0
    pcd_radius_m = pcd_mm / 2000.0
    chamfer_dist_m = chamfer_dist_mm / 1000.0
    
    try:
        # 3. 建模步骤
        
        # Step 1: 创建主体圆盘 (在 XY 平面)
        print("Step 1: 创建主体圆盘草图...")
        sketch_base = sw_doc.insert_sketch_on_plane("XY")
        sw_doc.create_circle(center_x=0, center_y=0, radius=outer_radius_m, sketch_ref="XY")
        
        print("Step 1: 拉伸主体...")
        # 向 Z 轴正方向拉伸厚度
        extrude_base = sw_doc.extrude(sketch_base, depth=thickness_m, single_direction=True, merge=True)
        
        # Step 2: 创建中心定位止口 (在顶面，即 Z = thickness_m 处)
        # 为了在顶面画草图，我们需要一个参考平面或者直接在顶面上操作。
        # 这里我们创建一个偏移平面作为草图基准，或者直接利用 Top Plane (如果API支持选择面)。
        # 根据 API 描述，insert_sketch_on_plane 接受 "XY", "XZ", "ZY" 或自定义平面名。
        # 我们可以先创建一个位于顶部的参考平面。
        
        print("Step 2: 创建顶部参考平面用于止口...")
        top_plane = sw_doc.create_ref_plane(plane="XY", offset_val=thickness_m, target_plane_name="TopFacePlane")
        
        print("Step 2: 绘制中心止口草图...")
        sketch_bore = sw_doc.insert_sketch_on_plane(top_plane)
        sw_doc.create_circle(center_x=0, center_y=0, radius=center_bore_radius_m, sketch_ref="XY") # 注意：虽然是在新平面上，但局部坐标通常仍映射为XY逻辑，除非API有特殊说明。假设局部坐标系对齐。
        
        print("Step 2: 切除中心止口...")
        # 向下切除 (负方向相对于平面法向量，或者指定深度为正但方向向内)
        # 通常 extrude_cut 的 depth 正值沿法向。如果平面法向向上，我们要向下切，可能需要负值或调整。
        # 假设 create_ref_plane 创建的平面法向与原始平面一致（向上）。
        # 我们要从顶面向下挖 5mm。
        cut_bore = sw_doc.extrude_cut(sketch_bore, depth=-center_bore_depth_m, single_direction=True)
        
        # Step 3: 创建安装孔 (分布在 PCD 上)
        # 同样在顶面 (TopFacePlane) 上绘制
        print("Step 3: 绘制安装孔草图...")
        sketch_holes = sw_doc.insert_sketch_on_plane(top_plane)
        
        # 计算4个孔的位置 (PCD=50mm, 半径25mm)
        # 角度: 45, 135, 225, 315 度 (或者 0, 90, 180, 270，取决于具体装配要求，通常对称分布即可)
        # 这里采用 45度起始，使孔位于象限平分线上，或者 0/90/180/270。
        # 题目未指定角度相位，默认按 0, 90, 180, 270 分布更常见于法兰。
        angles_deg = [0, 90, 180, 270]
        
        for angle in angles_deg:
            rad = math.radians(angle)
            x_pos = pcd_radius_m * math.cos(rad)
            y_pos = pcd_radius_m * math.sin(rad)
            sw_doc.create_circle(center_x=x_pos, center_y=y_pos, radius=hole_radius_m, sketch_ref="XY")
            
        print("Step 3: 切除安装孔 (通孔)...")
        # 通孔意味着切穿整个厚度。由于我们在顶面，向下切穿厚度即可。
        # 深度设为略大于厚度以确保切穿，或者使用 "Through All" 选项（如果API支持）。
        # 当前 API extrude_cut 只有 depth。设 depth = -thickness_m * 1.1 确保切穿。
        cut_holes = sw_doc.extrude_cut(sketch_holes, depth=-thickness_m * 1.1, single_direction=True)
        
        # Step 4: 边缘倒角 C1
        # 需要对上下外边缘进行倒角。
        # 上边缘点: (outer_radius_m, 0, thickness_m)
        # 下边缘点: (outer_radius_m, 0, 0)
        
        print("Step 4: 处理边缘倒角...")
        # 上边缘倒角
        top_edge_point = (outer_radius_m, 0, thickness_m)
        sw_doc.chamfer_edges(on_line_points=[top_edge_point], distance=chamfer_dist_m, angle=45.0)
        
        # 下边缘倒角
        bottom_edge_point = (outer_radius_m, 0, 0)
        sw_doc.chamfer_edges(on_line_points=[bottom_edge_point], distance=chamfer_dist_m, angle=45.0)
        
        # 5. 创建装配接口 (参考面和轴)
        print("Step 5: 创建装配接口...")
        
        # 接口1: 中心轴 (Z轴)
        # 从 (0,0,0) 到 (0,0,1)
        axis_z = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 1), axis_name="CenterAxis_Z")
        
        # 接口2: 上表面 (机械臂安装面)
        # 已经创建了 TopFacePlane，可以重命名或确认其存在。
        # 如果需要显式暴露，可以再次引用或确保名称正确。
        # 这里我们创建一个名为 "MountingFace_Top" 的参考面，其实就是 TopFacePlane
        # 由于 create_ref_plane 已经命名为 TopFacePlane，我们可以直接使用它，或者再创建一个别名。
        # 为了清晰，我们保留 TopFacePlane 作为内部参考，如果需要特定名称，可以再建一个重合面，但通常没必要。
        # 让我们确保有一个明确命名的面供装配引用。
        mounting_face = sw_doc.create_ref_plane(plane="XY", offset_val=thickness_m, target_plane_name="MountingFace_Top")
        
        # 接口3: 下表面 (抓手连接基准面)
        # 即 XY 平面本身，或者创建一个偏移为0的平面并命名
        base_face = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="BaseFace_Bottom")
        
        # 接口4: 中心孔轴线 (其实与 CenterAxis_Z 重合，但语义不同，可选)
        # 通常一个中心轴就够了。
        
        # 6. 保存文件
        model_path = r"D:\CAutoD\solidworks_agent\agent_output\机械臂抓手底座_圆形法兰-20260429_145212\part\机械臂抓手底座_圆形法兰.SLDPRT"
        print(f"Step 6: 保存零件至 {model_path}")
        success = sw_doc.save_as(model_path)
        
        if success:
            print("零件建模与保存成功。")
        else:
            print("零件保存失败。")
            
    except Exception as e:
        print(f"建模过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()