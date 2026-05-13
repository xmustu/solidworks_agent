# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc
import os
import time

def main():
    # 1. 配置参数
    part_name = "SolidCube_100mm"
    # 目标保存路径，根据输入JSON指定
    model_file_path = r"D:\CAutoD\solidworks_agent\agent_output\SolidCube_100mm-20260429_141557\part\SolidCube_100mm.SLDPRT"
    
    # 关键尺寸 (单位: mm -> m)
    side_length_mm = 100.0
    side_length_m = side_length_mm / 1000.0  # 0.1 m
    
    print(f"[INFO] 开始建模零件: {part_name}")
    print(f"[INFO] 边长: {side_length_mm} mm ({side_length_m} m)")

    try:
        # 2. 启动 SolidWorks 应用并创建零件文档
        # 增加重试机制以应对 COM 连接不稳定或启动延迟
        app = None
        sw_part_obj = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] 尝试连接 SolidWorks (Attempt {attempt + 1}/{max_retries})...")
                app = SldWorksApp()
                
                # 创建并激活零件
                sw_part_obj = app.createAndActivate_sw_part(part_name)
                
                if sw_part_obj is not None:
                    print("[INFO] SolidWorks 连接成功，零件文档已创建。")
                    break
                else:
                    print("[WARN] createAndActivate_sw_part 返回 None，可能正在初始化...")
                    
            except Exception as e:
                print(f"[WARN] 连接尝试 {attempt + 1} 失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2) # 等待2秒后重试
                else:
                    raise Exception("Failed to connect to SolidWorks after multiple attempts.")

        if sw_part_obj is None:
            raise Exception("Failed to create or activate part document. SolidWorks might not be running or accessible.")
            
        sw_doc = PartDoc(sw_part_obj)
        
        if sw_doc.partDoc is None:
            raise Exception("PartDoc object is invalid after creation.")

        print("[INFO] 零件文档已激活，准备建模。")

        # 3. 建模步骤
        
        # 3.1 在 XY 平面插入草图
        sketch_plane = "XY"
        sketch = sw_doc.insert_sketch_on_plane(sketch_plane)
        print(f"[INFO] 已在 {sketch_plane} 平面插入草图。")

        # 3.2 绘制中心矩形 (正方形)
        # 中心在 (0,0)，宽度和高度均为 side_length_m
        # sketch_ref 必须与当前草图平面方向一致，这里为 "XY"
        sw_doc.create_centre_rectangle(
            center_x=0.0, 
            center_y=0.0, 
            width=side_length_m, 
            height=side_length_m, 
            sketch_ref="XY"
        )
        print("[INFO] 已绘制中心正方形草图。")

        # 3.3 拉伸特征
        # 深度为 side_length_m，单向拉伸 (Z轴正向)
        extrude_feature = sw_doc.extrude(
            sketch=sketch, 
            depth=side_length_m, 
            single_direction=True, 
            merge=True
        )
        print("[INFO] 已完成拉伸特征，生成实心立方体。")

        # 4. 接口处理
        # 根据 spec，interfaces 为空，无需创建额外的参考面或轴。
        print("[INFO] 无额外接口要求，跳过参考几何创建。")

        # 5. 保存文件
        # 确保目录存在
        dir_path = os.path.dirname(model_file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"[INFO] 创建目录: {dir_path}")

        success = sw_doc.save_as(model_file_path)
        
        if success:
            print(f"[SUCCESS] 零件已成功保存至: {model_file_path}")
        else:
            print(f"[ERROR] 零件保存失败: {model_file_path}")

    except Exception as e:
        print(f"[ERROR] 建模过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()