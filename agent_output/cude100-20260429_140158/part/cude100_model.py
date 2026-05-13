# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc
import os

def main():
    # 1. 初始化应用并创建零件文档
    print("正在启动 SolidWorks 应用...")
    try:
        app = SldWorksApp()
    except Exception as e:
        print(f"SolidWorks 应用启动失败: {e}")
        return

    part_name = "cude100"
    print(f"正在创建零件: {part_name}")
    
    # 尝试创建并激活零件
    sw_part_obj = app.createAndActivate_sw_part(part_name)
    if sw_part_obj is None:
        print("错误：无法创建或激活零件文档。请检查 SolidWorks 是否已正确安装并注册 COM 组件。")
        return
        
    sw_doc = PartDoc(sw_part_obj)
    
    # 2. 定义参数 (单位转换: mm -> m)
    side_length_mm = 100.0
    side_length_m = side_length_mm / 1000.0  # 0.1 m
    
    # 3. 建模步骤
    # 目标：创建一个以原点 (0,0,0) 为中心的立方体，边长 0.1m。
    # 策略：在 Z = -0.05m 处创建基准面，绘制草图，然后向 +Z 方向拉伸 0.1m。
    
    # 3.1 创建偏移基准面
    print("创建偏移基准面 Plane_Offset_Z (-0.05m)...")
    try:
        plane_offset = sw_doc.create_workplane_p_d(plane="XY", offset_val=-side_length_m / 2.0)
    except Exception as e:
        print(f"创建基准面失败: {e}")
        return

    # 3.2 在偏移基准面上插入草图
    print("在偏移基准面上插入草图...")
    try:
        sketch_offset = sw_doc.insert_sketch_on_plane(plane_offset)
    except Exception as e:
        print(f"插入草图失败: {e}")
        return
    
    # 3.3 绘制中心矩形
    # 注意：sketch_ref 应该与当前草图平面的局部坐标系一致。
    # 对于由 XY 平面偏移得到的平面，其局部 X/Y 轴通常与全局 X/Y 平行。
    print(f"绘制中心矩形: 中心(0,0), 宽{side_length_m}m, 高{side_length_m}m")
    try:
        sw_doc.create_centre_rectangle(
            center_x=0.0, 
            center_y=0.0, 
            width=side_length_m, 
            height=side_length_m, 
            sketch_ref="XY" 
        )
    except Exception as e:
        print(f"绘制矩形失败: {e}")
        return
    
    # 3.4 拉伸凸台/基体
    print("执行拉伸操作，深度 0.1m...")
    try:
        # 从 Z=-0.05 向上拉伸 0.1m，到达 Z=0.05。中心即为 0。
        sw_doc.extrude(sketch_offset, depth=side_length_m, single_direction=True, merge=True)
    except Exception as e:
        print(f"拉伸操作失败: {e}")
        return
    
    # 4. 接口处理
    # 需求中 interfaces 为空，无需额外创建命名接口。
    
    # 5. 保存文件
    model_file_path = r"D:\CAutoD\solidworks_agent\agent_output\cude100-20260429_140158\part\cude100.SLDPRT"
    
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
            print("零件保存返回失败状态。")
    except Exception as e:
        print(f"保存文件时发生异常: {e}")

if __name__ == "__main__":
    main()