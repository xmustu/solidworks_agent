import os
from pysw import SldWorksApp, PartDoc, AssemDoc


WORKDIR = r"\Industrial_4Axis_Arm"

BASE_FILE = os.path.join(WORKDIR, "BasePlate.SLDPRT")
TURNTABLE_FILE = os.path.join(WORKDIR, "YawTurntable.SLDPRT")
JOINT_FORK_FILE = os.path.join(WORKDIR, "JointFork.SLDPRT")
LINK_FILE = os.path.join(WORKDIR, "HollowLink.SLDPRT")
PIN_FILE = os.path.join(WORKDIR, "HingePin.SLDPRT")

GRIPPER_RAIL_FILE = os.path.join(WORKDIR, "GripperRail.SLDPRT")
JAW_LEFT_FILE = os.path.join(WORKDIR, "SlidingJaw_Left.SLDPRT")
JAW_RIGHT_FILE = os.path.join(WORKDIR, "SlidingJaw_Right.SLDPRT")

GRIPPER_ASM_FILE = os.path.join(WORKDIR, "SlidingGripper.SLDASM")
ROBOT_ASM_FILE = os.path.join(WORKDIR, "Industrial_4Axis_RobotArm.SLDASM")


# -----------------------------
# 全局尺寸参数
# -----------------------------

BASE_R = 0.060
BASE_H = 0.010

TURNTABLE_R = 0.035
TURNTABLE_H = 0.014

FORK_BASE_L = 0.050
FORK_BASE_W = 0.050
FORK_BASE_H = 0.010
FORK_EAR_THK = 0.006
FORK_EAR_GAP = 0.026
FORK_EAR_H = 0.040
FORK_EAR_L = 0.020
FORK_AXIS_Z = 0.036
FORK_TOTAL_H = 0.052

LINK_LEN = 0.095
LINK_THK = 0.014
LINK_H = 0.020
LINK_BOSS_R = 0.016
LINK_HOLE_R = 0.0065

PIN_R = 0.0048
PIN_LEN = 0.044

GRIPPER_BASE_L = 0.060
GRIPPER_BASE_W = 0.075
GRIPPER_BASE_H = 0.006
GRIPPER_RAIL_H = 0.006
GRIPPER_SLIDE_Z = GRIPPER_BASE_H + GRIPPER_RAIL_H / 2


def ensure_dir():
    os.makedirs(WORKDIR, exist_ok=True)


def safe_face_chamfer(sw_doc, points, distance=0.001, angle=45.0, label=""):
    try:
        sw_doc.chamfer_faces(
            on_face_points=points,
            distance=distance,
            angle=angle
        )
    except Exception:
        print(f"{label} 面倒角跳过")


def safe_face_fillet(sw_doc, points, radius=0.001, label=""):
    try:
        sw_doc.fillet_faces(
            on_face_points=points,
            radius=radius
        )
    except Exception:
        print(f"{label} 面圆角跳过")


# =========================================================
# 1. 零件建模
# =========================================================

def create_base_plate(app):
    """
    工业圆形底座。
    提供竖直 CenterAxis，用于第 1 轴水平回转。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part("BasePlate"))

    s = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(0, 0, BASE_R, "XY")
    sw_doc.extrude(s, depth=BASE_H, single_direction=True, merge=True)

    # 中心安装孔
    s_cut = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(0, 0, 0.010, "XY")
    sw_doc.extrude_cut(s_cut, depth=BASE_H + 0.002, single_direction=True)

    # 四个安装孔
    bolt_r = 0.045
    for x, y in [
        (bolt_r, bolt_r),
        (-bolt_r, bolt_r),
        (-bolt_r, -bolt_r),
        (bolt_r, -bolt_r),
    ]:
        s_hole = sw_doc.insert_sketch_on_plane("XY")
        sw_doc.create_circle(x, y, 0.004, "XY")
        sw_doc.extrude_cut(s_hole, depth=BASE_H + 0.002, single_direction=True)

    sw_doc.create_axis(
        pt1=(0, 0, 0),
        pt2=(0, 0, BASE_H),
        axis_name="CenterAxis"
    )
    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", BASE_H, target_plane_name="TopPlane")

    safe_face_chamfer(
        sw_doc,
        points=[(0, 0, BASE_H), (BASE_R * 0.8, 0, BASE_H)],
        distance=0.0012,
        label="BasePlate"
    )

    sw_doc.save_as(BASE_FILE)


def create_yaw_turntable(app):
    """
    第一轴回转台。
    下方与底座同轴，上方承载肩关节叉。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part("YawTurntable"))

    s = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(0, 0, TURNTABLE_R, "XY")
    sw_doc.extrude(s, depth=TURNTABLE_H, single_direction=True, merge=True)

    # 中央凸台
    p_top = sw_doc.create_workplane_p_d("XY", TURNTABLE_H)
    s_boss = sw_doc.insert_sketch_on_plane(p_top)
    sw_doc.create_circle(0, 0, 0.018, "XY")
    sw_doc.extrude(s_boss, depth=0.010, single_direction=True, merge=True)

    # 顶部浅孔，表示轴承或定位孔
    p_boss_top = sw_doc.create_workplane_p_d("XY", TURNTABLE_H + 0.010)
    s_socket = sw_doc.insert_sketch_on_plane(p_boss_top)
    sw_doc.create_circle(0, 0, 0.009, "XY")
    sw_doc.extrude_cut(s_socket, depth=-0.006, single_direction=True)

    sw_doc.create_axis(
        pt1=(0, 0, 0),
        pt2=(0, 0, TURNTABLE_H + 0.010),
        axis_name="CenterAxis"
    )
    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", TURNTABLE_H + 0.010, target_plane_name="TopPlane")

    safe_face_chamfer(
        sw_doc,
        points=[(0, 0, TURNTABLE_H + 0.010), (TURNTABLE_R * 0.8, 0, TURNTABLE_H)],
        distance=0.001,
        label="YawTurntable"
    )

    sw_doc.save_as(TURNTABLE_FILE)


def create_joint_fork(app):
    """
    通用工业关节叉。
    肩、肘、腕三个关节都复用该零件。
    关节轴 HingeAxis 沿 Y 方向。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part("JointFork"))

    # 底部安装座
    s_base = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=FORK_BASE_L,
        height=FORK_BASE_W,
        sketch_ref="XY"
    )
    sw_doc.extrude(s_base, depth=FORK_BASE_H, single_direction=True, merge=True)

    # 中央加强台
    p_base_top = sw_doc.create_workplane_p_d("XY", FORK_BASE_H)
    s_ped = sw_doc.insert_sketch_on_plane(p_base_top)
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=0.030,
        height=0.034,
        sketch_ref="XY"
    )
    sw_doc.extrude(s_ped, depth=0.014, single_direction=True, merge=True)

    # 两侧耳板，沿 XZ 平面拉伸
    y_left = -FORK_EAR_GAP / 2 - FORK_EAR_THK
    y_right = FORK_EAR_GAP / 2

    p_left = sw_doc.create_workplane_p_d("XZ", y_left)
    s_left = sw_doc.insert_sketch_on_plane(p_left)
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=FORK_AXIS_Z,
        width=FORK_EAR_L,
        height=FORK_EAR_H,
        sketch_ref="XZ"
    )
    sw_doc.extrude(s_left, depth=FORK_EAR_THK, single_direction=True, merge=True)

    p_right = sw_doc.create_workplane_p_d("XZ", y_right)
    s_right = sw_doc.insert_sketch_on_plane(p_right)
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=FORK_AXIS_Z,
        width=FORK_EAR_L,
        height=FORK_EAR_H,
        sketch_ref="XZ"
    )
    sw_doc.extrude(s_right, depth=FORK_EAR_THK, single_direction=True, merge=True)

    # 两侧铰链孔，给销轴和臂段留空间
    s_hole_l = sw_doc.insert_sketch_on_plane(p_left)
    sw_doc.create_circle(0, FORK_AXIS_Z, 0.007, "XZ")
    sw_doc.extrude_cut(s_hole_l, depth=FORK_EAR_THK + 0.002, single_direction=True)

    s_hole_r = sw_doc.insert_sketch_on_plane(p_right)
    sw_doc.create_circle(0, FORK_AXIS_Z, 0.007, "XZ")
    sw_doc.extrude_cut(s_hole_r, depth=FORK_EAR_THK + 0.002, single_direction=True)

    # 减重窗口，耳板上部切除一个小孔，避免像纯方块
    for plane_obj in [p_left, p_right]:
        s_light = sw_doc.insert_sketch_on_plane(plane_obj)
        sw_doc.create_centre_rectangle(
            center_x=0,
            center_y=FORK_AXIS_Z + 0.010,
            width=0.010,
            height=0.012,
            sketch_ref="XZ"
        )
        sw_doc.extrude_cut(s_light, depth=FORK_EAR_THK + 0.002, single_direction=True)

    # 参考轴与参考面
    sw_doc.create_axis(
        pt1=(0, -0.030, FORK_AXIS_Z),
        pt2=(0, 0.030, FORK_AXIS_Z),
        axis_name="HingeAxis"
    )
    sw_doc.create_axis(
        pt1=(0, 0, 0),
        pt2=(0, 0, FORK_TOTAL_H),
        axis_name="CenterAxis"
    )

    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", FORK_TOTAL_H, target_plane_name="TopPlane")
    sw_doc.create_ref_plane("XZ", 0, target_plane_name="MidPlane")

    safe_face_chamfer(
        sw_doc,
        points=[
            (0, 0, FORK_BASE_H),
            (0, y_left, FORK_AXIS_Z + 0.015),
            (0, y_right, FORK_AXIS_Z + 0.015),
        ],
        distance=0.0008,
        label="JointFork"
    )

    sw_doc.save_as(JOINT_FORK_FILE)


def create_hollow_link(app):
    """
    通用中空机械臂段。
    上臂和前臂复用该零件。
    形态：两端圆形轴承座 + 中间矩形连杆 + 大镂空减重窗口。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part("HollowLink"))

    y_start = -LINK_THK / 2
    p_mid = sw_doc.create_workplane_p_d("XZ", y_start)

    # 中间梁
    s_body = sw_doc.insert_sketch_on_plane(p_mid)
    sw_doc.create_centre_rectangle(
        center_x=LINK_LEN / 2,
        center_y=0,
        width=LINK_LEN,
        height=LINK_H,
        sketch_ref="XZ"
    )
    sw_doc.extrude(s_body, depth=LINK_THK, single_direction=True, merge=True)

    # 两端轴承座
    for x in [0, LINK_LEN]:
        s_boss = sw_doc.insert_sketch_on_plane(p_mid)
        sw_doc.create_circle(x, 0, LINK_BOSS_R, "XZ")
        sw_doc.extrude(s_boss, depth=LINK_THK, single_direction=True, merge=True)

    # 中央减重窗口
    s_window = sw_doc.insert_sketch_on_plane(p_mid)
    sw_doc.create_centre_rectangle(
        center_x=LINK_LEN / 2,
        center_y=0,
        width=LINK_LEN * 0.52,
        height=LINK_H * 0.42,
        sketch_ref="XZ"
    )
    sw_doc.extrude_cut(s_window, depth=LINK_THK * 2, single_direction=True)

    # 两端铰链孔
    for x in [0, LINK_LEN]:
        s_hole = sw_doc.insert_sketch_on_plane(p_mid)
        sw_doc.create_circle(x, 0, LINK_HOLE_R, "XZ")
        sw_doc.extrude_cut(s_hole, depth=LINK_THK * 2, single_direction=True)

    # 小型减重孔
    for x in [LINK_LEN * 0.28, LINK_LEN * 0.72]:
        s_light = sw_doc.insert_sketch_on_plane(p_mid)
        sw_doc.create_circle(x, 0, 0.004, "XZ")
        sw_doc.extrude_cut(s_light, depth=LINK_THK * 2, single_direction=True)

    # 参考轴：两端关节轴，均沿 Y 方向
    sw_doc.create_axis(
        pt1=(0, -LINK_THK / 2, 0),
        pt2=(0, LINK_THK / 2, 0),
        axis_name="StartAxis"
    )
    sw_doc.create_axis(
        pt1=(LINK_LEN, -LINK_THK / 2, 0),
        pt2=(LINK_LEN, LINK_THK / 2, 0),
        axis_name="EndAxis"
    )

    sw_doc.create_ref_plane("XZ", 0, target_plane_name="MidPlane")
    sw_doc.create_ref_plane("ZY", 0, target_plane_name="StartPlane")
    sw_doc.create_ref_plane("ZY", LINK_LEN, target_plane_name="EndPlane")

    safe_face_chamfer(
        sw_doc,
        points=[
            (LINK_LEN / 2, 0, LINK_H / 2),
            (0, 0, LINK_BOSS_R),
            (LINK_LEN, 0, LINK_BOSS_R),
        ],
        distance=0.0008,
        label="HollowLink"
    )

    safe_face_fillet(
        sw_doc,
        points=[
            (0, 0, LINK_BOSS_R * 0.6),
            (LINK_LEN, 0, LINK_BOSS_R * 0.6),
        ],
        radius=0.0008,
        label="HollowLink"
    )

    sw_doc.save_as(LINK_FILE)


def create_hinge_pin(app):
    """
    通用铰链销轴。
    可用于视觉上填充关节位置。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part("HingePin"))

    p = sw_doc.create_workplane_p_d("XZ", -PIN_LEN / 2)
    s = sw_doc.insert_sketch_on_plane(p)
    sw_doc.create_circle(0, 0, PIN_R, "XZ")
    sw_doc.extrude(s, depth=PIN_LEN, single_direction=True, merge=True)

    sw_doc.create_axis(
        pt1=(0, -PIN_LEN / 2, 0),
        pt2=(0, PIN_LEN / 2, 0),
        axis_name="PinAxis"
    )
    sw_doc.create_ref_plane("XZ", 0, target_plane_name="MidPlane")

    safe_face_chamfer(
        sw_doc,
        points=[(0, PIN_LEN / 2, 0), (0, -PIN_LEN / 2, 0)],
        distance=0.0005,
        label="HingePin"
    )

    sw_doc.save_as(PIN_FILE)


def create_gripper_rail(app):
    """
    夹爪滑轨座。
    包含两条凸起滑轨、中心让位槽，以及腕部安装轴。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part("GripperRail"))

    # 基板
    s_base = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=GRIPPER_BASE_L,
        height=GRIPPER_BASE_W,
        sketch_ref="XY"
    )
    sw_doc.extrude(s_base, depth=GRIPPER_BASE_H, single_direction=True, merge=True)

    # 中央让位槽
    s_slot = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=0.020,
        height=0.050,
        sketch_ref="XY"
    )
    sw_doc.extrude_cut(s_slot, depth=GRIPPER_BASE_H + 0.002, single_direction=True)

    # 两条滑轨
    p_top = sw_doc.create_workplane_p_d("XY", GRIPPER_BASE_H)
    for x in [-0.015, 0.015]:
        s_rail = sw_doc.insert_sketch_on_plane(p_top)
        sw_doc.create_centre_rectangle(
            center_x=x,
            center_y=0,
            width=0.006,
            height=0.060,
            sketch_ref="XY"
        )
        sw_doc.extrude(s_rail, depth=GRIPPER_RAIL_H, single_direction=True, merge=True)

    # 滑动轴：沿 Y 方向，两个夹爪共用，保留滑动自由度
    sw_doc.create_axis(
        pt1=(0, -0.035, GRIPPER_SLIDE_Z),
        pt2=(0, 0.035, GRIPPER_SLIDE_Z),
        axis_name="SlideAxis"
    )

    # 腕部安装轴：沿 Y 方向，和腕关节叉配合
    sw_doc.create_axis(
        pt1=(-0.034, -0.035, GRIPPER_SLIDE_Z),
        pt2=(-0.034, 0.035, GRIPPER_SLIDE_Z),
        axis_name="WristMountAxis"
    )

    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", GRIPPER_BASE_H + GRIPPER_RAIL_H, target_plane_name="TopPlane")
    sw_doc.create_ref_plane("XZ", 0, target_plane_name="MidPlane")

    safe_face_chamfer(
        sw_doc,
        points=[(0, 0, GRIPPER_BASE_H + GRIPPER_RAIL_H)],
        distance=0.0006,
        label="GripperRail"
    )

    sw_doc.save_as(GRIPPER_RAIL_FILE)


def create_sliding_jaw(app, part_name, file_path, direction):
    """
    滑动夹爪。
    direction = 1 表示夹指朝 +Y；
    direction = -1 表示夹指朝 -Y。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

    # 滑块本体
    s_carriage = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=0.026,
        height=0.018,
        sketch_ref="XY"
    )
    sw_doc.extrude(s_carriage, depth=0.010, single_direction=True, merge=True)

    # 向内伸出的夹持指
    p_top = sw_doc.create_workplane_p_d("XY", 0.010)
    s_finger = sw_doc.insert_sketch_on_plane(p_top)
    sw_doc.create_centre_rectangle(
        center_x=0.008,
        center_y=direction * 0.014,
        width=0.012,
        height=0.026,
        sketch_ref="XY"
    )
    sw_doc.extrude(s_finger, depth=0.018, single_direction=True, merge=True)

    # 夹持端小凹槽，增加真实感
    p_finger_top = sw_doc.create_workplane_p_d("XY", 0.028)
    s_notch = sw_doc.insert_sketch_on_plane(p_finger_top)
    sw_doc.create_centre_rectangle(
        center_x=0.008,
        center_y=direction * 0.026,
        width=0.007,
        height=0.004,
        sketch_ref="XY"
    )
    sw_doc.extrude_cut(s_notch, depth=-0.006, single_direction=True)

    # 滑动参考轴，沿 Y 方向
    sw_doc.create_axis(
        pt1=(0, -0.030, GRIPPER_SLIDE_Z),
        pt2=(0, 0.030, GRIPPER_SLIDE_Z),
        axis_name="SlideAxis"
    )

    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", 0.028, target_plane_name="TopPlane")
    sw_doc.create_ref_plane("XZ", 0, target_plane_name="MidPlane")

    safe_face_chamfer(
        sw_doc,
        points=[(0, 0, 0.010), (0.008, direction * 0.020, 0.028)],
        distance=0.0005,
        label=part_name
    )

    sw_doc.save_as(file_path)


def create_all_parts():
    ensure_dir()
    app = SldWorksApp()

    create_base_plate(app)
    create_yaw_turntable(app)
    create_joint_fork(app)
    create_hollow_link(app)
    create_hinge_pin(app)
    create_gripper_rail(app)
    create_sliding_jaw(app, "SlidingJaw_Left", JAW_LEFT_FILE, direction=-1)
    create_sliding_jaw(app, "SlidingJaw_Right", JAW_RIGHT_FILE, direction=1)


# =========================================================
# 2. 夹爪子装配体
# =========================================================

def create_gripper_assembly():
    """
    单独生成夹爪装配体。
    滑块只约束在滑轨轴线上，并贴合底面，理论上保留沿 Y 方向的滑动自由度。
    """
    app = SldWorksApp()
    assem = AssemDoc(app.createAndActivate_sw_assembly("SlidingGripper"))

    assem_name = "SlidingGripper"

    rail = assem.add_component(GRIPPER_RAIL_FILE, 0, 0, 0)
    jaw_l = assem.add_component(JAW_LEFT_FILE, 0, -0.020, GRIPPER_BASE_H + GRIPPER_RAIL_H)
    jaw_r = assem.add_component(JAW_RIGHT_FILE, 0, 0.020, GRIPPER_BASE_H + GRIPPER_RAIL_H)

    for jaw in [jaw_l, jaw_r]:
        assem.mate_axes(
            assem_name=assem_name,
            comp1=rail,
            comp2=jaw,
            axis_name1="SlideAxis",
            axis_name2="SlideAxis",
            aligned=True
        )

        assem.mate_faces(
            assem_name=assem_name,
            comp1=rail,
            comp2=jaw,
            plane_name1="TopPlane",
            plane_name2="BottomPlane",
            aligned=True
        )

    assem.save_as(GRIPPER_ASM_FILE)


# =========================================================
# 3. 主机械臂装配体
# =========================================================

def create_robot_assembly():
    """
    四轴工业机械臂总装。
    由于当前 add_component 主要面向零件，这里把夹爪零件直接展开加入主装配；
    同时也会单独保存 SlidingGripper.SLDASM。
    """
    app = SldWorksApp()
    assem = AssemDoc(app.createAndActivate_sw_assembly("Industrial_4Axis_RobotArm"))

    assem_name = "Industrial_4Axis_RobotArm"

    # -----------------------------
    # 添加核心组件
    # -----------------------------

    base = assem.add_component(BASE_FILE, 0, 0, 0)
    turntable = assem.add_component(TURNTABLE_FILE, 0, 0, BASE_H)

    shoulder = assem.add_component(
        JOINT_FORK_FILE,
        0,
        0,
        BASE_H + TURNTABLE_H + 0.010
    )

    link1 = assem.add_component(
        LINK_FILE,
        0,
        0,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z
    )

    elbow = assem.add_component(
        JOINT_FORK_FILE,
        LINK_LEN,
        0,
        BASE_H + TURNTABLE_H + 0.010
    )

    link2 = assem.add_component(
        LINK_FILE,
        LINK_LEN,
        0,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z
    )

    wrist = assem.add_component(
        JOINT_FORK_FILE,
        LINK_LEN * 2,
        0,
        BASE_H + TURNTABLE_H + 0.010
    )

    gripper_rail = assem.add_component(
        GRIPPER_RAIL_FILE,
        LINK_LEN * 2 + 0.034,
        0,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z - GRIPPER_SLIDE_Z
    )

    jaw_l = assem.add_component(
        JAW_LEFT_FILE,
        LINK_LEN * 2 + 0.034,
        -0.020,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z + GRIPPER_RAIL_H
    )

    jaw_r = assem.add_component(
        JAW_RIGHT_FILE,
        LINK_LEN * 2 + 0.034,
        0.020,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z + GRIPPER_RAIL_H
    )

    # 关节销轴，主要用于视觉填充
    pin_shoulder = assem.add_component(
        PIN_FILE,
        0,
        0,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z
    )
    pin_elbow = assem.add_component(
        PIN_FILE,
        LINK_LEN,
        0,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z
    )
    pin_wrist = assem.add_component(
        PIN_FILE,
        LINK_LEN * 2,
        0,
        BASE_H + TURNTABLE_H + 0.010 + FORK_AXIS_Z
    )

    # -----------------------------
    # 第 1 轴：底座水平回转
    # -----------------------------

    assem.mate_axes(
        assem_name=assem_name,
        comp1=base,
        comp2=turntable,
        axis_name1="CenterAxis",
        axis_name2="CenterAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=base,
        comp2=turntable,
        plane_name1="TopPlane",
        plane_name2="BottomPlane",
        aligned=True
    )

    # 肩关节叉固定在回转台上
    assem.mate_axes(
        assem_name=assem_name,
        comp1=turntable,
        comp2=shoulder,
        axis_name1="CenterAxis",
        axis_name2="CenterAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=turntable,
        comp2=shoulder,
        plane_name1="TopPlane",
        plane_name2="BottomPlane",
        aligned=True
    )

    # -----------------------------
    # 第 2 轴：肩关节
    # -----------------------------

    assem.mate_axes(
        assem_name=assem_name,
        comp1=shoulder,
        comp2=link1,
        axis_name1="HingeAxis",
        axis_name2="StartAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=shoulder,
        comp2=link1,
        plane_name1="MidPlane",
        plane_name2="MidPlane",
        aligned=True
    )

    assem.mate_axes(
        assem_name=assem_name,
        comp1=shoulder,
        comp2=pin_shoulder,
        axis_name1="HingeAxis",
        axis_name2="PinAxis",
        aligned=True
    )

    # -----------------------------
    # 第 3 轴：肘关节
    # -----------------------------

    assem.mate_axes(
        assem_name=assem_name,
        comp1=link1,
        comp2=elbow,
        axis_name1="EndAxis",
        axis_name2="HingeAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=link1,
        comp2=elbow,
        plane_name1="MidPlane",
        plane_name2="MidPlane",
        aligned=True
    )

    assem.mate_axes(
        assem_name=assem_name,
        comp1=elbow,
        comp2=link2,
        axis_name1="HingeAxis",
        axis_name2="StartAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=elbow,
        comp2=link2,
        plane_name1="MidPlane",
        plane_name2="MidPlane",
        aligned=True
    )

    assem.mate_axes(
        assem_name=assem_name,
        comp1=elbow,
        comp2=pin_elbow,
        axis_name1="HingeAxis",
        axis_name2="PinAxis",
        aligned=True
    )

    # -----------------------------
    # 第 4 轴：腕关节
    # -----------------------------

    assem.mate_axes(
        assem_name=assem_name,
        comp1=link2,
        comp2=wrist,
        axis_name1="EndAxis",
        axis_name2="HingeAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=link2,
        comp2=wrist,
        plane_name1="MidPlane",
        plane_name2="MidPlane",
        aligned=True
    )

    assem.mate_axes(
        assem_name=assem_name,
        comp1=wrist,
        comp2=gripper_rail,
        axis_name1="HingeAxis",
        axis_name2="WristMountAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=wrist,
        comp2=gripper_rail,
        plane_name1="MidPlane",
        plane_name2="MidPlane",
        aligned=True
    )

    assem.mate_axes(
        assem_name=assem_name,
        comp1=wrist,
        comp2=pin_wrist,
        axis_name1="HingeAxis",
        axis_name2="PinAxis",
        aligned=True
    )

    # -----------------------------
    # 夹爪滑轨装配
    # -----------------------------

    for jaw in [jaw_l, jaw_r]:
        assem.mate_axes(
            assem_name=assem_name,
            comp1=gripper_rail,
            comp2=jaw,
            axis_name1="SlideAxis",
            axis_name2="SlideAxis",
            aligned=True
        )

        assem.mate_faces(
            assem_name=assem_name,
            comp1=gripper_rail,
            comp2=jaw,
            plane_name1="TopPlane",
            plane_name2="BottomPlane",
            aligned=True
        )

    assem.save_as(ROBOT_ASM_FILE)


# =========================================================
# 4. 主入口
# =========================================================

if __name__ == "__main__":
    create_all_parts()
    create_gripper_assembly()
    create_robot_assembly()