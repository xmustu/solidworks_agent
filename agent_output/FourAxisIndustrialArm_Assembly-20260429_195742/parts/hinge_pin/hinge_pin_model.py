from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "hinge_pin"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 参数定义 (单位: m)
    diameter_mm = 19.8
    length_mm = 75.0
    chamfer_dist_mm = 1.0
    
    diameter_m = diameter_mm / 1000.0
    length_m = length_mm / 1000.0
    chamfer_dist_m = chamfer_dist_mm / 1000.0
    
    radius_m = diameter_m / 2.0
    
    print(f"开始建模 {part_name}: D={diameter_mm}mm, L={length_mm}mm")

    # 3. 主体建模
    # 在 XY 平面绘制圆形草图
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(center_x=0, center_y=0, radius=radius_m, sketch_ref="XY")
    
    # 拉伸生成圆柱体
    # 沿 Z 轴正向拉伸
    extrude_feat = sw_doc.extrude(sketch_base, depth=length_m, single_direction=True, merge=True)
    print("主体拉伸完成")

    # 4. 倒角处理 (C1 Chamfer)
    # 需要对顶部和底部的圆形边进行倒角
    # 底部边坐标: (radius, 0, 0) 附近
    # 顶部边坐标: (radius, 0, length) 附近
    
    # 底部倒角
    bottom_edge_point = (radius_m, 0, 0)
    sw_doc.chamfer_edges(on_line_points=[bottom_edge_point], distance=chamfer_dist_m, angle=45.0)
    print("底部倒角完成")
    
    # 顶部倒角
    top_edge_point = (radius_m, 0, length_m)
    sw_doc.chamfer_edges(on_line_points=[top_edge_point], distance=chamfer_dist_m, angle=45.0)
    print("顶部倒角完成")

    # 5. 创建装配接口
    # 轴接口: pin_axis (沿局部 Z 轴，用于同心配合)
    # 起点 (0,0,0), 终点 (0,0,length)
    sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, length_m), axis_name="pin_axis")
    print("接口轴 pin_axis 创建完成")

    # 面接口: cylindrical_surface
    # 虽然 API 没有直接命名面的功能，但通常通过几何选择或参考面来辅助。
    # 对于圆柱面，装配时通常直接使用“同心”约束引用轴，或者手动选择面。
    # 这里我们确保轴已创建，这是最关键的接口。
    # 如果需要显式的面参考，可以创建一个通过轴的基准面，但通常轴足以满足同心配合。
    # 根据要求，尽量暴露接口名称。轴已命名。

    # 6. 保存文件
    model_path = r"D:\a_src\python\sw_agent\agent_output\FourAxisIndustrialArm_Assembly-20260429_195742\parts\hinge_pin\hinge_pin.SLDPRT"
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"零件成功保存至: {model_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()