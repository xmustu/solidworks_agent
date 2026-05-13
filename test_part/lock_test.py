import asyncio
from concurrent.futures import ThreadPoolExecutor
from pysw import SldWorksApp, PartDoc


def create_cylinder_part(index: int):
    """
    创建一个简单圆柱体零件，用于测试 SolidWorks 自身进程锁。
    不使用 Python threading.Lock。
    """

    part_name = f"AsyncCylinder_{index}"

    print(f"[Task {index}] 开始创建零件: {part_name}")

    app = SldWorksApp()
    sw_doc = PartDoc(app.createAndActivate_sw_part(part_name))

    sketch = sw_doc.insert_sketch_on_plane("XY")

    sw_doc.create_circle(
        center_x=0,
        center_y=0,
        radius=0.01 + index * 0.002,
        sketch_ref="XY"
    )

    sw_doc.extrude(
        sketch=sketch,
        depth=0.02 + index * 0.005,
        single_direction=True,
        merge=True
    )

    print(f"[Task {index}] 零件创建完成: {part_name}")


async def main():
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_running_loop()

    tasks = []

    for i in range(1, 5):
        print(f"[Main] 提交 Task {i}")

        task = loop.run_in_executor(
            executor,
            create_cylinder_part,
            i
        )

        tasks.append(task)

        if i < 4:
            await asyncio.sleep(1)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    print("\n========== 测试结果 ==========")

    for i, result in enumerate(results, start=1):
        if isinstance(result, Exception):
            print(f"[Task {i}] 失败: {repr(result)}")
        elif result is None:
            print(f"[Task {i}] 执行完成，但保存失败")
        else:
            print(f"[Task {i}] 成功: {result}")


if __name__ == "__main__":
    asyncio.run(main())