from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化应用与零件文档
    app = SldWorksApp()
    part_name = "p00_base"
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    
    print(f"开始建模零件: {part_name}")

    # 2. 定义关键尺寸 (单位: m)
    length = 0.2      # X方向长度
    width = 0.15      # Y方向宽度
    height = 0.02     # Z方向高度 (底板厚度)
    boss_diam = 0.05  # 中心凸台直径
    boss_height = 0.01 # 中心凸台高度

    # 3. 创建底板主体
    # 在XY平面绘制矩形草图，中心在原点
    sketch_base = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=length, 
        height=width, 
        sketch_ref="XY"
    )
    # 拉伸底板，单向向上拉伸
    extrude_base = sw_doc.extrude(sketch_base, depth=height, single_direction=True, merge=True)
    print("底板主体创建完成")

    # 4. 创建中心凸台
    # 需要在底板顶面(Z=height)上创建草图。
    # 由于API限制，我们通常基于基准面偏移或直接使用坐标。
    # 这里我们在XY平面上画圆，然后拉伸到指定高度，或者更稳妥地：
    # 创建一个偏移平面作为草图基准，或者直接利用extrude的起始位置逻辑。
    # 根据API描述，insert_sketch_on_plane支持自定义平面名或基准面。
    # 为了精确控制凸台位于底板顶部，我们可以先创建一个参考平面，或者简单地在XY平面画圆，
    # 然后拉伸时设置合适的深度和方向。
    # 但更标准的做法是：在Z=height处建立草图。
    # 让我们尝试直接在XY平面画圆，然后拉伸。如果直接拉伸，它会从Z=0开始。
    # 我们需要它从Z=0.02开始。
    # 策略：在XY平面画圆，拉伸深度为boss_height，但是需要确保它与底板合并且位置正确。
    # 实际上，SolidWorks的Extrude默认从草图平面开始。
    # 所以，如果在XY平面画圆并拉伸0.01，它会占据Z=[0, 0.01]。这与底板Z=[0, 0.02]重叠。
    # 我们需要凸台在底板之上，即Z=[0.02, 0.03]。
    # 因此，我们需要一个位于Z=0.02的草图平面。
    
    # 创建偏移平面用于凸台草图
    plane_top = sw_doc.create_workplane_p_d(plane="XY", offset_val=height)
    
    sketch_boss = sw_doc.insert_sketch_on_plane(plane_top)
    sw_doc.create_circle(
        center_x=0, 
        center_y=0, 
        radius=boss_diam / 2, 
        sketch_ref="XY" # 注意：虽然平面是偏移的，但sketch_ref通常指代局部坐标系方向，对于平行于XY的平面，仍用"XY"
    )
    # 拉伸凸台，向上拉伸
    extrude_boss = sw_doc.extrude(sketch_boss, depth=boss_height, single_direction=True, merge=True)
    print("中心凸台创建完成")

    # 5. 创建装配接口 (参考几何)
    
    # 5.1 创建参考轴 AXIS_J1_Z
    # 穿过原点(0,0,0)和(0,0,1)，沿Z轴方向
    axis_j1 = sw_doc.create_axis(
        pt1=(0, 0, 0), 
        pt2=(0, 0, 1), 
        axis_name="AXIS_J1_Z"
    )
    print("参考轴 AXIS_J1_Z 创建完成")

    # 5.2 创建参考面 PL_BASE_TOP
    # 这是底板的顶面，位于Z=height。
    # 我们可以通过偏移XY平面来创建这个命名参考面，以便装配时引用。
    # 虽然实体表面存在，但显式创建命名参考面更稳定。
    plane_base_top = sw_doc.create_ref_plane(
        plane="XY", 
        offset_val=height, 
        target_plane_name="PL_BASE_TOP"
    )
    print("参考面 PL_BASE_TOP 创建完成")

    # 5.3 创建参考面 PL_BASE_ZERO_XZ
    # 这是一个平行于XZ平面且过原点(Y=0)的面。
    # XZ平面的法线是Y。
    plane_zero_xz = sw_doc.create_ref_plane(
        plane="XZ", 
        offset_val=0, 
        target_plane_name="PL_BASE_ZERO_XZ"
    )
    print("参考面 PL_BASE_ZERO_XZ 创建完成")

    # 6. 保存零件
    model_path = r"D:\a_src\python\sw_agent\agent_output\4DOF_Desktop_Robot_Arm-20260428_112023\parts\p00_base\p00_base.SLDPRT"
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"零件成功保存至: {model_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()