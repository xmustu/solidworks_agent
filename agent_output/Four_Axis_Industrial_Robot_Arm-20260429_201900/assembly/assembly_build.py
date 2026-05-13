from pysw import SldWorksApp, AssemDoc
import os

def build_assembly():
    # 1. 初始化 SolidWorks 应用
    sw_app = SldWorksApp()
    assem_name = "Four_Axis_Industrial_Robot_Arm"
    
    # 2. 创建并激活装配体文档
    print(f"正在创建装配体: {assem_name}")
    sw_assem_obj = sw_app.createAndActivate_sw_assembly(assem_name)
    sw_assem = AssemDoc(sw_assem_obj)
    
    # 3. 定义零件路径映射 (part_id -> model_file)
    part_paths = {
        "robot_base": r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\robot_base\robot_base.SLDPRT",
        "turntable": r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\turntable\turntable.SLDPRT",
        "joint_fork": r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\joint_fork\joint_fork.SLDPRT",
        "hollow_link": r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\hollow_link\hollow_link.SLDPRT",
        "pivot_pin": r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\pivot_pin\pivot_pin.SLDPRT",
        "gripper": r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\parts\gripper\gripper.SLDPRT"
    }

    # 4. 插入组件实例并记录组件名 (instance_id -> comp_name)
    comp_map = {}
    
    print("正在插入组件实例...")
    # 按顺序插入
    comp_map["base_inst"] = sw_assem.add_component(part_paths["robot_base"], 0, 0, 0)
    comp_map["turntable_inst"] = sw_assem.add_component(part_paths["turntable"], 0, 0, 0.15)
    comp_map["link_upper_arm"] = sw_assem.add_component(part_paths["hollow_link"], 0, 0, 0.25)
    comp_map["fork_elbow"] = sw_assem.add_component(part_paths["joint_fork"], 0.4, 0, 0.25)
    comp_map["link_forearm"] = sw_assem.add_component(part_paths["hollow_link"], 0.4, 0, 0.35)
    comp_map["fork_wrist"] = sw_assem.add_component(part_paths["joint_fork"], 0.8, 0, 0.35)
    comp_map["gripper_inst"] = sw_assem.add_component(part_paths["gripper"], 0.9, 0, 0.35)
    
    # 插入销轴（重复件）
    comp_map["pin_shoulder"] = sw_assem.add_component(part_paths["pivot_pin"], 0, 0, 0.25)
    comp_map["pin_elbow"] = sw_assem.add_component(part_paths["pivot_pin"], 0.4, 0, 0.25)
    comp_map["pin_wrist"] = sw_assem.add_component(part_paths["pivot_pin"], 0.8, 0, 0.35)

    # 5. 执行配合约束
    print("正在施加配合约束...")

    # --- 1. 底座与地面 (固定) ---
    # 默认第一个插入的组件通常是固定的，此处根据规划逻辑执行
    print("约束: 固定底座")

    # --- 2. 回转台与底座 ---
    if comp_map["turntable_inst"] and comp_map["base_inst"]:
        sw_assem.mate_axes(assem_name, comp_map["turntable_inst"], comp_map["base_inst"], "rotation_axis_z", "center_axis_z", True)
        sw_assem.mate_faces(assem_name, comp_map["turntable_inst"], comp_map["base_inst"], "bottom_contact_face", "top_mount_face", False)
        print("约束: 回转台 -> 底座 完成")

    # --- 3. 大臂与回转台 ---
    if comp_map["link_upper_arm"] and comp_map["turntable_inst"]:
        sw_assem.mate_axes(assem_name, comp_map["link_upper_arm"], comp_map["turntable_inst"], "start_axis_y", "joint_axis_y", True)
        sw_assem.mate_faces(assem_name, comp_map["link_upper_arm"], comp_map["turntable_inst"], "mid_plane_y", "mid_plane_y", True)
        print("约束: 大臂 -> 回转台 完成")

    # --- 4. 肩部销轴 ---
    if comp_map["pin_shoulder"] and comp_map["turntable_inst"]:
        sw_assem.mate_axes(assem_name, comp_map["pin_shoulder"], comp_map["turntable_inst"], "main_axis", "joint_axis_y", True)
        print("约束: 肩部销轴插入 完成")

    # --- 5. 肘关节叉与大臂 (参照规划建议模式) ---
    if comp_map["fork_elbow"] and comp_map["link_upper_arm"]:
        sw_assem.mate_axes(assem_name, comp_map["fork_elbow"], comp_map["link_upper_arm"], "hinge_axis_y", "end_axis_y", True)
        sw_assem.mate_faces(assem_name, comp_map["fork_elbow"], comp_map["link_upper_arm"], "mid_plane_y", "mid_plane_y", True)
        sw_assem.mate_axes(assem_name, comp_map["pin_elbow"], comp_map["fork_elbow"], "main_axis", "hinge_axis_y", True)
        print("约束: 肘关节叉 -> 大臂 完成")

    # --- 6. 小臂与肘关节叉 ---
    if comp_map["link_forearm"] and comp_map["fork_elbow"]:
        sw_assem.mate_axes(assem_name, comp_map["link_forearm"], comp_map["fork_elbow"], "start_axis_y", "hinge_axis_y", True)
        sw_assem.mate_faces(assem_name, comp_map["link_forearm"], comp_map["fork_elbow"], "mid_plane_y", "mid_plane_y", True)
        print("约束: 小臂 -> 肘关节叉 完成")

    # --- 7. 腕关节叉与小臂 ---
    if comp_map["fork_wrist"] and comp_map["link_forearm"]:
        sw_assem.mate_axes(assem_name, comp_map["fork_wrist"], comp_map["link_forearm"], "hinge_axis_y", "end_axis_y", True)
        sw_assem.mate_faces(assem_name, comp_map["fork_wrist"], comp_map["link_forearm"], "mid_plane_y", "mid_plane_y", True)
        sw_assem.mate_axes(assem_name, comp_map["pin_wrist"], comp_map["fork_wrist"], "main_axis", "hinge_axis_y", True)
        print("约束: 腕关节叉 -> 小臂 完成")

    # --- 8. 夹爪与腕关节叉 ---
    if comp_map["gripper_inst"] and comp_map["fork_wrist"]:
        sw_assem.mate_axes(assem_name, comp_map["gripper_inst"], comp_map["fork_wrist"], "mount_axis_y", "hinge_axis_y", True)
        sw_assem.mate_faces(assem_name, comp_map["gripper_inst"], comp_map["fork_wrist"], "mid_plane_y", "mid_plane_y", True)
        print("约束: 夹爪 -> 腕关节叉 完成")

    # 6. 保存装配体
    output_path = r"D:\a_src\python\sw_agent\agent_output\Four_Axis_Industrial_Robot_Arm-20260429_201900\assembly\Four_Axis_Industrial_Robot_Arm.SLDASM"
    print(f"正在保存装配体到: {output_path}")
    sw_assem.save_as(output_path)
    print("装配任务完成。")

if __name__ == "__main__":
    try:
        build_assembly()
    except Exception as e:
        print(f"装配过程中发生错误: {str(e)}")