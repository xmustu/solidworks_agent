# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "Table Top"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    # 参数定义 (单位: m)
    length = 1.200      # 1200 mm
    width = 0.600       # 600 mm
    thickness = 0.025   # 25 mm
    hole_dia = 0.009    # 9 mm
    hole_offset_x = 0.550 # 550 mm from center (1200/2 - 50)
    hole_offset_y = 0.250 # 250 mm from center (600/2 - 50)
    
    print(f"开始建模零件: {part_name}")
    
    # 2. 主体建模：在XY平面绘制矩形并拉伸
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    # 中心矩形，宽=Length(X), 高=Width(Y)
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=length, 
        height=width, 
        sketch_ref="XY"
    )
    # 拉伸生成桌面主体，厚度沿Z轴正向
    extrude_base = sw_doc.extrude(sketch_base, depth=thickness, single_direction=True, merge=True)
    print("桌面主体拉伸完成")
    
    # 3. 创建安装孔
    # 孔位置坐标 (相对于原点):
    # FL: (-hole_offset_x, -hole_offset_y)
    # FR: ( hole_offset_x, -hole_offset_y)
    # BL: (-hole_offset_x,  hole_offset_y)
    # BR: ( hole_offset_x,  hole_offset_y)
    
    hole_positions = [
        (-hole_offset_x, -hole_offset_y, "FL"),
        ( hole_offset_x, -hole_offset_y, "FR"),
        (-hole_offset_x,  hole_offset_y, "BL"),
        ( hole_offset_x,  hole_offset_y, "BR")
    ]
    
    for x, y, name in hole_positions:
        # 在顶面(Z=thickness)或底面(Z=0)创建草图。为了切除通孔，通常在顶面画圆向下切，或者在底面向上切。
        # 这里选择在顶面(Z=thickness)创建草图，然后向下切除贯穿。
        # 注意：insert_sketch_on_plane 通常基于基准面。如果要在实体面上画草图，可能需要先选择面。
        # 根据API文档，insert_sketch_on_plane 接受 "XY", "XZ", "ZY" 或自定义平面名。
        # 为了简化，我们可以在 XY 平面 (Z=0) 画圆，然后向上切除贯穿整个厚度。
        
        sketch_hole = sw_doc.insert_sketch_on_plane("XY")
        sw_doc.create_circle(center_x=x, center_y=y, radius=hole_dia/2, sketch_ref="XY")
        
        # 拉伸切除，深度设为大于厚度的值以确保贯穿，或者使用双向/特定方向
        # 由于我们在 Z=0 平面画图，向 +Z 方向切除可以贯穿到 Z=thickness
        sw_doc.extrude_cut(sketch_hole, depth=thickness + 0.001, single_direction=True)
        print(f"创建安装孔 {name} 完成")

    # 4. 创建装配接口
    
    # 4.1 面接口
    # top_face: 桌面上表面 (Z = thickness)
    # bottom_face: 桌面下表面 (Z = 0)
    # 使用 create_ref_plane 创建命名参考面，虽然它们可能与现有几何面重合，但命名后便于装配引用
    
    # 创建 top_face 参考平面 (偏移 XY 平面 +thickness)
    ref_top = sw_doc.create_ref_plane(plane="XY", offset_val=thickness, target_plane_name="top_face")
    print("创建参考面: top_face")
    
    # 创建 bottom_face 参考平面 (偏移 XY 平面 0，即 XY 本身，但重命名以便区分语义)
    # 注意：如果直接重命名 XY 可能会影响其他操作，最好创建一个偏移量为0的新平面或直接使用 XY 并在装配时指定。
    # 但为了接口一致性，我们创建一个名为 bottom_face 的平面，位于 Z=0
    ref_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0.0, target_plane_name="bottom_face")
    print("创建参考面: bottom_face")
    
    # 4.2 轴接口
    # 四个孔的轴线，沿 Z 方向
    # hole_axis_fl, hole_axis_fr, hole_axis_bl, hole_axis_br
    
    axes_data = [
        ("hole_axis_fl", -hole_offset_x, -hole_offset_y),
        ("hole_axis_fr",  hole_offset_x, -hole_offset_y),
        ("hole_axis_bl", -hole_offset_x,  hole_offset_y),
        ("hole_axis_br",  hole_offset_x,  hole_offset_y)
    ]
    
    for axis_name, ax, ay in axes_data:
        # 创建从 (ax, ay, 0) 到 (ax, ay, thickness) 的轴，方向沿 +Z
        pt1 = (ax, ay, 0.0)
        pt2 = (ax, ay, thickness)
        sw_doc.create_axis(pt1=pt1, pt2=pt2, axis_name=axis_name)
        print(f"创建参考轴: {axis_name}")

    # 5. 保存文件
    model_path = r"D:\a_src\python\sw_agent\agent_output\Table_Assembly_M8_Fastened-20260429_112407\parts\table_top\table_top.SLDPRT"
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"零件模型已保存至: {model_path}")
    else:
        print("零件模型保存失败")

if __name__ == "__main__":
    main()