from pysw import SldWorksApp, PartDoc
import math

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    sw_doc = PartDoc(app.createAndActivate_sw_part("BasePlate"))

    # 参数定义 (单位: m)
    diameter = 0.200      # D200mm
    height = 0.030        # H30mm
    center_hole_dia = 0.050 # D50mm
    pcd = 0.160           # PCD 160mm
    mount_hole_dia = 0.008 # M8 hole approx D8mm for clearance/modeling simplicity
    chamfer_dist = 0.001  # C1 chamfer

    print("Step 1: Creating base disk...")
    # 2. 建模主体
    # 在 XY 平面绘制外圆
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(center_x=0, center_y=0, radius=diameter/2, sketch_ref="XY")
    # 拉伸高度 30mm (+Z)
    extrude_body = sw_doc.extrude(sketch_base, depth=height, single_direction=True, merge=True)

    print("Step 2: Cutting center hole...")
    # 在顶面 (Z=0.03) 或直接在 XY 平面画孔并切除贯穿
    # 为了简单，我们在 XY 平面画中心孔草图，然后做贯穿切除
    sketch_center_hole = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(center_x=0, center_y=0, radius=center_hole_dia/2, sketch_ref="XY")
    # 切除贯穿 (深度设为大于高度即可，或者使用 Through All 逻辑，这里用足够大的深度)
    sw_doc.extrude_cut(sketch_center_hole, depth=-0.1, single_direction=True) # 向 -Z 切穿，或者双向。通常切除是相对于草图平面法向。
    # 注意：extrude_cut 的 depth 正负取决于法向。XY 平面法向通常是 +Z。
    # 如果要切穿整个实体，且实体在 +Z 方向，我们需要向 +Z 方向切除吗？
    # 不，实体是从 Z=0 到 Z=0.03。如果在 Z=0 画草图，向 +Z 切除会切掉实体。
    # 让我们修正：在 XY (Z=0) 画草图，向 +Z 切除 0.04m (大于厚度)。
    # 重新执行切除逻辑以确保正确性：
    # 上面的 create_circle 已经在 sketch_center_hole 中。
    # 调用 extrude_cut
    cut_feature = sw_doc.extrude_cut(sketch_center_hole, depth=0.04, single_direction=True)

    print("Step 3: Creating mounting holes...")
    # 在顶面 (Z=0.03) 创建安装孔草图
    # 首先创建一个偏移平面或者直接引用 Top Face? 
    # API 允许 insert_sketch_on_plane 使用 "XY" 等，但要在特定高度，最好创建参考平面或使用现有面。
    # 这里我们创建一个位于 Z=0.03 的参考平面用于草图，或者直接在 XY 平面画然后指定切除深度从顶部开始？
    # 更稳健的方法：创建参考平面 TopPlane at Z=0.03
    top_plane = sw_doc.create_workplane_p_d("XY", offset_val=height)
    
    sketch_mount_holes = sw_doc.insert_sketch_on_plane(top_plane)
    
    # 计算 4 个孔的位置 (PCD 160mm -> Radius 80mm)
    r_pcd = pcd / 2
    angles = [45, 135, 225, 315] # 均布
    
    for angle_deg in angles:
        rad = math.radians(angle_deg)
        x = r_pcd * math.cos(rad)
        y = r_pcd * math.sin(rad)
        sw_doc.create_circle(center_x=x, center_y=y, radius=mount_hole_dia/2, sketch_ref="XY") # sketch_ref 对应平面的局部坐标，TopPlane 平行于 XY，所以用 XY 参考系逻辑
        
    # 切除贯穿向下
    sw_doc.extrude_cut(sketch_mount_holes, depth=-0.04, single_direction=True) # 向 -Z 切穿

    print("Step 4: Applying Chamfers...")
    # 对上下外边缘进行 C1 倒角
    # 需要定位边上的点。
    # 底面外边缘：Z=0, R=0.1
    # 顶面外边缘：Z=0.03, R=0.1
    
    # 底面边缘点 (例如 X=0.1, Y=0, Z=0)
    pt_bottom_edge = (0.1, 0, 0)
    # 顶面边缘点 (例如 X=0.1, Y=0, Z=0.03)
    pt_top_edge = (0.1, 0, 0.03)
    
    # 应用倒角
    sw_doc.chamfer_edges(on_line_points=[pt_bottom_edge], distance=chamfer_dist, angle=45.0)
    sw_doc.chamfer_edges(on_line_points=[pt_top_edge], distance=chamfer_dist, angle=45.0)

    print("Step 5: Creating Interfaces...")
    # 创建参考轴：Center Axis Z
    # 从 (0,0,0) 到 (0,0,1)
    axis_z = sw_doc.create_axis(pt1=(0, 0, 0), pt2=(0, 0, 1), axis_name="center_axis_z")
    
    # 创建参考面：Bottom Face (Z=0) 和 Top Face (Z=0.03)
    # 虽然基准面 XY 存在，但为了装配接口明确性，创建命名参考面
    ref_bottom = sw_doc.create_ref_plane(plane="XY", offset_val=0, target_plane_name="bottom_face")
    ref_top = sw_doc.create_ref_plane(plane="XY", offset_val=height, target_plane_name="top_face")

    print("Step 6: Saving part...")
    # 保存文件
    save_path = r"D:\a_src\python\sw_agent\agent_output\FourAxisIndustrialArm_Assembly-20260429_195742\parts\base_plate\base_plate.SLDPRT"
    success = sw_doc.save_as(save_path)
    
    if success:
        print(f"Part saved successfully to {save_path}")
    else:
        print("Failed to save part.")

if __name__ == "__main__":
    main()