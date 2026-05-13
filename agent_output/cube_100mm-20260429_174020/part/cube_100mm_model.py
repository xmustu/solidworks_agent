# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc
import os

def main():
    # 1. 配置参数
    # 输入尺寸单位为 mm，需转换为 m (SolidWorks API 默认米制)
    side_length_mm = 100.0
    side_length_m = side_length_mm / 1000.0
    
    # 目标文件路径
    model_file_path = r"D:\CAutoD\solidworks_agent\agent_output\cube_100mm-20260429_174020\part\cube_100mm.SLDPRT"
    
    # 确保目录存在
    part_dir = os.path.dirname(model_file_path)
    if not os.path.exists(part_dir):
        os.makedirs(part_dir)
        print(f"创建目录: {part_dir}")

    try:
        # 2. 启动 SolidWorks 应用并创建零件文档
        print("正在启动 SolidWorks 应用...")
        app = SldWorksApp()
        
        print("正在创建零件文档 'cube_100mm'...")
        sw_doc = PartDoc(app.createAndActivate_sw_part("cube_100mm"))
        
        # 3. 建模步骤
        
        # 3.1 在 XY 平面插入草图
        print("在 XY 平面插入草图...")
        sketch_xy = sw_doc.insert_sketch_on_plane("XY")
        
        # 3.2 绘制正方形草图
        # 使用 create_centre_rectangle 绘制中心在原点的正方形
        # width 和 height 均为边长
        print(f"绘制边长为 {side_length_m}m 的正方形草图...")
        sw_doc.create_centre_rectangle(
            center_x=0.0, 
            center_y=0.0, 
            width=side_length_m, 
            height=side_length_m, 
            sketch_ref="XY"
        )
        
        # 3.3 拉伸凸台/基体
        # 沿 Z 轴正向拉伸，深度为边长
        print(f"沿 Z 轴正向拉伸 {side_length_m}m...")
        extrude_feature = sw_doc.extrude(
            sketch=sketch_xy, 
            depth=side_length_m, 
            single_direction=True, 
            merge=True
        )
        
        # 4. 接口处理
        # 根据 spec，该零件无特定命名接口要求 (faces/axes/points 为空)
        # 但为了后续装配通用性，通常保留默认基准面即可。
        # 若有需要，可在此处添加 create_ref_plane 或 create_axis
        
        # 5. 保存零件
        print(f"正在保存零件到: {model_file_path}")
        success = sw_doc.save_as(model_file_path)
        
        if success:
            print("零件建模与保存成功。")
        else:
            print("零件保存失败。")
            
    except Exception as e:
        print(f"发生错误: {e}")
        raise

if __name__ == "__main__":
    main()