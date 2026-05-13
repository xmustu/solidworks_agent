# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "Table Leg"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模零件: {part_name}")

    # 2. 参数定义 (单位: m)
    outer_diameter = 0.040  # 40 mm
    inner_diameter = 0.030  # 30 mm
    height = 0.750          # 750 mm
    
    outer_radius = outer_diameter / 2
    inner_radius = inner_diameter / 2

    # 3. 建模主体：空心圆柱
    # 在 XY 平面绘制草图
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    
    # 绘制外圆
    sw_doc.create_circle(center_x=0, center_y=0, radius=outer_radius, sketch_ref="XY")
    # 绘制内圆
    sw_doc.create_circle(center_x=0, center_y=0, radius=inner_radius, sketch_ref="XY")
    
    # 拉伸生成空心圆柱体
    # 单向拉伸，高度为 height
    extrude_body = sw_doc.extrude(sketch_base, depth=height, single_direction=True, merge=True)
    print("主体空心圆柱已创建")

    # 4. 创建装配接口
    
    # 4.1 面接口: top_face 和 bottom_face
    # 创建命名参考平面以便于装配引用
    try:
        # 底面参考平面 (Offset 0 from XY)
        ref_plane_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="bottom_face")
        print("创建底面参考平面: bottom_face")
        
        # 顶面参考平面 (Offset height from XY)
        ref_plane_top = sw_doc.create_ref_plane(plane="XY", offset_val=height, target_plane_name="top_face")
        print("创建顶面参考平面: top_face")
    except Exception as e:
        print(f"创建参考平面时出错: {e}")

    # 4.2 轴接口: central_axis
    # 创建沿 Z 轴的基准轴，从 (0,0,0) 到 (0,0,height)
    try:
        central_axis = sw_doc.create_axis(
            pt1=(0, 0, 0), 
            pt2=(0, 0, height), 
            axis_name="central_axis"
        )
        print("创建中心轴线: central_axis")
    except Exception as e:
        print(f"创建中心轴线时出错: {e}")

    # 5. 保存零件
    model_path = r"D:\a_src\python\sw_agent\agent_output\Table_Assembly_M8_Fastened-20260429_112407\parts\table_leg\table_leg.SLDPRT"
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"零件成功保存至: {model_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()
