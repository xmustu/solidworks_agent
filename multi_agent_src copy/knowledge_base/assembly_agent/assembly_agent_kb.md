# AssemblyAgent Knowledge Base

你会收到完整装配规划 JSON，以及已经成功生成的零件输出路径。你的任务是输出可执行 Python 装配代码。

## 1. 你的目标

你的代码必须：
- 创建或激活装配文档
- 插入各零件文件
- 按规划中的顺序和关系完成装配
- 保存到指定装配输出路径
- 打印关键步骤日志，便于失败时定位

## 2. 当前装配层真实支持的核心能力

### 应用/装配文档
- `SldWorksApp()`
- `createAndActivate_sw_assembly(assem_name)`
- `get_assembly_path(workdir, assem_name)`

### 插入零件
- `add_component(file_path, x, y, z)`

### 配合
- `mate_faces(assem_name, comp1, comp2, plane_name1, plane_name2, aligned=True)`
- `mate_axes(assem_name, comp1, comp2, axis_name1, axis_name2, aligned=True)`

### 保存
- `save_as(path)`

## 3. 你必须依赖的接口类型

当前最可靠的装配对象引用方式是：
- 组件名 `comp_name`
- 组件内部的命名参考面
- 组件内部的命名参考轴

因此你必须严格使用规划中已经定义好的接口名称。

不要假设可以临时通过几何识别自动找到正确面/轴。

## 4. 装配实现策略

推荐标准流程：
1. 创建装配文档
2. 先建立 `part_id -> model_file` 映射，再按 `assembly.instances` / `assembly_sequence` 插入所有实例
3. 记录每个实例插入后返回的 `comp_name`
4. 以基准件为起点（通常是 `GROUND` 对应零件）
5. 按约束逐条施加平面配合 / 轴配合
6. 保存装配

### 重复零件的复用规则

如果多个实例引用同一个 `part_id`：
- 必须复用同一个零件文件路径
- 通过多次 `add_component(...)` 插入得到多个组件实例
- 用 `instance_id -> comp_name` 区分这些实例

不要错误地假设：
- 每个实例都对应一个独立 `.SLDPRT`
- 约束里只出现 `part_id` 就足够区分重复件

## 5. 基准件处理原则

装配规划里若有基准件：
- 先插入该零件
- 视作固定参考
- 其它零件相对它配合

如果约束里出现 `GROUND`：
- 说明该接口是相对装配全局基准或首个固定件建立关系
- 代码中应优先通过首个基准件承接这些关系，或按你的装配框架显式固定该基准件

## 6. 约束落地规则

### 平面关系
当规划要求某两个面重合时：
- 使用 `mate_faces(...)`
- 必须传入正确的装配体名、组件名、面名
- `plane_name1` / `plane_name2` 必须与零件内部接口名称一致

### 轴关系
当规划要求同心时：
- 使用 `mate_axes(...)`
- 传入正确轴名称
- `aligned` 要尽量匹配规划的方向要求

当存在重复件时，约束解析应遵循：
- 先根据 `source_instance_id` / `target_instance_id` 找到组件实例
- 再根据 `source_interface` / `target_interface` 找到接口名称
- `source_part_id` / `target_part_id` 只作为校验和辅助信息

## 7. 你要特别警惕的点

### 组件名不是零件名
`add_component(...)` 返回的是装配中的组件名称。
后续配合应使用：
- 返回的组件名
而不是原始文件名或零件名字符串。

### 接口名必须严格一致
如果规划里是 `main_axis_z`，代码就不能擅自换成 `axis_main`。

### 路径必须来自输入
你必须使用传入的零件文件路径和装配输出路径。
允许在固定工作区内通过相对路径、路径变量或路径拼接来组织保存路径，但不要把文件保存到无关目录。

### 日志要简洁但关键
建议至少打印：
- 装配开始
- 每个零件导入成功/失败
- 每条约束执行情况
- 最终保存路径

## 8. 代码风格建议

你必须只输出 Python 代码块。

推荐结构：
1. 导入封装
2. 读取装配规划、实例列表和路径
3. 创建装配文档
4. 插入零件并缓存 `part_id -> model_file`、`instance_id -> comp_name`
5. 按 sequence/constraints 执行配合
6. 保存装配
7. 对关键失败点做判空/异常处理

## 9. 当前系统限制（不要越界）

当前最稳定的装配能力主要是：
- 插入组件
- 平面配合
- 轴配合

不要假设系统稳定支持：
- 高级运动副
- 限位配合
- 齿轮/螺旋/路径等高级配合
- 自动求解复杂过约束问题

## 10. 你的成功标准

一段好的装配代码应做到：
- 所有零件都从给定路径成功导入
- 对重复零件正确复用同一个模型文件并生成多个实例
- 所有关键接口都按规划完成引用
- 关键配合顺序清楚
- 能保存到目标 `.SLDASM`
- 失败时日志足够定位是哪一步出问题


一个RV减速器装配案例：

from pysw import SldWorksApp, PartDoc, AssemDoc
import os


sw_app = SldWorksApp()
# ---------- 装配体演示 ----------
assem_name = "gears"
sw_assem = AssemDoc(sw_app.createAndActivate_sw_assembly(assem_name))
native_assem = sw_assem.assemDoc
# 下方填入该装配体的工作目录
base_path = r"D:\a_src\python\sw_agent\agent_output\assname"
carrier_path = os.path.join(base_path, "行星齿架.SLDPRT")
planet_path  = os.path.join(base_path, "行星齿轮35×0.5.SLDPRT")
flangle_path = os.path.join(base_path, "摆线01法兰.SLDPRT")
pin_path = os.path.join(base_path, "摆线01销.SLDPRT")
Sun_path = os.path.join(base_path, "太阳齿轮13×0.5.SLDPRT")
Cycloidal_path = os.path.join(base_path, "摆线01叶.SLDPRT")
carrier = sw_assem.add_component(carrier_path, 0, 0, 0)
planet1 = sw_assem.add_component(planet_path, 0.05, 0, 0)
planet2 = sw_assem.add_component(planet_path, 0, 0.05, 0)
planet3 = sw_assem.add_component(planet_path, -0.05, 0, 0)
sun = sw_assem.add_component(Sun_path, 0, 0, 0)
flange = sw_assem.add_component(flangle_path, 0, 0, 0.05)
pin = sw_assem.add_component(pin_path, 0, 0, -0.05)
cycloidal1 = sw_assem.add_component(Cycloidal_path, 0.05, 0.05, 0)
cycloidal2 = sw_assem.add_component(Cycloidal_path, 0.05, 0.05, 0.1)
if flange and pin and carrier:
    sw_assem.mate_faces(assem_name, pin, flange ,"Plane1","Plane1")   # 法兰面配合
    sw_assem.mate_axes(assem_name, pin, flange, "Axis1", "Axis1")    # 法兰销轴同心
    sw_assem.mate_axes(assem_name, pin, flange, "Axis2", "Axis2")    # 法兰销轴同心
    sw_assem.mate_axes(assem_name, flange, carrier, "Axis4", "Axis5")   
    sw_assem.mate_faces(assem_name, flange, carrier, "f_c","f_c")    # 法兰面和行星架面配合
    
    
    # sw_assem.mate_faces(assem_name, flange, carrier, "f_c1")    # 法兰面和行星架面配合

if carrier and planet1 and planet2 and planet3 and sun and cycloidal1 and cycloidal2:
    # 每个行星轮先面配合再轴配合
    for planet, axis in [(planet1, "Axis1"),
                         (planet2, "Axis2"),
                         (planet3, "Axis3")]:
        sw_assem.mate_axes(assem_name, carrier, planet, axis, "Axis1")       # 轴同心（行星轮轴固定为 Axis1）
        sw_assem.mate_faces(assem_name, carrier, planet, "Plane1","Plane1")                     # 面重合
    
    sw_assem.mate_axes(assem_name, sun, carrier, "Axis1", "Axis4")    
    sw_assem.mate_faces(assem_name, sun, planet1 ,"Top","Top")   # 太阳轮和行星轮配合
    
    # 配合行星轮和摆线轮
    sw_assem.mate_axes(assem_name, planet1, cycloidal1, "Axis2", "Axis1")    # 轴同心
    sw_assem.mate_axes(assem_name, planet2, cycloidal1, "Axis2", "Axis2")    # 轴同心
    sw_assem.mate_axes(assem_name, planet3, cycloidal1, "Axis2", "Axis3")    # 轴同心
    sw_assem.mate_axes(assem_name, planet1, cycloidal2, "Axis3", "Axis1")    # 轴同心
    sw_assem.mate_axes(assem_name, planet2, cycloidal2, "Axis3", "Axis2")    # 轴同心
    sw_assem.mate_axes(assem_name, planet3, cycloidal2, "Axis3", "Axis3")    # 轴同心
    
    sw_assem.mate_faces(assem_name, planet1, cycloidal1, "p_c","p_c")
    sw_assem.mate_faces(assem_name, planet1, cycloidal2, "p_c1","p_c1")
    
