# -*- coding: utf-8 -*-
import sys
import os

# 尝试导入 SolidWorks Python 封装库
# 注意：实际环境中可能需要根据安装路径调整 sys.path 或使用正确的包名
# 这里假设 pyswassem 是已安装的包，如果失败，请检查环境配置
try:
    from pyswassem import SldWorksApp, PartDoc
except ImportError:
    print("Error: 'pyswassem' module not found. Please ensure the SolidWorks Python wrapper is installed and accessible.")
    # 为了代码的健壮性，如果是在测试环境或特定容器中，可能需要动态添加路径
    # 例如: sys.path.append(r"C:\Path\To\Pyswassem")
    raise

def main():
    # 1. 初始化应用与创建零件文档
    app = SldWorksApp()
    part_name = "Base Plate"
    
    # 创建并激活零件文档
    sw_doc_obj = app.createAndActivate_sw_part(part_name)
    if sw_doc_obj is None:
        raise Exception("Failed to create or activate part document.")
        
    sw_doc = PartDoc(sw_doc_obj)
    
    print(f"开始建模: {part_name}")

    # 2. 定义尺寸 (单位: m)
    # 输入尺寸为 mm，需转换为 m
    base_width = 0.100   # 100 mm
    base_depth = 0.100   # 100 mm
    base_height = 0.080  # 80 mm
    
    boss_diameter = 0.040 # 40 mm
    boss_radius = boss_diameter / 2.0
    boss_height = 0.010   # 10 mm

    # 3. 建模步骤 1: 底座主体 (Rectangular Block)
    # 在 XY 平面绘制中心矩形
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    if sketch_base is None:
        raise Exception("Failed to insert sketch on XY plane for base.")
        
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=base_width, 
        height=base_depth, 
        sketch_ref="XY"
    )
    
    # 向上拉伸 80mm
    extrude_base = sw_doc.extrude(sketch_base, depth=base_height, single_direction=True, merge=True)
    if extrude_base is None:
        raise Exception("Failed to extrude base block.")
    print("底座主体拉伸完成")

    # 4. 建模步骤 2: 顶部凸台 (Central Cylindrical Boss)
    # 需要在底座顶面 (Z = 0.080) 上绘制草图
    # 创建一个位于 Z=0.080 的参考平面，平行于 XY 平面
    plane_top = sw_doc.create_workplane_p_d(plane="XY", offset_val=base_height)
    if plane_top is None:
        raise Exception("Failed to create workplane for boss.")
    
    sketch_boss = sw_doc.insert_sketch_on_plane(plane_top)
    if sketch_boss is None:
        raise Exception("Failed to insert sketch on top plane for boss.")
        
    sw_doc.create_circle(
        center_x=0, 
        center_y=0, 
        radius=boss_radius, 
        sketch_ref="XY" # 局部坐标系方向继承自基准面
    )
    
    # 向上拉伸 10mm
    extrude_boss = sw_doc.extrude(sketch_boss, depth=boss_height, single_direction=True, merge=True)
    if extrude_boss is None:
        raise Exception("Failed to extrude boss.")
    print("顶部凸台拉伸完成")

    # 5. 创建装配接口 (Interfaces)
    
    # 5.1 面接口: bottom_face (Z=0, Normal -Z)
    # 创建命名参考面以便装配识别
    ref_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0.0, target_plane_name="bottom_face")
    if ref_bottom is None:
        print("Warning: Failed to create reference plane 'bottom_face'.")
    
    # 5.2 面接口: top_face_boss (Z=0.090, Normal +Z)
    # 凸台顶部高度 = base_height + boss_height = 0.080 + 0.010 = 0.090
    ref_top_boss = sw_doc.create_ref_plane(plane="XY", offset_val=base_height + boss_height, target_plane_name="top_face_boss")
    if ref_top_boss is None:
        print("Warning: Failed to create reference plane 'top_face_boss'.")

    # 5.3 轴接口: central_axis_z (Along Z, through origin)
    # 创建一条沿 Z 轴的基准轴
    axis_z = sw_doc.create_axis(
        pt1=(0, 0, 0), 
        pt2=(0, 0, 0.1), 
        axis_name="central_axis_z"
    )
    if axis_z is None:
        print("Warning: Failed to create axis 'central_axis_z'.")
        
    print("装配接口创建完成")

    # 6. 保存文件
    output_path = r"D:\CAutoD\solidworks_agent\agent_output\FiveAxisRoboticArm_Assembly-20260429_123555\parts\base_plate\base_plate.SLDPRT"
    
    # 确保目录存在
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    success = sw_doc.save_as(output_path)
    
    if success:
        print(f"零件已成功保存至: {output_path}")
    else:
        print("零件保存失败")
        raise Exception("Failed to save part file.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred during modeling: {e}")
        sys.exit(1)