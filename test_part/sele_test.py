from pysw import SldWorksApp, PartDoc

# 1. 初始化应用
app = SldWorksApp()
sw_doc = app.createAndActivate_sw_part("SimpleBox")

if sw_doc:
    part = PartDoc(sw_doc)
    
    # 2. 在 XY 平面上创建草图
    sketch = part.insert_sketch_on_plane("XY")
    
    # 3. 绘制一个方形
    rect = part.create_centre_rectangle(
        center_x=0, 
        center_y=0, 
        width=0.04,    # 40mm
        height=0.02,   # 20mm
        sketch_ref="XY"
    )
    
    # 4. 拉伸形成 3D 实体
    feature = part.extrude(sketch=sketch, depth=0.01, single_direction=True)

    edge_pts = [(0.02,0.01,0.01), (-0.02,0.01,0.01), (-0.02,-0.01,0.01), (0.02,-0.01,0.01)]
    # for pt in edge_pts:
    #     sel_status = part.select_edge_by_coordinates(*pt,append = True)
    #     if sel_status:
    #         print(f"✅ 成功选择边缘点: {pt}")
    #     else:
    #         print(f"❌ 选择边缘点失败: {pt}")
    part.chamfer_edges(edge_pts,0.001)  # 倒角 1mm
    # sel_status = part.select_face_by_coordinates(0, 0, 0.01, append=False)  # 选择顶部面
    # if sel_status:
    #     print("✅ 成功选择顶部面")
    # else:        print("❌ 选择顶部面失败")
    part.shell([(0,0,0.01)], 0.002)  # 壳体厚度 2mm

    part.color("orange", transparency=0.0)
    
    print("✅ 零件创建成功！")
else:
    print("❌ 零件创建失败")