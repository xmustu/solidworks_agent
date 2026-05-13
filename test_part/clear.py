from pysw import SldWorksApp

swapp = SldWorksApp(close_before_task=True)
print("应用初始化成功！")

#建模步骤省略



#假设不在一个程序里跑
from pysw import SldWorksApp
import os
from pathlib import Path

swapp = SldWorksApp(close_before_task=False)
print("应用初始化成功！")

sw_app = SldWorksApp()

out_dir = r"..."
Path(out_dir).mkdir(parents=True, exist_ok=True)
shots = sw_app.capture_active_model_views(
    output_dir=out_dir,
    base_name="active_model_test",
    width=1600,
    height=1200,
    delay=0.3,
)
print("\n===== 截图结果 =====")
if not shots:
    print("❌ 没有生成任何截图。请确认 SOLIDWORKS 当前有打开的零件或装配体。")
