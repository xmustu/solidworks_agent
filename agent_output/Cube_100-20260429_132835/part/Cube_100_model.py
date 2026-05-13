# -*- coding: utf-8 -*-
from pyswassem import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用并创建零件文档
    print("正在启动 SolidWorks 应用...")
    app = SldWorksApp()
    
    part_name = "Cube_100"
    print(f"正在创建零件: {part_name}")
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 2. 定义参数 (单位转换: mm -> m)
    side_length_mm = 100.0
    side_length_m = side_length_mm / 1000.0
    
    # 3. 建模步骤
    # 3.1 在 XY 平面创建草图
    print("正在插入草图到 XY 平面...")
    sketch_xy = sw_doc.insert_sketch_on_plane("XY")
    
    # 3.2 绘制正方形轮廓
    # 要求：一个顶点位于原点(0,0)，向正X、正Y延伸
    # create_centre_rectangle 需要中心点坐标和宽高
    # 如果左下角是 (0,0)，边长 L，则中心点是 (L/2, L/2)
    center_x = side_length_m / 2.0
    center_y = side_length_m / 2.0
    
    print(f"正在绘制中心矩形: 中心({center_x}, {center_y}), 宽{side_length_m}, 高{side_length_m}")
    sw_doc.create_centre_rectangle(
        center_x=center_x, 
        center_y=center_y, 
        width=side_length_m, 
        height=side_length_m, 
        sketch_ref="XY"
    )
    
    # 3.3 拉伸生成实体
    print(f"正在执行拉伸特征，深度: {side_length_m} m")
    extrude_feature = sw_doc.extrude(
        sketch=sketch_xy, 
        depth=side_length_m, 
        single_direction=True, 
        merge=True
    )
    
    # 4. 接口处理
    # 根据 spec，interfaces 为空，但为了后续装配通用性，通常建议保留基准面。
    # 此处无需额外创建命名参考面或轴，因为默认基准面已存在且无特殊接口需求。
    
    # 5. 保存文件
    model_path = r"D:\CAutoD\solidworks_agent\agent_output\Cube_100-20260429_132835\part\Cube_100.SLDPRT"
    print(f"正在保存零件至: {model_path}")
    success = sw_doc.save_as(model_path)
    
    if success:
        print("零件建模与保存成功完成。")
    else:
        print("零件保存失败。")

if __name__ == "__main__":
    main()