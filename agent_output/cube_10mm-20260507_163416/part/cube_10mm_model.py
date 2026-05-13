# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用并创建零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "cube_10mm"
    print(f"正在创建零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 定义尺寸参数 (单位: m)
    # 输入要求边长 10mm，转换为米为 0.01m
    side_length_m = 0.01
    
    # 3. 建模步骤
    # 3.1 在 XY 基准面上插入草图
    print("在 XY 基准面上插入草图...")
    sketch_xy = sw_doc.insert_sketch_on_plane("XY")
    
    # 3.2 绘制中心矩形
    # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
    # 为了保持对称性，通常以原点为中心绘制正方形
    print(f"绘制 {side_length_m*1000}x{side_length_m*1000} mm 的中心矩形...")
    sw_doc.create_centre_rectangle(
        center_x=0.0, 
        center_y=0.0, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref="XY"
    )
    
    # 3.3 拉伸凸台/基体
    # extrude(sketch, depth, single_direction=True, merge=True)
    # 沿 Z 轴正方向拉伸 10mm (0.01m)
    print(f"沿 Z 轴拉伸 {side_length_m*1000} mm...")
    sw_doc.extrude(
        sketch=sketch_xy, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    # 4. 接口处理
    # 根据 spec，该零件没有特定的命名接口需求 (faces/axes/points 为空)
    # 但为了后续装配方便，SolidWorks 默认的原点、基准面已存在。
    # 如果需要显式暴露某些面或轴，可在此处添加 create_ref_plane 或 create_axis
    # 当前任务无此要求，跳过。
    
    # 5. 保存文件
    target_path = r"D:\CAutoD\solidworks_agent\agent_output\cube_10mm-20260507_163416\part\cube_10mm.SLDPRT"
    print(f"正在保存零件到: {target_path}")
    success = sw_doc.save_as(target_path)
    
    if success:
        print("零件建模与保存成功。")
    else:
        print("零件保存失败，请检查路径权限或 SolidWorks 状态。")

if __name__ == "__main__":
    main()