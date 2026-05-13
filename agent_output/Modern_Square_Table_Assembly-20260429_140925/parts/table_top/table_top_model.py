# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "Table Top"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模零件: {part_name}")

    # 2. 参数定义 (单位: m)
    length_m = 1.200  # 1200 mm
    width_m = 0.600   # 600 mm
    thickness_m = 0.025 # 25 mm
    
    # 3. 建模步骤
    
    # 3.1 在 XY 平面创建草图
    sketch_plane = "XY"
    sketch = sw_doc.insert_sketch_on_plane(sketch_plane)
    
    # 3.2 绘制中心矩形 (1200mm x 600mm)
    # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
    # 注意：width 对应 X 方向长度，height 对应 Y 方向宽度
    sw_doc.create_centre_rectangle(
        center_x=0.0, 
        center_y=0.0, 
        width=length_m, 
        height=width_m, 
        sketch_ref=sketch_plane
    )
    
    # 退出草图并拉伸
    # 根据说明：Extrude cut or boss extrude 25mm in the -Z direction.
    # 通常桌面主体是实体，所以使用 extrude (Boss)。
    # depth 为负值表示向 Z 轴负方向拉伸。
    extrude_feature = sw_doc.extrude(
        sketch=sketch, 
        depth=-thickness_m, 
        single_direction=True, 
        merge=True
    )
    print("主体拉伸完成")

    # 4. 创建接口 (参考面/轴)
    
    # 4.1 bottom_face: Mating surface for table legs, normal -Z
    # 该面位于 Z = -thickness_m 处。
    # 创建一个偏移平面作为参考，命名为 "bottom_face"
    try:
        bottom_plane = sw_doc.create_ref_plane(
            plane="XY", 
            offset_val=-thickness_m, 
            target_plane_name="bottom_face"
        )
        print("创建底部参考面: bottom_face")
    except Exception as e:
        print(f"创建底部参考面失败: {e}")

    # 4.2 top_face: User surface, normal +Z
    # 该面位于 Z = 0 处 (即原始 XY 平面)。
    # 创建一个偏移为 0 的新平面以明确命名 "top_face"
    try:
        top_plane = sw_doc.create_ref_plane(
            plane="XY", 
            offset_val=0.0, 
            target_plane_name="top_face"
        )
        print("创建顶部参考面: top_face")
    except Exception as e:
        print(f"创建顶部参考面失败: {e}")

    # 5. 保存零件
    model_path = r"D:\a_src\python\sw_agent\agent_output\Modern_Square_Table_Assembly-20260429_140925\parts\table_top\table_top.SLDPRT"
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"零件成功保存至: {model_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()
