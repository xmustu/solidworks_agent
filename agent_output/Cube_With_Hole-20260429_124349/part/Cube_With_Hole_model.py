# -*- coding: utf-8 -*-
import sys
import os

# 尝试导入 pyswassem，如果失败则添加可能的路径
try:
    from pyswassem import SldWorksApp, PartDoc
except ImportError:
    # 常见的安装路径或相对路径
    possible_paths = [
        r"D:\CAutoD\pysw_assem",
        os.path.join(os.getcwd(), "..", "pysw_assem"),
        os.path.join(os.getcwd(), "pysw_assem")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            sys.path.insert(0, p)
            break
    try:
        from pyswassem import SldWorksApp, PartDoc
    except ImportError:
        print("错误: 无法找到 pyswassem 模块。请确保环境配置正确。")
        sys.exit(1)

def main():
    print("=== 开始建模 Cube_With_Hole ===")
    
    # 1. 初始化应用与零件文档
    try:
        app = SldWorksApp()
        part_name = "Cube_With_Hole"
        print(f"创建并激活零件: {part_name}")
        sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))
    except Exception as e:
        print(f"初始化 SolidWorks 失败: {e}")
        return

    # 2. 定义尺寸参数 (单位: m)
    # 输入尺寸为 mm，需转换为 m
    cube_side_mm = 100.0
    hole_diam_mm = 20.0
    
    cube_side_m = cube_side_mm / 1000.0  # 0.1 m
    hole_radius_m = (hole_diam_mm / 1000.0) / 2.0  # 0.01 m
    
    print(f"建模参数: 正方体边长={cube_side_m}m, 孔半径={hole_radius_m}m")

    # 3. 创建主体：正方体
    # 在 XY 平面绘制中心矩形
    print("步骤 1: 创建正方体主体草图 (XY平面)")
    try:
        sketch_base = sw_doc.insert_sketch_on_plane("XY")
        
        # 创建以原点为中心的正方形
        # create_centre_rectangle(center_x, center_y, width, height, sketch_ref)
        sw_doc.create_centre_rectangle(
            center_x=0.0, 
            center_y=0.0, 
            width=cube_side_m, 
            height=cube_side_m, 
            sketch_ref="XY"
        )
        
        # 拉伸生成实体
        print("步骤 2: 拉伸生成正方体")
        extrude_body = sw_doc.extrude(sketch_base, depth=cube_side_m, single_direction=True, merge=True)
    except Exception as e:
        print(f"创建主体失败: {e}")
        return

    # 4. 创建通孔
    # 需要在顶面（Z轴正向面）中心创建圆形草图
    # 顶面的 Z 坐标为 cube_side_m
    print("步骤 3: 创建通孔草图 (顶面)")
    
    try:
        # 为了在顶面画草图，创建一个偏移平面，位于 Z=cube_side_m
        # 使用 create_workplane_p_d 基于 XY 平面偏移
        top_plane = sw_doc.create_workplane_p_d("XY", offset_val=cube_side_m)
        
        # 在该平面上插入草图
        sketch_hole = sw_doc.insert_sketch_on_plane(top_plane)
        
        # 在草图中心 (0,0) 绘制圆
        # 注意：sketch_ref 需要与当前草图平面的局部坐标系一致。
        # 对于平行于 XY 的偏移平面，通常仍使用 "XY" 作为参考系标识
        sw_doc.create_circle(
            center_x=0.0, 
            center_y=0.0, 
            radius=hole_radius_m, 
            sketch_ref="XY" 
        )
        
        # 拉伸切除，贯穿整个实体
        # 顶面法线指向 +Z。我们要往 -Z 方向切（进入实体）。
        # extrude_cut 的 depth 正值为向平面法向量正方向切除。
        # 因此，要向下切，depth 应为负值。
        # 深度设为 -cube_side_m 即可刚好切到底部表面。
        print("步骤 4: 拉伸切除生成通孔")
        cut_hole = sw_doc.extrude_cut(sketch_hole, depth=-cube_side_m, single_direction=True)
    except Exception as e:
        print(f"创建通孔失败: {e}")
        return

    # 5. 保存文件
    output_path = r"D:\CAutoD\solidworks_agent\agent_output\Cube_With_Hole-20260429_124349\part\Cube_With_Hole.SLDPRT"
    print(f"正在保存零件到: {output_path}")
    
    try:
        success = sw_doc.save_as(output_path)
        if success:
            print("零件建模与保存成功完成。")
        else:
            print("零件保存返回失败状态。")
    except Exception as e:
        print(f"保存文件时发生异常: {e}")

if __name__ == "__main__":
    main()