# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用并创建零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "cube100"
    print(f"正在创建零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    if not sw_doc or not sw_doc.partDoc:
        raise Exception("无法创建或激活零件文档")

    # 2. 定义参数 (单位转换: mm -> m)
    side_length_mm = 100.0
    side_length_m = side_length_mm / 1000.0  # 0.1 m
    
    print(f"建模参数: 边长 {side_length_mm}mm ({side_length_m}m)")

    # 3. 建模步骤
    
    # 3.1 在 XY 平面插入草图
    print("在 XY 平面插入草图...")
    sketch_plane = "XY"
    sketch = sw_doc.insert_sketch_on_plane(sketch_plane)
    
    # 3.2 绘制中心矩形 (正方形)
    # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
    # 中心在原点 (0,0)，宽高均为 side_length_m
    print("绘制中心正方形草图...")
    sw_doc.create_centre_rectangle(
        center_x=0.0, 
        center_y=0.0, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref=sketch_plane
    )
    
    # 3.3 拉伸成型
    # extrude(sketch, depth, single_direction=True, merge=True)
    # 深度为 side_length_m，单向拉伸
    print("执行拉伸特征...")
    extrude_feature = sw_doc.extrude(
        sketch=sketch, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    if not extrude_feature:
        print("警告: 拉伸特征可能未成功创建，请检查几何约束")

    # 4. 接口处理
    # 根据 spec，interfaces 为空，无需额外创建参考面或轴。
    # 但为了后续装配方便，通常立方体的六个面可以通过坐标选择，
    # 这里暂不显式创建命名参考面，除非有特定需求。

    # 5. 保存文件
    target_path = r"D:\CAutoD\solidworks_agent\agent_output\cube100-20260429_174447\part\cube100.SLDPRT"
    print(f"正在保存零件到: {target_path}")
    
    success = sw_doc.save_as(target_path)
    
    if success:
        print("零件建模与保存成功完成。")
    else:
        print("错误: 零件保存失败。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"发生异常: {e}")