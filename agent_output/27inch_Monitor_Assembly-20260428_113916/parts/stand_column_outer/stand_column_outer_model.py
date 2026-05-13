# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用与零件文档
    app = SldWorksApp()
    part_name = "Stand Column Outer Tube"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模: {part_name}")

    # 2. 参数定义 (单位: mm -> m)
    outer_diameter_mm = 40.0
    inner_diameter_mm = 32.0
    height_mm = 200.0
    
    outer_radius_m = outer_diameter_mm / 2000.0  # 40mm / 2 = 20mm = 0.02m
    inner_radius_m = inner_diameter_mm / 2000.0  # 32mm / 2 = 16mm = 0.016m
    height_m = height_mm / 1000.0                # 200mm = 0.2m

    # 3. 创建草图 (XY平面)
    # 在XY平面上绘制两个同心圆，形成环形截面
    sketch_ref = "XY"
    sketch = sw_doc.insert_sketch_on_plane(sketch_ref)
    
    # 外圆
    sw_doc.create_circle(center_x=0, center_y=0, radius=outer_radius_m, sketch_ref=sketch_ref)
    # 内圆
    sw_doc.create_circle(center_x=0, center_y=0, radius=inner_radius_m, sketch_ref=sketch_ref)
    
    print("草图绘制完成: 同心圆环")

    # 4. 拉伸特征
    # 单向拉伸 +Z 方向，高度 0.2m
    extrude_feat = sw_doc.extrude(sketch, depth=height_m, single_direction=True, merge=True)
    print(f"拉伸完成: 高度 {height_m}m")

    # 5. 创建装配接口 (参考面与参考轴)
    
    # 5.1 参考轴: outer_tube_center_axis
    # 沿 Z 轴，从底部中心 (0,0,0) 到顶部中心 (0,0,height_m)
    axis_pt1 = (0.0, 0.0, 0.0)
    axis_pt2 = (0.0, 0.0, height_m)
    sw_doc.create_axis(pt1=axis_pt1, pt2=axis_pt2, axis_name="outer_tube_center_axis")
    print("创建参考轴: outer_tube_center_axis")

    # 5.2 参考面: outer_tube_bottom_face
    # 基于 XY 平面偏移 0 (即底面)，法向 -Z (指向下方/外部)
    # 注意：create_ref_plane 通常创建平行面。底面即为 Z=0 的平面。
    # 为了明确接口，我们创建一个位于 Z=0 的命名平面。
    base_plane = sw_doc.create_ref_plane(plane="XY", offset_val=0.0, target_plane_name="outer_tube_bottom_face")
    print("创建参考面: outer_tube_bottom_face")

    # 5.3 参考面: outer_tube_top_face
    # 基于 XY 平面偏移 height_m (即顶面)，法向 +Z
    top_plane = sw_doc.create_ref_plane(plane="XY", offset_val=height_m, target_plane_name="outer_tube_top_face")
    print("创建参考面: outer_tube_top_face")

    # 6. 保存文件
    model_file_path = r"D:\a_src\python\sw_agent\agent_output\27inch_Monitor_Assembly-20260428_113916\parts\stand_column_outer\stand_column_outer.SLDPRT"
    success = sw_doc.save_as(model_file_path)
    
    if success:
        print(f"零件已成功保存至: {model_file_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()