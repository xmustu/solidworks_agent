# -*- coding: utf-8 -*-
import sys
import os

# 1. 配置路径与导入
# 根据错误信息，库位于 D:\CAutoD\pysw_assem
lib_path = r"D:\CAutoD\pysw_assem"
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

try:
    from pyswassem import SldWorksApp, PartDoc
except ImportError as e:
    print(f"Error importing pyswassem: {e}")
    print("Please ensure the library is installed and accessible.")
    sys.exit(1)

def main():
    # 2. 初始化应用与零件文档
    print("正在启动 SolidWorks 应用...")
    try:
        app = SldWorksApp()
    except Exception as e:
        print(f"Failed to initialize SldWorksApp: {e}")
        return

    part_name = "Cube_100mm"
    print(f"创建并激活零件: {part_name}")
    try:
        sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    except Exception as e:
        print(f"Failed to create part document: {e}")
        return
    
    # 3. 参数定义 (单位转换为米)
    # 输入尺寸为 mm，API 要求 m
    side_length_mm = 100.0
    side_length_m = side_length_mm / 1000.0  # 0.1 m
    
    # 4. 建模步骤
    # 4.1 在 XY 平面插入草图
    print("在 XY 平面插入草图...")
    try:
        sketch_xy = sw_doc.insert_sketch_on_plane("XY")
    except Exception as e:
        print(f"Failed to insert sketch on XY plane: {e}")
        return
    
    # 4.2 绘制中心矩形 (边长 100mm)
    # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
    # 原点位于底面中心，所以矩形中心为 (0,0)
    print(f"绘制中心矩形: 宽={side_length_m}m, 高={side_length_m}m")
    try:
        sw_doc.create_centre_rectangle(
            center_x=0.0, 
            center_y=0.0, 
            width=side_length_m, 
            height=side_length_m, 
            sketch_ref="XY"
        )
    except Exception as e:
        print(f"Failed to create rectangle: {e}")
        return
    
    # 4.3 拉伸成型 (Z轴正向，深度 100mm)
    print(f"执行拉伸特征: 深度={side_length_m}m")
    try:
        extrude_feat = sw_doc.extrude(
            sketch=sketch_xy, 
            depth=side_length_m, 
            single_direction=True, 
            merge=True
        )
    except Exception as e:
        print(f"Failed to extrude: {e}")
        return
    
    # 5. 接口处理
    # 根据 spec，该零件无特定命名接口要求。
    
    # 6. 保存文件
    model_file_path = r"D:\CAutoD\solidworks_agent\agent_output\Cube_100mm-20260429_125023\part\Cube_100mm.SLDPRT"
    
    # 确保目录存在
    dir_path = os.path.dirname(model_file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        
    print(f"正在保存零件至: {model_file_path}")
    try:
        success = sw_doc.save_as(model_file_path)
        if success:
            print("零件建模与保存成功。")
        else:
            print("零件保存失败，请检查路径权限或 SolidWorks 状态。")
    except Exception as e:
        print(f"Exception during save: {e}")

if __name__ == "__main__":
    main()