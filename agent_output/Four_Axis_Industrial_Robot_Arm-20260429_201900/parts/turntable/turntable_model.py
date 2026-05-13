import os
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化与路径设置
    model_path = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\turntable\turntable.SLDPRT"
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    app = SldWorksApp()
    # 创建零件文档
    sw_doc = PartDoc(app.createAndActivate_sw_part("turntable"))
    print("开始建模：回转台 (turntable)")

    # 尺寸定义 (单位换算为 m)
    outer_diameter = 0.180  # 180mm
    total_height = 0.100    # 100mm
    fork_width = 0.061      # 61mm
    pin_hole_diameter = 0.020 # 20mm
    base_height = 0.030     # 底部圆柱高度
    wall_thickness = 0.010  # 叉架壁厚 (估算，总宽约 61+10*2=81mm)
    
    # 2. 创建主体圆柱 (XY平面)
    print("步骤 1: 创建主体圆柱")
    sketch1 = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(0, 0, outer_diameter / 2, "XY")
    sw_doc.extrude(sketch1, depth=total_height, single_direction=True)

    # 3. 切除形成U型槽
    # 在 XZ 平面（或垂直于 Y 的平面）进行切除，以形成开口宽度为 61mm 的槽
    # 槽的深度：从顶部向下切到底部圆柱上方
    print("步骤 2: 切除形成U型槽")
    sketch2 = sw_doc.insert_sketch_on_plane("XZ")
    # 矩形中心在 (0, total_height)，宽度为 fork_width，高度覆盖 total_height - base_height
    # 注意：XZ平面坐标系中，水平为X，垂直为Z(高度)
    # 我们在 XZ 平面画一个矩形，然后沿 Y 方向双向切除
    # 矩形中心 X=0, Y=(total_height + base_height)/2, 宽=fork_width, 高=total_height-base_height
    cut_depth = total_height - base_height
    sw_doc.create_centre_rectangle(0, total_height - cut_depth/2, fork_width, cut_depth, "XZ")
    # 双向拉伸切除，确保切透圆柱 (外径180mm，切除深度给 200mm 足够)
    sw_doc.extrude_cut(sketch2, depth=0.2, single_direction=False)

    # 4. 在槽壁打销轴通孔 (直径 20mm)
    # 孔的中心高度设在叉架的中部，例如距离顶端 30mm 处
    print("步骤 3: 打销轴通孔")
    hole_z = total_height - 0.030 
    sketch3 = sw_doc.insert_sketch_on_plane("ZY")
    sw_doc.create_circle(0, hole_z, pin_hole_diameter / 2, "ZY")
    sw_doc.extrude_cut(sketch3, depth=0.2, single_direction=False)

    # 5. 创建装配接口
    print("步骤 4: 创建装配接口")
    
    # 接口：bottom_contact_face (底部接触面)
    # 位于 XY 平面 (Z=0)
    sw_doc.create_ref_plane("XY", 0, "bottom_contact_face")
    
    # 接口：mid_plane_y (对称中心面)
    # 位于 XZ 平面 (Y=0)
    sw_doc.create_ref_plane("XZ", 0, "mid_plane_y")
    
    # 接口：rotation_axis_z (第一轴旋转轴)
    sw_doc.create_axis((0, 0, 0), (0, 0, 0.1), "rotation_axis_z")
    
    # 接口：joint_axis_y (第二轴销轴孔轴线)
    # 轴线位于 (0, Y, hole_z)
    sw_doc.create_axis((0, -0.1, hole_z), (0, 0.1, hole_z), "joint_axis_y")

    # 6. 保存零件
    success = sw_doc.save_as(model_path)
    if success:
        print(f"回转台建模完成并保存至: {model_path}")
    else:
        print("保存失败")

if __name__ == "__main__":
    main()