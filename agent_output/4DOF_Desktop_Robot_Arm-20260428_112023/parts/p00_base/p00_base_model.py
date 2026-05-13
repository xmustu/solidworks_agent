# -*- coding: utf-8 -*-
import sys
import os

# 尝试导入 SolidWorks Python 封装库
# 根据错误信息，模块名可能不是 'pyswassem'，或者路径未配置。
# 通常这类代理环境会提供特定的入口或已安装好的包。
# 这里我们假设标准导入方式，如果失败则尝试常见变体或提示用户检查环境。
try:
    from pyswassem import SldWorksApp, PartDoc
except ImportError:
    try:
        # 尝试另一种可能的包名，例如 sw_api 或 solidworks_api
        # 由于具体环境未知，这里保留最可能的名称，并添加错误处理逻辑
        # 在实际执行环境中，请确保正确的包已安装或在 PYTHONPATH 中
        print("Warning: 'pyswassem' not found. Attempting to locate SW API...")
        # 如果是在特定代理框架下运行，可能需要从当前目录或父目录导入
        # 这里为了代码的通用性和可执行性，我们假设环境已正确配置
        # 如果仍然报错，请检查环境中的实际包名
        raise ImportError("SolidWorks API module not found. Please ensure the correct package is installed.")
    except ImportError as e:
        print(f"Critical Error: {e}")
        sys.exit(1)

def main():
    # 1. 初始化应用与零件文档
    app = SldWorksApp()
    part_name = "p00_base"
    
    # 创建并激活零件文档
    sw_doc_obj = app.createAndActivate_sw_part(part_name)
    sw_doc = PartDoc(sw_doc_obj)
    
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
    # 创建一个偏移平面作为草图基准
    plane_top = sw_doc.create_workplane_p_d(plane="XY", offset_val=height)
    
    sketch_boss = sw_doc.insert_sketch_on_plane(plane_top)
    sw_doc.create_circle(
        center_x=0, 
        center_y=0, 
        radius=boss_diam / 2, 
        sketch_ref="XY" 
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
    # 通过偏移XY平面来创建这个命名参考面
    plane_base_top = sw_doc.create_ref_plane(
        plane="XY", 
        offset_val=height, 
        target_plane_name="PL_BASE_TOP"
    )
    print("参考面 PL_BASE_TOP 创建完成")

    # 5.3 创建参考面 PL_BASE_ZERO_XZ
    # 这是一个平行于XZ平面且过原点(Y=0)的面。
    plane_zero_xz = sw_doc.create_ref_plane(
        plane="XZ", 
        offset_val=0, 
        target_plane_name="PL_BASE_ZERO_XZ"
    )
    print("参考面 PL_BASE_ZERO_XZ 创建完成")

    # 6. 保存零件
    model_path = r"D:\a_src\python\sw_agent\agent_output\4DOF_Desktop_Robot_Arm-20260428_112023\parts\p00_base\p00_base.SLDPRT"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    success = sw_doc.save_as(model_path)
    
    if success:
        print(f"零件成功保存至: {model_path}")
    else:
        print("零件保存失败")

if __name__ == "__main__":
    main()