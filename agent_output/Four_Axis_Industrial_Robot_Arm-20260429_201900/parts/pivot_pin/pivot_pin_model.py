import os
from pysw import SldWorksApp, PartDoc

def main():
    # 1. 初始化与创建零件
    # 零件 ID: pivot_pin
    # 目标路径: D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\pivot_pin\pivot_pin.SLDPRT
    model_file = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\pivot_pin\pivot_pin.SLDPRT"
    model_dir = os.path.dirname(model_file)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    app = SldWorksApp()
    sw_doc = PartDoc(app.createAndActivate_sw_part("pivot_pin"))
    print("已创建零件文档: pivot_pin")

    # 2. 参数定义 (单位换算: mm -> m)
    diameter = 19.5 / 1000.0
    length = 80.0 / 1000.0
    radius = diameter / 2.0
    chamfer_dist = 1.0 / 1000.0

    # 3. 建模步骤
    # 步骤 1: 在 ZY 平面绘制圆并沿 X 轴拉伸 (为了符合接口中 main_axis 沿 local X 的定义)
    print(f"正在创建主体圆柱: 直径 {diameter*1000}mm, 长度 {length*1000}mm")
    sketch1 = sw_doc.insert_sketch_on_plane("ZY")
    sw_doc.create_circle(0, 0, radius, "ZY")
    # 拉伸深度为 length，单向拉伸
    sw_doc.extrude(sketch1, depth=length, single_direction=True)

    # 步骤 2: 添加倒角
    # 倒角位置：两端的圆周边。
    # 起点面在 ZY 平面 (X=0)，终点面在 X=length。
    # 边上的点坐标：(0, radius, 0) 和 (length, radius, 0)
    print(f"正在添加倒角: {chamfer_dist*1000}mm x 45度")
    edge_points = [
        (0.0, radius, 0.0),
        (length, radius, 0.0)
    ]
    sw_doc.chamfer_edges(edge_points, distance=chamfer_dist, angle=45.0)

    # 4. 创建装配接口
    # 接口 1: main_axis (中心轴线，沿 local X)
    print("正在创建参考轴接口: main_axis")
    sw_doc.create_axis((0, 0, 0), (length, 0, 0), axis_name="main_axis")

    # 接口 2: end_face (轴向定位面，法向 X)
    # 我们可以通过在 X=0 处创建一个参考面来显式命名
    print("正在创建参考面接口: end_face")
    sw_doc.create_ref_plane("ZY", 0, target_plane_name="end_face")
    
    # 备注：cylinder_surface 接口通常在装配时通过选择圆柱面实体即可，无需额外创建参考几何体。

    # 5. 保存零件
    save_success = sw_doc.save_as(model_file)
    if save_success:
        print(f"零件建模完成并成功保存至: {model_file}")
    else:
        print("零件保存失败，请检查路径或权限。")

if __name__ == "__main__":
    main()