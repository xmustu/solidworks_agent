import subprocess
import time
from pathlib import Path


# 按你的实际安装路径修改
SLDWORKS_EXE = r"D:\IndustrialSoftware\sw2026\SOLIDWORKS\SLDWORKS.exe"


def count_sldworks_processes() -> int:
    """
    使用 Windows tasklist 统计当前 SLDWORKS.exe 数量。
    不依赖 psutil。
    """
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
            text=True,
            errors="ignore",
        )

        count = 0
        for line in output.splitlines():
            if "SLDWORKS.exe" in line:
                count += 1

        return count

    except Exception as e:
        print(f"统计 SLDWORKS.exe 失败: {e}")
        return -1


def launch_sldworks_instances(num_instances: int = 4, delay: float = 12.0):
    exe_path = Path(SLDWORKS_EXE)

    if not exe_path.exists():
        print(f"找不到 SLDWORKS.exe: {exe_path}")
        return []

    procs = []

    print(f"启动前 SLDWORKS.exe 数量: {count_sldworks_processes()}")

    for i in range(num_instances):
        print(f"\n正在启动第 {i + 1}/{num_instances} 个 SOLIDWORKS...")
        
        proc = subprocess.Popen(
            [str(exe_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

        procs.append(proc)

        print(f"Popen PID: {proc.pid}")
        print(f"等待 {delay} 秒，让 SOLIDWORKS 初始化...")
        time.sleep(delay)

        alive = proc.poll() is None
        current_count = count_sldworks_processes()

        print(f"Popen 进程仍存活: {alive}")
        print(f"当前 SLDWORKS.exe 数量: {current_count}")

    print("\n===== 启动测试完成 =====")
    print(f"最终 SLDWORKS.exe 数量: {count_sldworks_processes()}")

    print("\n请手动打开任务管理器确认是否真的有多个 SLDWORKS.exe。")
    input("确认完成后按 Enter 结束脚本...")

    return procs


if __name__ == "__main__":
    launch_sldworks_instances(num_instances=4, delay=15.0)