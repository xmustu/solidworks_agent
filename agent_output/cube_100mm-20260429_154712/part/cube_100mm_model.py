# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用并创建零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "cube_100mm"
    print(f"正在创建零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 定义尺寸参数 (单位: m)
    # 输入尺寸为 100mm，转换为米为 0.1m
    side_length_m = 0.1
    
    # 3. 建模步骤
    # 3.1 在 XY 平面插入草图
    print("在 XY 平面插入草图...")
    sketch_xy = sw_doc.insert_sketch_on_plane("XY")
    
    # 3.2 绘制中心矩形 (正方形)
    # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
    # 中心在原点 (0,0)，宽高均为 0.1m
    print(f"绘制边长为 {side_length_m}m 的正方形...")
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref="XY"
    )
    
    # 3.3 拉伸成型
    # extrude(sketch, depth, single_direction=True, merge=True)
    # 沿 Z 轴正向拉伸 0.1m
    print(f"沿 Z 轴正向拉伸 {side_length_m}m...")
    sw_doc.extrude(
        sketch=sketch_xy, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    # 4. 接口处理
    # 根据 spec，该零件无特定命名接口要求，但为了通用性，
    # 我们可以保留默认基准面作为潜在参考。
    # 此处无需额外创建命名参考面或轴，因为 interfaces 列表为空。
    
    # 5. 保存文件
    target_path = r"D:\CAutoD\solidworks_agent\agent_output\cube_100mm-20260429_154712\part\cube_100mm.SLDPRT"
    print(f"正在保存零件到: {target_path}")
    success = sw_doc.save_as(target_path)
    
    if success:
        print("零件建模与保存成功完成。")
    else:
        print("零件保存失败，请检查路径权限或 SolidWorks 状态。")

if __name__ == "__main__":
    main()