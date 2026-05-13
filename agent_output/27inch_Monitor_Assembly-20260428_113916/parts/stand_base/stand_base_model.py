# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用与零件文档
    app = SldWorksApp()
    part_name = "Stand Base"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模: {part_name}")

    # 2. 参数定义 (单位: m)
    diameter_mm = 250
    thickness_mm = 15
    
    diameter_m = diameter_mm / 1000.0
    radius_m = diameter_m / 2.0
    thickness_m = thickness_mm / 1000.0

    # 3. 建模步骤
    # 3.1 在 XY 平面创建草图
    sketch_plane = "XY"
    sketch = sw_doc.insert_sketch_on_plane(sketch_plane)
    
    # 3.2 绘制圆形轮廓 (中心在原点)
    # create_circle(center_x, center_y, radius, sketch_ref)
    sw_doc.create_circle(0, 0, radius_m, sketch_plane)
    
    # 3.3 拉伸生成实体
    # extrude(sketch, depth, single_direction=True, merge=True)
    # 向 +Z 方向拉伸厚度
    extrude_feature = sw_doc.extrude(sketch, depth=thickness_m, single_direction=True, merge=True)
    print("主体拉伸完成")

    # 4. 创建装配接口 (参考面与参考轴)
    
    # 4.1 创建底面参考 (base_bottom_face)
    # 位于 Z=0，法向 -Z。由于是基准面 XY 本身，我们可以直接引用或创建一个偏移为0的命名平面以便明确语义
    # 这里创建一个名为 base_bottom_face 的参考平面，基于 XY 平面偏移 0
    bottom_plane = sw_doc.create_ref_plane(plane="XY", offset_val=0.0, target_plane_name="base_bottom_face")
    print("创建接口: base_bottom_face")

    # 4.2 创建顶面参考 (base_top_face)
    # 位于 Z=thickness_m，法向 +Z
    top_plane = sw_doc.create_ref_plane(plane="XY", offset_val=thickness_m, target_plane_name="base_top_face")
    print("创建接口: base_top_face")

    # 4.3 创建中心轴参考 (base_center_axis)
    # 沿 Z 轴，从 (0,0,0) 到 (0,0,thickness_m)
    axis_pt1 = (0.0, 0.0, 0.0)
    axis_pt2 = (0.0, 0.0, thickness_m)
    center_axis = sw_doc.create_axis(pt1=axis_pt1, pt2=axis_pt2, axis_name="base_center_axis")
    print("创建接口: base_center_axis")

    # 5. 保存文件
    model_file_path = r"D:\a_src\python\sw_agent\agent_output\27inch_Monitor_Assembly-20260428_113916\parts\stand_base\stand_base.SLDPRT"
    success = sw_doc.save_as(model_file_path)
    
    if success:
        print(f"零件成功保存至: {model_file_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()