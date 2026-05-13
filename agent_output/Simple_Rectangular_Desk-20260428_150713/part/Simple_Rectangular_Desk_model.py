# -*- coding: utf-8 -*-
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 启动与创建
    app = SldWorksApp()
    part_name = "Simple_Rectangular_Desk"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模零件: {part_name}")

    # 2. 参数定义 (单位: m)
    # 桌面尺寸
    desk_length = 1.200  # 1200 mm
    desk_width = 0.600   # 600 mm
    desk_thickness = 0.025 # 25 mm
    
    # 桌腿尺寸
    leg_side = 0.040     # 40 mm
    leg_height = 0.725   # 725 mm
    
    # 位置参数
    # 桌腿位于桌面四角内侧，距边缘内缩 20mm (0.02m)
    inset = 0.020
    
    # 计算桌腿中心坐标 (相对于桌面中心原点)
    # X方向半长: 0.6, Y方向半宽: 0.3
    half_len = desk_length / 2.0
    half_wid = desk_width / 2.0
    
    # 桌腿中心到原点的距离
    # 桌腿外边缘距桌面边缘 inset
    # 桌腿中心距桌面边缘 = inset + leg_side/2
    leg_center_x_offset = half_len - (inset + leg_side / 2.0)
    leg_center_y_offset = half_wid - (inset + leg_side / 2.0)
    
    # 四个桌腿的中心坐标 (x, y)
    leg_positions = [
        (-leg_center_x_offset, -leg_center_y_offset), # 左下
        (leg_center_x_offset, -leg_center_y_offset),  # 右下
        (leg_center_x_offset, leg_center_y_offset),   # 右上
        (-leg_center_x_offset, leg_center_y_offset)   # 左上
    ]

    # 3. 建模步骤
    
    # --- 3.1 创建桌面 ---
    # 在 XY 平面绘制桌面草图
    sketch_desktop = sw_doc.insert_sketch_on_plane("XY")
    # 中心矩形，中心(0,0)，长1.2，宽0.6
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=desk_length, 
        height=desk_width, 
        sketch_ref="XY"
    )
    # 拉伸桌面，厚度 0.025m，向上(Z正方向)
    # 注意：SolidWorks默认Z轴向上。如果XY是地面，通常Z向上。
    # 这里假设桌面底面在 Z=0，顶面在 Z=0.025
    extrude_desktop = sw_doc.extrude(sketch_desktop, depth=desk_thickness, single_direction=True, merge=True)
    print("桌面创建完成")

    # --- 3.2 创建桌腿 ---
    # 桌腿从桌面底面 (Z=0) 向下延伸? 
    # 需求描述: "总高750mm", "桌面厚25mm", "桌腿高725mm". 
    # 通常桌子是桌面在上，桌腿在下支撑。
    # 如果坐标系原点在桌面中心，且Z向上：
    # 桌面占据 Z=[0, 0.025] (假设底面为基准) 或者 Z=[-0.0125, 0.0125]?
    # 让我们重新审视坐标系要求："坐标系：XY平面为地面，Z轴向上，桌面中心对齐原点"
    # 这意味着：
    # 地面是 Z=0。
    # 桌面中心在原点 (0,0,0)? 这不可能，因为桌面有厚度且在地面上方。
    # 通常“桌面中心对齐原点”指的是水平面的中心 (X,Y)=(0,0)。
    # 垂直方向：如果XY是地面，那么桌腿底部应该在 Z=0 附近？
    # 不，通常建模时，为了方便，会将主要特征放在原点。
    # 让我们解读：“XY平面为地面... 桌面中心对齐原点”。
    # 这可能意味着原点是桌面的几何中心 (X=0, Y=0, Z=Height/2?) 或者仅仅是水平中心。
    # 结合“总高750mm”，如果地面是Z=0，桌面顶部可能在 Z=0.750。
    # 桌面厚度 0.025，所以桌面底部在 Z=0.725。
    # 桌腿高度 0.725，连接桌面底部到地面。
    # 这样桌腿范围 Z=[0, 0.725]。
    # 桌面范围 Z=[0.725, 0.750]。
    # 这种解释符合物理逻辑。
    
    # 但是，API `extrude` 是基于当前草图平面的法向。
    # 如果我们在 XY 平面 (Z=0) 画草图并拉伸，它会在 Z>0 或 Z<0 生成实体。
    # 为了简化，我们可以先建立桌面，再建立桌腿，最后移动或调整位置？
    # 不，最好直接按坐标建模。
    
    # 策略调整：
    # 1. 在 Z=0.725 处创建一个工作平面用于桌面？或者直接在 XY 平面画桌面，然后移动？
    # SolidWorks API 中，草图通常依附于基准面。
    # 让我们先在 XY 平面 (Z=0) 创建桌面草图，拉伸得到桌面实体 (Z: 0 -> 0.025)。
    # 然后创建桌腿，从 Z=0 向下？不，桌腿应该支撑桌面。
    # 如果桌面在 Z: 0->0.025，桌腿应该在 Z: -0.725 -> 0。
    # 这样总高是 0.750。
    # 但需求说“XY平面为地面”。如果地面是 Z=0，桌腿底部应在 Z=0。
    # 那么桌面应该在 Z=0.725 以上。
    
    # 让我们采用以下坐标系构建方式以符合“XY为地面”：
    # 1. 创建桌腿：在 XY 平面 (Z=0) 画桌腿截面，向上拉伸 0.725m。
    #    这样桌腿占据 Z: 0 -> 0.725。
    # 2. 创建桌面：需要在 Z=0.725 处有一个平面。
    #    我们可以创建一个偏移平面 OffsetPlane_TopLegs 在 Z=0.725。
    #    在该平面上画桌面草图，向上拉伸 0.025m。
    #    这样桌面占据 Z: 0.725 -> 0.750。
    #    总高 0.750m。符合题意。
    
    # --- 3.2.1 创建桌腿 ---
    # 我们需要在 XY 平面 (Z=0) 上为每个桌腿画一个正方形。
    # 由于有4个桌腿，我们可以画在一个草图里，或者分开。
    # 为了清晰，我们可以在一个草图中画出4个正方形，然后一次性拉伸。
    
    sketch_legs = sw_doc.insert_sketch_on_plane("XY")
    
    for pos in leg_positions:
        cx, cy = pos
        # 创建中心矩形作为桌腿截面
        # 边长 0.04m
        sw_doc.create_centre_rectangle(
            center_x=cx,
            center_y=cy,
            width=leg_side,
            height=leg_side,
            sketch_ref="XY"
        )
        
    # 拉伸桌腿，高度 0.725m，向上 (Z正方向)
    extrude_legs = sw_doc.extrude(sketch_legs, depth=leg_height, single_direction=True, merge=True)
    print("桌腿创建完成")

    # --- 3.2.2 创建桌面 ---
    # 创建参考平面，位于 Z = leg_height (0.725)
    # 基于 XY 平面偏移
    plane_desktop_bottom = sw_doc.create_workplane_p_d(plane="XY", offset_val=leg_height)
    
    # 在该平面上插入草图
    sketch_desktop_top = sw_doc.insert_sketch_on_plane(plane_desktop_bottom)
    
    # 绘制桌面矩形
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=desk_length,
        height=desk_width,
        sketch_ref="XY" # 注意：虽然平面是偏移的，但 sketch_ref 通常指代局部坐标系的参考，对于平行于XY的平面，仍用XY
    )
    
    # 拉伸桌面，厚度 0.025m，向上
    extrude_desktop_top = sw_doc.extrude(sketch_desktop_top, depth=desk_thickness, single_direction=True, merge=True)
    print("桌面创建完成")

    # 4. 细节特征
    
    # --- 4.1 桌面边缘 C2 倒角 ---
    # C2 表示 2mm x 45度 倒角。
    # 需要选择桌面的顶面边缘。
    # 桌面顶面 Z = 0.750。
    # 边缘点可以取桌面顶面的四个角点附近。
    # 角点坐标: (+-0.6, +-0.3, 0.750)
    
    chamfer_points = [
        (0.6, 0.3, 0.750),
        (-0.6, 0.3, 0.750),
        (0.6, -0.3, 0.750),
        (-0.6, -0.3, 0.750)
    ]
    
    # 倒角距离 0.002m (2mm), 角度 45度
    try:
        sw_doc.chamfer_edges(on_line_points=chamfer_points, distance=0.002, angle=45.0)
        print("桌面边缘倒角完成")
    except Exception as e:
        print(f"桌面边缘倒角失败: {e}")

    # --- 4.2 桌腿底部 R2 圆角 ---
    # R2 表示半径 2mm 的圆角。
    # 桌腿底部在 Z=0。
    # 需要选择桌腿底部的边缘。
    # 每个桌腿底部有4条边。
    # 我们可以选取每条边的中点或端点来定位。
    # 桌腿截面 40x40mm，中心在 (cx, cy)。
    # 底部边的 Z=0。
    # 例如，右前桌腿 (cx, cy) = (leg_center_x_offset, -leg_center_y_offset)
    # 其底部四条边的中点大致在:
    # x = cx +/- 0.02, y = cy, z = 0 (前后边)
    # x = cx, y = cy +/- 0.02, z = 0 (左右边)
    
    fillet_points = []
    half_leg = leg_side / 2.0 # 0.02
    
    for pos in leg_positions:
        cx, cy = pos
        # 添加该桌腿底部四条边的代表点
        # 为了稳健，每条边选一个点
        fillet_points.append((cx + half_leg, cy, 0.0)) # 右边中点
        fillet_points.append((cx - half_leg, cy, 0.0)) # 左边中点
        fillet_points.append((cx, cy + half_leg, 0.0)) # 上边中点
        fillet_points.append((cx, cy - half_leg, 0.0)) # 下边中点
        
    try:
        sw_doc.fillet_edges(on_line_points=fillet_points, radius=0.002)
        print("桌腿底部圆角完成")
    except Exception as e:
        print(f"桌腿底部圆角失败: {e}")

    # 5. 保存文件
    model_path = r"D:\a_src\python\sw_agent\agent_output\Simple_Rectangular_Desk-20260428_150713\part\Simple_Rectangular_Desk.SLDPRT"
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"模型已成功保存至: {model_path}")
    else:
        print("模型保存失败")

if __name__ == "__main__":
    main()