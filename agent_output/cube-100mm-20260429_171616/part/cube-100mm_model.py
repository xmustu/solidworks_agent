# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用与零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "cube-100mm"
    print(f"创建并激活零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 定义尺寸参数 (单位: m)
    # 输入尺寸为 100mm，转换为米为 0.1m
    side_length_m = 0.1
    
    # 3. 建模步骤
    # 3.1 在 XY 基准面上插入草图
    print("在 XY 平面插入草图...")
    sketch_xy = sw_doc.insert_sketch_on_plane("XY")
    
    # 3.2 绘制中心矩形 (正方形)
    # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
    # 中心在 (0,0)，宽高均为 0.1m
    print(f"绘制边长为 {side_length_m}m 的正方形草图...")
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref="XY"
    )
    
    # 3.3 拉伸特征
    # extrude(sketch, depth, single_direction=True, merge=True)
    # 沿 Z 轴正方向拉伸 0.1m
    print(f"沿 Z 轴拉伸深度 {side_length_m}m...")
    extrude_feature = sw_doc.extrude(
        sketch=sketch_xy, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    # 4. 接口处理
    # 根据 spec，该零件暂无特定的命名接口要求 (faces/axes/points 为空)。
    # 但为了后续装配方便，通常立方体的面可以通过几何选择或默认基准面引用。
    # 此处无需额外创建参考面或轴，除非有特定命名需求。
    
    # 5. 保存文件
    # 目标路径: D:\CAutoD\solidworks_agent\agent_output\cube-100mm-20260429_171616\part\cube-100mm.SLDPRT
    target_path = r"D:\CAutoD\solidworks_agent\agent_output\cube-100mm-20260429_171616\part\cube-100mm.SLDPRT"
    print(f"尝试保存零件至: {target_path}")
    
    success = sw_doc.save_as(target_path)
    
    if success:
        print("零件建模与保存成功完成。")
    else:
        print("零件保存失败，请检查路径权限或 SolidWorks 状态。")

if __name__ == "__main__":
    main()