import os
from pysw import SldWorksApp, PartDoc, AssemDoc


WORKDIR = r"\IndustrialSimpleAssembly"

BASE_FILE = os.path.join(WORKDIR, "BasePlate.SLDPRT")
TOP_FILE = os.path.join(WORKDIR, "TopPlate.SLDPRT")
POST_FILE = os.path.join(WORKDIR, "SupportPost.SLDPRT")
PIN_FILE = os.path.join(WORKDIR, "CenterPin.SLDPRT")
BOLT_FILE = os.path.join(WORKDIR, "BoltHead.SLDPRT")
ASSEMBLY_FILE = os.path.join(WORKDIR, "IndustrialSupportPlatform.SLDASM")


def ensure_dir():
    os.makedirs(WORKDIR, exist_ok=True)


def create_plate(app, part_name, file_path, length, width, thickness):
    """
    创建简单矩形板，并添加装配参考轴和平面。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

    sketch = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_centre_rectangle(
        center_x=0,
        center_y=0,
        width=length,
        height=width,
        sketch_ref="XY"
    )
    sw_doc.extrude(sketch, depth=thickness, single_direction=True, merge=True)

    # 中心参考轴
    sw_doc.create_axis(
        pt1=(0, 0, 0),
        pt2=(0, 0, thickness),
        axis_name="CenterAxis"
    )

    # 底面与顶面
    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", thickness, target_plane_name="TopPlane")

    # 四个支撑柱位置参考轴
    x = length / 2 - 0.018
    y = width / 2 - 0.018

    post_points = [
        (x, y),
        (-x, y),
        (-x, -y),
        (x, -y),
    ]

    for idx, (px, py) in enumerate(post_points, start=1):
        sw_doc.create_axis(
            pt1=(px, py, 0),
            pt2=(px, py, thickness),
            axis_name=f"PostAxis{idx}"
        )

    # 四个螺栓参考轴，略靠近支撑柱外侧
    bx = length / 2 - 0.010
    by = width / 2 - 0.010

    bolt_points = [
        (bx, by),
        (-bx, by),
        (-bx, -by),
        (bx, -by),
    ]

    for idx, (px, py) in enumerate(bolt_points, start=1):
        sw_doc.create_axis(
            pt1=(px, py, 0),
            pt2=(px, py, thickness),
            axis_name=f"BoltAxis{idx}"
        )

    # 简单面倒角，失败可跳过
    try:
        sw_doc.chamfer_faces(
            on_face_points=[(0, 0, thickness)],
            distance=0.001,
            angle=45.0
        )
    except Exception:
        print(f"{part_name}: 面倒角跳过")

    sw_doc.save_as(file_path)


def create_cylinder(app, part_name, file_path, radius, height):
    """
    创建简单圆柱，并添加中心轴和上下参考平面。
    """
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

    sketch = sw_doc.insert_sketch_on_plane("XY")
    sw_doc.create_circle(0, 0, radius, "XY")
    sw_doc.extrude(sketch, depth=height, single_direction=True, merge=True)

    sw_doc.create_axis(
        pt1=(0, 0, 0),
        pt2=(0, 0, height),
        axis_name="CenterAxis"
    )

    sw_doc.create_ref_plane("XY", 0, target_plane_name="BottomPlane")
    sw_doc.create_ref_plane("XY", height, target_plane_name="TopPlane")

    try:
        sw_doc.chamfer_faces(
            on_face_points=[(0, 0, height)],
            distance=0.0008,
            angle=45.0
        )
    except Exception:
        print(f"{part_name}: 面倒角跳过")

    sw_doc.save_as(file_path)


def create_parts():
    ensure_dir()
    app = SldWorksApp()

    # 下底板
    create_plate(
        app=app,
        part_name="BasePlate",
        file_path=BASE_FILE,
        length=0.120,
        width=0.080,
        thickness=0.008
    )

    # 上压板
    create_plate(
        app=app,
        part_name="TopPlate",
        file_path=TOP_FILE,
        length=0.100,
        width=0.060,
        thickness=0.006
    )

    # 四根支撑柱共用一个零件
    create_cylinder(
        app=app,
        part_name="SupportPost",
        file_path=POST_FILE,
        radius=0.006,
        height=0.045
    )

    # 中央定位短轴
    create_cylinder(
        app=app,
        part_name="CenterPin",
        file_path=PIN_FILE,
        radius=0.008,
        height=0.014
    )

    # 螺栓头
    create_cylinder(
        app=app,
        part_name="BoltHead",
        file_path=BOLT_FILE,
        radius=0.004,
        height=0.003
    )


def create_assembly():
    app = SldWorksApp()
    assem = AssemDoc(app.createAndActivate_sw_assembly("IndustrialSupportPlatform"))

    assem_name = "IndustrialSupportPlatform"

    # 添加下底板
    base = assem.add_component(BASE_FILE, 0, 0, 0)

    # 添加上压板，初始放在上方
    top = assem.add_component(TOP_FILE, 0, 0, 0.053)

    # 添加四根支撑柱
    post_positions = [
        (0.042, 0.022, 0.008),
        (-0.042, 0.022, 0.008),
        (-0.042, -0.022, 0.008),
        (0.042, -0.022, 0.008),
    ]

    posts = []
    for i, pos in enumerate(post_positions, start=1):
        comp = assem.add_component(POST_FILE, *pos)
        posts.append(comp)

    # 添加中央定位轴
    center_pin = assem.add_component(PIN_FILE, 0, 0, 0.008)

    # 添加四个螺栓头在上压板附近
    bolt_positions = [
        (0.042, 0.022, 0.059),
        (-0.042, 0.022, 0.059),
        (-0.042, -0.022, 0.059),
        (0.042, -0.022, 0.059),
    ]

    bolts = []
    for i, pos in enumerate(bolt_positions, start=1):
        comp = assem.add_component(BOLT_FILE, *pos)
        bolts.append(comp)

    # =========================
    # 装配配合
    # =========================

    # 中央轴对齐
    assem.mate_axes(
        assem_name=assem_name,
        comp1=base,
        comp2=top,
        axis_name1="CenterAxis",
        axis_name2="CenterAxis",
        aligned=True
    )

    # 上压板底面与支撑柱顶面配合
    for i, post in enumerate(posts, start=1):
        assem.mate_axes(
            assem_name=assem_name,
            comp1=base,
            comp2=post,
            axis_name1=f"PostAxis{i}",
            axis_name2="CenterAxis",
            aligned=True
        )

        assem.mate_faces(
            assem_name=assem_name,
            comp1=base,
            comp2=post,
            plane_name1="TopPlane",
            plane_name2="BottomPlane",
            aligned=True
        )

        assem.mate_faces(
            assem_name=assem_name,
            comp1=post,
            comp2=top,
            plane_name1="TopPlane",
            plane_name2="BottomPlane",
            aligned=True
        )

    # 中央定位轴装在底板中心
    assem.mate_axes(
        assem_name=assem_name,
        comp1=base,
        comp2=center_pin,
        axis_name1="CenterAxis",
        axis_name2="CenterAxis",
        aligned=True
    )

    assem.mate_faces(
        assem_name=assem_name,
        comp1=base,
        comp2=center_pin,
        plane_name1="TopPlane",
        plane_name2="BottomPlane",
        aligned=True
    )

    # 螺栓头装在上压板四角
    for i, bolt in enumerate(bolts, start=1):
        assem.mate_axes(
            assem_name=assem_name,
            comp1=top,
            comp2=bolt,
            axis_name1=f"PostAxis{i}",
            axis_name2="CenterAxis",
            aligned=True
        )

        assem.mate_faces(
            assem_name=assem_name,
            comp1=top,
            comp2=bolt,
            plane_name1="TopPlane",
            plane_name2="BottomPlane",
            aligned=True
        )

    assem.save_as(ASSEMBLY_FILE)


if __name__ == "__main__":
    create_parts()
    create_assembly()