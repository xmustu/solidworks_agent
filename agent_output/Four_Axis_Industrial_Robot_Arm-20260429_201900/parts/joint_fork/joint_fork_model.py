from pysw import SldWorksApp, PartDoc
import os

# 零件参数定义 (单位换算: mm -> m)
OPENING_WIDTH = 0.061  # 开口宽度 61mm
WALL_THICKNESS = 0.008 # 壁厚 8mm (根据装配建议，确保外宽 77mm < 销轴 80mm)
FORK_OUTER_WIDTH = OPENING_WIDTH + 2 * WALL_THICKNESS # 0.077m
TOTAL_LENGTH = 0.120   # 总长 120mm
FORK_DEPTH = 0.080     # U型槽深度
BASE_DIAMETER = 0.050  # 底部圆柱直径
HOLE_DIAMETER = 0.020  # 销轴孔径 20mm
HOLE_OFFSET_FROM_TOP = 0.020 # 孔中心距顶端距离

# 目标路径
model_path = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\joint_fork\joint_fork.SLDPRT"
model_dir = os.path.dirname(model_path)
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

# 1. 启动与创建零件
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("joint_fork"))
print("开始建模：关节叉 (joint_fork)")

# 2. 创建 U 型主体 (基于 XZ 平面拉伸，沿 Y 轴对称)
# 我们先画一个外轮廓矩形，然后拉伸，再切除中间的槽
# 这样可以方便地定义 mid_plane_y
sketch1 = sw_doc.insert_sketch_on_plane("XZ")
# 中心矩形：中心在(0,0)，宽度为总长120mm(X)，高度为外宽77mm(Y)
# 注意：在XZ平面，create_centre_rectangle 的 width 对应 X，height 对应 Y (即装配中的 Y)
sw_doc.create_centre_rectangle(center_x=TOTAL_LENGTH/2, center_y=0, width=TOTAL_LENGTH, height=FORK_OUTER_WIDTH, sketch_ref="XZ")
extrude1 = sw_doc.extrude(sketch1, depth=0.040, single_direction=False) # 双向拉伸总厚度 40mm (Z方向)
print("主体块创建完成")

# 3. 切除 U 型槽
# 在 XZ 平面（或顶面）切除
sketch2 = sw_doc.insert_sketch_on_plane("XZ")
# 槽的起始位置在 X 轴末端，宽度为 61mm，深度为 80mm
# 矩形中心 X = TOTAL_LENGTH - FORK_DEPTH/2, Y = 0
sw_doc.create_centre_rectangle(center_x=TOTAL_LENGTH - FORK_DEPTH/2, center_y=0, width=FORK_DEPTH, height=OPENING_WIDTH, sketch_ref="XZ")
sw_doc.extrude_cut(sketch2, depth=0.1, single_direction=False) # 贯穿切除
print("U型槽切除完成")

# 4. 打销轴孔 (穿过两个叉壁)
# 在 XY 平面（侧面）打孔，孔中心位于 X = TOTAL_LENGTH - HOLE_OFFSET_FROM_TOP, Y = 0
sketch3 = sw_doc.insert_sketch_on_plane("XY")
sw_doc.create_circle(center_x=TOTAL_LENGTH - HOLE_OFFSET_FROM_TOP, center_y=0, radius=HOLE_DIAMETER/2, sketch_ref="XY")
sw_doc.extrude_cut(sketch3, depth=0.1, single_direction=False)
print("销轴孔加工完成")

# 5. 创建接口
# 接口：mid_plane_y (XZ基准面即为对称中心面)
sw_doc.create_ref_plane("XZ", 0, target_plane_name="mid_plane_y")

# 接口：base_face (底部安装面，位于 X=0 的平面)
# 创建一个在 X=0 处的参考面
sw_doc.create_ref_plane("ZY", 0, target_plane_name="base_face")

# 接口：hinge_axis_y (关节旋转轴)
# 轴线位于 X = TOTAL_LENGTH - HOLE_OFFSET_FROM_TOP, Z = 0, 沿 Y 轴
pt1 = (TOTAL_LENGTH - HOLE_OFFSET_FROM_TOP, -FORK_OUTER_WIDTH/2, 0)
pt2 = (TOTAL_LENGTH - HOLE_OFFSET_FROM_TOP, FORK_OUTER_WIDTH/2, 0)
sw_doc.create_axis(pt1, pt2, axis_name="hinge_axis_y")
print("装配接口创建完成")

# 6. 保存零件
sw_doc.save_as(model_path)
print(f"零件建模成功，保存路径: {model_path}")