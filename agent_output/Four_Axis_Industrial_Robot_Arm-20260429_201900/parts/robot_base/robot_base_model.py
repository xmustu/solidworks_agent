from pysw import SldWorksApp, PartDoc
import os

def main():
    # 1. 初始化与创建零件
    # 零件 ID: robot_base
    # 目标路径: D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\robot_base\robot_base.SLDPRT
    model_path = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\robot_base\robot_base.SLDPRT"
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    app = SldWorksApp()
    sw_doc = PartDoc(app.createAndActivate_sw_part("robot_base"))
    print("开始建模零件: robot_base (底座)")

    # 2. 定义尺寸 (将 mm 转换为 m)
    base_diameter = 200 / 1000.0
    base_height = 150 / 1000.0
    hole_diameter = 50 / 1000.0
    hole_depth = 50 / 1000.0

    # 3. 创建主体：圆柱形底盘
    # 在 XY 平面绘制直径 200mm 的圆
    sketch_main = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(0, 0, base_diameter / 2.0, "XY")
    # 向 Z 正方向拉伸 150mm
    sw_doc.extrude(sketch_main, depth=base_height, single_direction=True)
    print(f"主体拉伸完成: 直径 {base_diameter}m, 高度 {base_height}m")

    # 4. 创建中心孔：顶部中心切除
    # 修复逻辑：在顶面创建参考平面，然后在此平面上绘制草图并向下切除
    # 创建位于 Z = base_height 的顶面参考平面
    top_plane = sw_doc.create_workplane_p_d("XY", base_height)
    
    # 在顶面参考平面上插入草图
    sketch_hole_top = sw_doc.insert_sketch_on_plane(top_plane)
    sw_doc.create_circle(0, 0, hole_diameter / 2.0, "XY")
    
    # 向下切除。在顶面草图上，深度为正值通常指向实体内部（-Z方向）
    # 如果 extrude_cut 默认方向不确定，使用 0.05m 深度。
    # 根据封装，正值为向平面法向量正方向切除。XY平面的法向是+Z。
    # 因为我们在 Z=0.15 处，要往回切，所以深度应为 -0.05m。
    sw_doc.extrude_cut(sketch_hole_top, depth=-hole_depth, single_direction=True)
    print(f"中心孔切除完成: 孔径 {hole_diameter}m, 深度 {hole_depth}m")

    # 5. 创建装配接口
    # 接口 1: bottom_face (地面固定面) - 位于 Z=0
    sw_doc.create_ref_plane("XY", 0, "bottom_face")
    
    # 接口 2: top_mount_face (回转台支撑面) - 位于 Z=150mm
    sw_doc.create_ref_plane("XY", base_height, "top_mount_face")
    
    # 接口 3: center_axis_z (第一轴旋转中心)
    sw_doc.create_axis((0, 0, 0), (0, 0, base_height), "center_axis_z")
    print("装配接口 (bottom_face, top_mount_face, center_axis_z) 创建完成")

    # 6. 保存零件
    sw_doc.save_as(model_path)
    print(f"零件已保存至: {model_path}")

if __name__ == "__main__":
    main()