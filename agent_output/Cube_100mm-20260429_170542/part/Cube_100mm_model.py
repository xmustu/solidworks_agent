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
    
    # 3.2 绘制正方形轮廓
    # 使用中心矩形，中心在原点 (0,0)，宽高均为 side_length_m
    # 这样立方体将关于 Z 轴对称，底面位于 Z=0 到 Z=-side_length_m/2? 
    # 不，extrude 默认单向。如果我们在 XY 平面画草图，拉伸深度为正，则向 Z+ 方向。
    # 为了符合常规“角点基准”或“中心基准”，这里采用中心矩形，原点在中心。
    # 如果后续装配需要特定原点位置，可以通过参考面调整。
    # 这里创建一个以原点为中心的正方形。
    print(f"绘制边长为 {side_length_m}m 的正方形...")
    sw_doc.create_centre_rectangle(
        center_x=0.0, 
        center_y=0.0, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref="XY"
    )
    
    # 3.3 拉伸生成实体
    # 沿 Z 轴正向拉伸，深度为 side_length_m
    print(f"沿 Z 轴正向拉伸，深度 {side_length_m}m...")
    extrude_feature = sw_doc.extrude(
        sketch=sketch_xy, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    # 4. 接口处理
    # 根据 spec，interfaces 为空，但为了通用性，我们可以保留主要基准面名称
    # 如果需要暴露特定的面或轴用于装配，应在此处创建命名参考几何
    # 当前无特定接口要求，跳过额外参考几何创建
    
    # 5. 保存文件
    # 目标路径: D:\CAutoD\solidworks_agent\agent_output\Cube_100mm-20260429_170542\part\Cube_100mm.SLDPRT
    target_path = r"D:\CAutoD\solidworks_agent\agent_output\Cube_100mm-20260429_170542\part\Cube_100mm.SLDPRT"
    print(f"正在保存零件至: {target_path}")
    success = sw_doc.save_as(target_path)
    
    if success:
        print("零件建模与保存成功。")
    else:
        print("零件保存失败。")

if __name__ == "__main__":
    main()