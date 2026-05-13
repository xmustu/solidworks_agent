# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用并创建零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "Cube_100mm"
    print(f"正在创建零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 定义尺寸参数 (单位: m)
    # 输入尺寸为 100mm，转换为米为 0.1m
    side_length_m = 0.1
    
    # 3. 建模步骤
    # 3.1 在 XY 平面插入草图
    print("在 XY 平面插入草图...")
    sketch_xy = sw_doc.insert_sketch_on_plane("XY")
    
    # 3.2 绘制正方形草图
    # 使用 create_centre_rectangle 绘制中心矩形
    # 为了符合“一角位于原点”的常见定位习惯，或者更通用的中心对齐，
    # 这里采用中心对齐方式绘制，即中心在 (0,0)，宽度和高度均为 side_length_m。
    # 如果后续装配需要特定角点在原点，可以通过移动实体或调整参考面实现，
    # 但通常中心对称件以中心为基准更利于约束。
    # 根据 prompt 描述：“原点位置：立方体一角位于全局原点...或中心位于原点...此处按常规一角对齐处理”
    # 然而，create_centre_rectangle 是以中心为基准的。
    # 若要一角在原点 (0,0,0)，则中心应在 (side/2, side/2, 0)。
    # 让我们按照“一角在原点”的要求来设置中心坐标。
    center_x = side_length_m / 2.0
    center_y = side_length_m / 2.0
    
    print(f"绘制中心矩形: 中心({center_x}, {center_y}), 宽高({side_length_m})")
    sw_doc.create_centre_rectangle(
        center_x=center_x, 
        center_y=center_y, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref="XY"
    )
    
    # 3.3 拉伸特征
    # 沿 Z 轴正向拉伸 100mm (0.1m)
    print(f"执行拉伸操作: 深度 {side_length_m} m")
    extrude_feat = sw_doc.extrude(
        sketch=sketch_xy, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    # 4. 接口处理
    # 当前零件无特定接口要求，但为了通用性，可以保留默认基准面。
    # 如果有后续装配需求，可在此处添加 create_ref_plane 或 create_axis。
    
    # 5. 保存文件
    # 目标路径: D:\CAutoD\solidworks_agent\agent_output\Cube_100mm-20260429_144509\part\Cube_100mm.SLDPRT
    target_path = r"D:\CAutoD\solidworks_agent\agent_output\Cube_100mm-20260429_144509\part\Cube_100mm.SLDPRT"
    
    print(f"正在保存零件至: {target_path}")
    success = sw_doc.save_as(target_path)
    
    if success:
        print("零件建模与保存成功。")
    else:
        print("零件保存失败，请检查路径权限或 SolidWorks 状态。")

if __name__ == "__main__":
    main()