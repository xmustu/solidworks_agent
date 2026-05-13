from pysw import SldWorksApp, PartDoc
import os

# 零件参数定义 (单位换算: mm -> m)
LENGTH = 0.400  # 400mm 臂长 (孔中心距)
END_THICKNESS = 0.060  # 60mm 端部厚度
HOLE_DIAM = 0.020  # 20mm 销轴孔径
ARM_WIDTH = 0.050  # 50mm 臂身宽度
END_RADIUS = 0.035  # 35mm 端部圆角半径

# 文件路径
model_file = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\hollow_link\hollow_link.SLDPRT"
model_dir = os.path.dirname(model_file)

if not os.path.exists(model_dir):
    os.makedirs(model_dir)

def main():
    # 1. 启动与创建零件
    app = SldWorksApp()
    sw_doc = PartDoc(app.createAndActivate_sw_part("hollow_link"))
    print("开始建模连杆 (hollow_link)...")

    # 2. 建立主体结构
    # 之前的失败可能是因为草图包含多个重叠闭合区域（两个圆+一个矩形）导致拉伸歧义。
    # 改进策略：分步拉伸，先拉伸中间臂身，再拉伸两端圆柱。
    
    # 2.1 拉伸中间臂身
    sketch_arm = sw_doc.insert_sketch_on_plane("XZ")
    sw_doc.create_centre_rectangle(LENGTH/2, 0, LENGTH, ARM_WIDTH, "XZ")
    sw_doc.extrude(sketch_arm, depth=END_THICKNESS, single_direction=False)
    print("臂身拉伸完成")

    # 2.2 拉伸两端圆柱 (合并到主体)
    sketch_ends = sw_doc.insert_sketch_on_plane("XZ")
    sw_doc.create_circle(0, 0, END_RADIUS, "XZ")
    sw_doc.create_circle(LENGTH, 0, END_RADIUS, "XZ")
    sw_doc.extrude(sketch_ends, depth=END_THICKNESS, single_direction=False, merge=True)
    print("两端圆柱拉伸完成")

    # 3. 切除销轴孔
    sketch_holes = sw_doc.insert_sketch_on_plane("XZ")
    sw_doc.create_circle(0, 0, HOLE_DIAM/2, "XZ")
    sw_doc.create_circle(LENGTH, 0, HOLE_DIAM/2, "XZ")
    # 使用正值深度进行双向切除
    sw_doc.extrude_cut(sketch_holes, depth=END_THICKNESS, single_direction=False)
    print(f"销轴孔切除完成，孔径: {HOLE_DIAM}m")

    # 4. 添加减重孔
    sketch_weight = sw_doc.insert_sketch_on_plane("XZ")
    # 使用较小的矩形作为减重孔
    sw_doc.create_centre_rectangle(LENGTH/2, 0, LENGTH * 0.5, ARM_WIDTH * 0.5, "XZ")
    sw_doc.extrude_cut(sketch_weight, depth=END_THICKNESS, single_direction=False)
    print("减重孔特征添加完成")

    # 5. 创建装配接口
    # 5.1 轴接口: 起始端旋转轴 (Y方向)
    sw_doc.create_axis((0, -END_THICKNESS/2, 0), (0, END_THICKNESS/2, 0), "start_axis_y")
    # 5.2 轴接口: 末端旋转轴 (Y方向)
    sw_doc.create_axis((LENGTH, -END_THICKNESS/2, 0), (LENGTH, END_THICKNESS/2, 0), "end_axis_y")
    # 5.3 面接口: 对称中心面 (XZ平面即为 mid_plane_y)
    sw_doc.create_ref_plane("XZ", 0, "mid_plane_y")
    
    print("装配接口 (start_axis_y, end_axis_y, mid_plane_y) 创建完成")

    # 6. 保存零件
    sw_doc.save_as(model_file)
    print(f"零件建模成功，保存至: {model_file}")

if __name__ == "__main__":
    main()