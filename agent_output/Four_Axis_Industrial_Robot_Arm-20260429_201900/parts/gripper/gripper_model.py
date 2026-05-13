import os
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化与创建零件
    app = SldWorksApp()
    part_name = "gripper"
    model_path = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\gripper\gripper.SLDPRT"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    print(f"开始建模零件: {part_name}")

    # 尺寸定义 (单位换算: mm -> m)
    base_width = 0.080  # 基座总宽度 (Y方向)
    base_height = 0.040 # 基座高度 (Z方向)
    base_thickness = 0.060 # 安装座厚度 (X方向)
    hole_diameter = 0.020 # 销轴孔径
    finger_length = 0.050 # 手指长度
    finger_width = 0.015  # 手指宽度
    
    # 2. 创建安装基座 (Center Rectangle on ZY plane)
    # 我们在 ZY 平面绘制，向 X 正方向拉伸
    sketch_base = sw_doc.insert_sketch_on_plane("ZY")
    # 中心矩形：中心(0,0)，宽度(Y) 0.08, 高度(Z) 0.04
    sw_doc.create_centre_rectangle(0, 0, base_width, base_height, "ZY")
    # 拉伸 0.06m (X方向)
    sw_doc.extrude(sketch_base, depth=base_thickness, single_direction=True)
    print("基座主体拉伸完成")

    # 3. 切除销轴安装孔 (Mounting Hole)
    # 在 ZY 平面（即基座背面）绘制圆，沿 X 方向切穿
    sketch_hole = sw_doc.insert_sketch_on_plane("ZY")
    sw_doc.create_circle(0, 0, hole_diameter / 2, "ZY")
    sw_doc.extrude_cut(sketch_hole, depth=base_thickness)
    print("安装孔切除完成")

    # 4. 创建两个手指 (Fingers)
    # 在基座的前表面 (X = 0.06) 绘制两个矩形
    # 首先创建一个偏移平面作为手指的起始面
    finger_plane = sw_doc.create_workplane_p_d("ZY", base_thickness)
    sketch_fingers = sw_doc.insert_sketch_on_plane(finger_plane)
    
    # 左手指 (Y正向偏移)
    sw_doc.create_centre_rectangle(0, 0.025, finger_width, 0.030, "ZY")
    # 右手指 (Y负向偏移)
    sw_doc.create_centre_rectangle(0, -0.025, finger_width, 0.030, "ZY")
    
    # 拉伸手指 0.05m
    sw_doc.extrude(sketch_fingers, depth=finger_length, single_direction=True)
    print("手指特征拉伸完成")

    # 5. 创建装配接口
    # 接口1: mid_plane_y (对称中心面，即原始 XZ 平面)
    sw_doc.create_ref_plane("XZ", 0, target_plane_name="mid_plane_y")
    
    # 接口2: mount_axis_y (安装轴线，位于 X=0.03, Z=0 的 Y 向轴)
    # 轴线穿过基座中心孔
    sw_doc.create_axis((0, 0, 0), (0, 0.04, 0), axis_name="mount_axis_y")
    print("装配接口创建完成")

    # 6. 保存零件
    save_success = sw_doc.save_as(model_path)
    if save_success:
        print(f"零件成功保存至: {model_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()