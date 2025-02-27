import arcpy
import os

def build_pyramids(file_paths):
    total_files = len(file_paths)
    for i, file_path in enumerate(file_paths):
        try:
            arcpy.AddMessage(f"正在构建: {file_path}")
            
            arcpy.SetProgressorPosition(i + 1)

            arcpy.BuildPyramids_management(
                file_path, "-1", "NONE", "NEAREST", "JPEG", "100", "SKIP_EXISTING"
            )
            arcpy.AddMessage(f"金字塔构建成功: {file_path}")
        except arcpy.ExecuteError as e:
            arcpy.AddError(f"执行错误: {arcpy.GetMessages(2)}")
        except Exception as e:
            arcpy.AddError(f"发生错误: {e}")

    arcpy.AddMessage("所有金字塔构建完成。")

def main():
    # 获取参数
    input_folders = arcpy.GetParameterAsText(0).split(";")

    # 调试信息
    arcpy.AddMessage(f"输入文件夹: {input_folders}")

    file_paths = []
    for input_folder in input_folders:
        # 检查文件夹是否存在
        if not os.path.exists(input_folder):
            arcpy.AddError(f"输入文件夹不存在: {input_folder}")
            continue

        # 获取文件夹及其子文件夹中的所有 TIFF 文件
        try:
            for root, _, files in os.walk(input_folder):
                for f in files:
                    if f.endswith('.tif'):
                        file_paths.append(os.path.join(root, f))
        except Exception as e:
            arcpy.AddError(f"无法列出文件夹中的文件: {e}")
            continue

    if not file_paths:
        arcpy.AddWarning("没有找到影像文件。")
        return

    total_files = len(file_paths)
    arcpy.SetProgressor(
        "step", 
        "构建金字塔...", 
        0,          # min_range
        total_files, # max_range 
        1           # step_interval
    )
    build_pyramids(file_paths)

if __name__ == "__main__":
    main()