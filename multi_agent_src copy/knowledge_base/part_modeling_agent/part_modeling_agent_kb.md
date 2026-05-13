# PartModelingAgent Knowledge Base

你会收到单个零件 JSON，有时还会收到完整装配规划摘要。你的任务是输出可执行 Python 建模代码。

## 1. 代码目标

你的代码必须：
- 使用当前 SolidWorks Python 封装
- 创建或激活零件文档
- 按要求建模
- 保存到输入 JSON 里的 `model_file` 对应目标位置，允许使用相对路径、路径变量或等价输出路径，只要最终落到固定工作区下的正确文件即可
- 最终保存 `.SLDPRT`
- 尽量暴露后续装配需要的接口名称

如果该零件被多个装配实例复用，你仍然只生成一次通用零件模型。实例差异属于装配阶段，不属于零件阶段重复建模。

## 2. 单位规则（非常重要）

底层封装在新建文档后会统一设置为 **米制**。
因此：
- 代码中所有建模尺寸都应使用 **m**
- 若输入尺寸是 mm，必须先换算
- 不要把 10 mm 直接当作 10 m 传入 API

## 3. 你可调用的主要能力

## 2. API 接口签名

```python
class SldWorksApp:
    def __init__(self): ...
    # 返回 PartDoc 对象用于后续操作
    def createAndActivate_sw_part(self, part_name: str) -> "PartDoc": ...
    def createAndActivate_sw_assembly(self, assem_name: str) -> "PartDoc": ...

class PartDoc:
    def __init__(self, sw_doc): ...

    # 创建偏移平面。plane可以是 "XY"/"XZ"/"ZY" 或已创建的平面名
    def create_workplane_p_d(self, plane: str, offset_val: float) -> object: ...
    
    # --- 2.2 草图 (必须先调用 insert_sketch_on_plane) ---
    # plane_name 仅限: "XY", "XZ", "ZY" 或自定义平面名
    def insert_sketch_on_plane(self, plane: str/object) -> object: ...
    
    # sketch_ref 必须与当前草图平面方向一致 ("XY"/"XZ"/"ZY")
    def create_centre_rectangle(self, center_x: float, center_y: float, width: float, height: float, sketch_ref: str): ...
    def create_circle(self, center_x: float, center_y: float, radius: float, sketch_ref: str): ...
    def create_3point_arc(self, start_x: float, start_y: float, end_x: float, end_y: float, mid_x: float, mid_y: float, sketch_ref: str): ...
    def create_lines(self, points: list[tuple[float, float]], sketch_ref: str): ... # points=[(x1,y1), (x2,y2)...]
    def create_sketch_fillet(self, sketch_points: list[tuple[float, float]], radius: float, sketch_ref: str): ...
    def create_sketch_chamfer(self, sketch_points: list[tuple[float, float]], distance: float, angle: float, sketch_ref: str): ...
    def create_ellipse(self, center_x: float, center_y: float, length: float, width: float, sketch_ref: str)->object:
    def create_construction_line(self, x1: float, y1: float, x2: float, y2: float, sketch_ref: str): ...
    def create_polygon(self, center_x: float, center_y: float, radius: float, sides: int, inscribed: bool, sketch_ref: str)->object:
        """
        在当前草图上创建多边形
        radius: 内接圆半径, inscribed=True表示内接圆, False表示外接圆
        返回值: 创建的多边形对象
        """

    # --- 2.3 特征 ---
    def extrude(self, sketch: object, depth: float, single_direction: bool=True, merge: bool=True)->object:
        """
        拉伸当前草图
        depth: 拉伸深度，为-则向坐标轴负方向拉伸
        single_direction: 是否单向拉伸,True为单向拉伸,False为双向拉伸，默认单向拉伸
        merge: 是否与先前实体合并，默认合并，如新实体需要和先前创建的实体分开或者新实体是用来做布尔减操作的，请设置为False
        返回值: 创建的拉伸特征对象
        """
    def extrude_cut(self, sketch: object, depth: float, single_direction: bool=True)->object:
        """
        按当前草图做拉伸切除
        depth: 需要特别注意正负，切除深度，正值为向平面法向量正方向切除，负值为向平面法向量负方向切除
        single_direction: 是否单向切除
        返回值: 创建的拉伸特征对象
        """
    def shell(self, on_face_points: list[tuple[float, float, float]], thickness: float, outward: bool=False) -> None:
        """
        对选择的面对应的实体进行壳化处理，选择的面为开口方向
        thickness: 壳化厚度
        outward: 是否向外壳化，默认向内壳化
        返回值: 创建的壳化特征对象
        示例：
        sketch1 = sw_part.insert_sketch_on_plane("XY")
        sw_part.create_centre_rectangle(center_x=0, center_y=0, width=0.06, height=0.04, sketch_ref="XY")
        sw_part.extrude(sketch1,depth=0.02, single_direction=True)
        sw_part.shell(on_face_points=[(0, 0, 0.02)], thickness=0.002, outward=False)
        """
    # 前置条件: 草图需包含封闭轮廓 + 构造线轴
    def revolve(self, sketch: object, angle: float, merge: bool=True) -> object: ...
        """
        对草图进行旋转拉伸, angle为旋转角度，单位为度
        merge: 是否与先前实体合并，默认合并，如新实体需要和先前创建的实体分开或者新实体是用来做布尔减操作的，请设置为False
        使用，首先在草图定义画需要旋转的闭合轮廓，随后用构造线定义旋转轴，然后直接调用该方法，示例：
            sketch1 = sw_part.insert_sketch_on_plane("ZY")
            sw_part.create_circle(center_x=0.03, center_y=0.01, radius=0.01, sketch_ref="ZY")
            sw_part.create_construction_line(x1=0, y1=0, x2=0, y2=0.03, sketch_ref="ZY")
            revolve1 = sw_part.revolve(sketch, angle=360)
        返回值: 创建的旋转拉伸特征对象
        """
    def revolve_cut(self, sketch: object, angle: float) -> object: ...
    def sweep(self, profile_sketch: object, path_sketch: object) -> object: ...
        """

        s_rode = sw_doc.insert_sketch_on_plane("ZY")
        sw_doc.create_lines([(0, 0), (0.02, 0), (0.02, 0.02)], "ZY")
        s_profile = sw_doc.insert_sketch_on_plane("XY")
        sw_doc.create_circle(0, 0, bar_diam/2, "XY")
        sw_doc.partDoc.SketchManager.InsertSketch(True)
        sw_doc.sweep(s_profile, s_path)
        """
    def fillet_edges(on_line_points: list[tuple[float, float,float]], radius: float) -> object:
        """
        对实体的边进行圆角处理 (Fillet)。
        
        参数:
        on_line_points: 边上任意点的坐标列表 [(x1, y1, z1), (x2, y2, z2), ...]，每个点用于定位需要圆角处理的边。
        radius: 圆角半径。
        使用:
        1. 确保实体已经创建并且边可见。
        2. 调用此方法，传入边上点的坐标列表和所需的圆角半径。
        返回值: 无返回值，直接在实体上应用圆角特征。
        """
    def fillet_faces(on_face_points: list[tuple[float, float,float]], radius: float) -> object:
        """
        对实体的面上的边进行圆角处理 (Fillet)。
        """
    def chamfer_edges(on_line_points: list[tuple[float, float,float]], distance: float, angle: float=45.0) -> object:
        """
        对实体的边进行倒角处理 (Chamfer)。
        参数:
        on_line_points: 边上任意点的坐标列表 [(x1, y1, z1), (x2, y2, z2), ...]，每个点用于定位需要倒角处理的边。
        distance: 倒角距离。
        angle: 倒角角度，默认为45度。
        返回值: 创建的倒角特征对象。
        """
    def chamfer_faces(on_face_points: list[tuple[float, float,float]], distance: float, angle: float=45.0) -> object:
        """
        对实体的面上的边进行倒角处理 (Chamfer)。
        """
    
    # 以下两个接口用于创建装配阶段需要的参考面和参考轴
    def create_ref_plane(self, plane: object, offset_val: float, target_plane_name: str = None) -> object:
        """
        基于plane基准面，创建平行偏移工作平面，plane可以为创建的平面变量，也可以是“XY”,“XZ”,“ZY”
        offset_val: 偏移距离，可以为负
        target_plane_name: 可选的工作平面名称，创建成功后会重命名该平面
        返回值: 创建的工作平面对象
        """

    def create_axis(self, pt1: tuple[float, float, float], pt2: tuple[float, float, float], axis_name: str = None) -> object:
        """
        创建一条从pt1到pt2的基准轴 (Reference Axis)，轴在装配中有方向区别，默认从pt1指向pt2。
        参数:
            pt1: 基准轴起点坐标 (x, y, z)
            pt2: 基准轴终点坐标 (x, y, z)
            axis_name: 可选的轴名称，创建成功后会重命名该轴
        """

    # 保存零件文件，装配体调用前必须保存
    def save_as(self, path: str)->bool:
        """
        保存零件到指定路径 (装配体调用前必须保存)
        """
        if self.partDoc is None: return False
        longstatus = self.partDoc.Extension.SaveAs3(
            path, constants.swSaveAsCurrentVersion, constants.swSaveAsOptions_Silent, arg_Nothing, arg_Nothing, arg_Long_error, arg_Long_warning
        )

        if longstatus == True: # 0 表示成功
            print(f"零件已保存至: {path}")
            return True
        else:
            print(f"保存失败，错误代码: {longstatus}")
            return False
## 3. 标准代码模板 (Few-Shot)

```python
from pysw import SldWorksApp, PartDoc

# 1. 启动与创建
app = SldWorksApp()
sw_doc = PartDoc(app.createAndActivate_sw_part("DemoPart"))

# 2. 建模
...

#
sw_doc.save_as("规定的路径/DemoPart.SLDPRT")
```

## 4. 草图与基准面的使用习惯

### 基准面表示
底层常用主基准面标记：
- `XY`
- `XZ`
- `ZY`

内部会映射到 SolidWorks 中文基准面名称。

### 坐标修正
不同草图面有坐标翻转处理：
- `ZY` 可能对 x 做反号处理
- `XZ` 可能对 y 做反号处理

因此你只需要按封装要求给 `sketch_ref`，不要自己重复做二次坐标系补偿。

## 5. 建模策略建议

优先采用以下稳定套路：
- 主体：中心矩形/圆/多边形草图 + 拉伸
- 回转体：剖面 + 构造线 + `revolve`
- 孔槽：在已有面对应平面建草图 + `extrude_cut`
- 对称结构：用中心草图和全尺寸参数减少歧义
- 装配接口：创建命名参考面 / 命名参考轴

## 6. 接口实现原则

如果零件 JSON 中要求接口，请优先这样实现：

如果完整装配规划中显示该零件对应多个 `instances`：
- 你要实现的是“可复用的统一零件模板”
- 接口应覆盖这些实例实际使用到的接口并保持命名稳定
- 不要为每个实例各写一份几何几乎相同的代码
- 只有当实例对应的几何特征本身不同，才说明装配规划拆件有误或需要重新拆分

### 面接口
优先方式：
- 通过创建命名参考面暴露接口

### 轴接口
优先方式：
- 使用 `create_axis(pt1, pt2, axis_name=...)`
- 轴方向要与规划中的 `direction_relation` 一致

### 点接口
没有成熟的“命名点”封装。
如果需要点位语义，可：
- 用变量保留关键点坐标
- 用这些点创建参考轴
- 在日志里标注点位用途

## 7. 关键前置条件（你必须自己满足）

### `revolve` / `revolve_cut`
必须确保：
- 草图中有闭合轮廓（切除也需合理闭合）
- 草图中有一条构造线作为旋转轴

### `sweep`
必须确保：
- 有轮廓草图和路径草图
- 轮廓与路径起点关系合理
- 路径连续，轮廓不过度异常

### `shell`
必须提供：
- 可用于选择开口面的面上点坐标

### `fillet` / `chamfer`
通常需要：
- 边上点坐标或面上点坐标足够准确
- 半径/倒角不要大到产生几何干涉

## 8. 代码风格要求

你必须只输出 Python 代码块。

推荐代码结构：
1. 导入封装
2. 解析输入参数/路径
3. 创建应用和零件文档
4. 分步骤建模，关键步骤 `print` 日志
5. 创建参考面/参考轴接口
6. 保存到指定路径
7. 对失败点进行基本判空或异常处理

## 9. 你应避免的错误

- 忘记保存到输入指定路径或等价目标位置
- 混淆 mm 与 m
- 在需要旋转轴时没画构造线
- 依赖未确认存在的高级能力
- 输出伪代码而不是可执行代码
- 不体现接口名称，导致后续装配无法引用

## 10. 你的目标

你的代码不只是“画出形状”，而是要产出：
- 可保存
- 可复现
- 可重试
- 可被装配阶段继续引用接口的零件模型

在存在重复件时，还要满足：
- 一个零件模板可被多次插入装配
- 同一模型能支撑不同实例通过不同接口完成装配
