import arcpy
import os
import re

# 规范化文件名的函数
def normalize_name(name):
    # 如果文件名以数字开头，在前面加上 "T"
    if re.match(r'^\d', name):
        name = 'T' + name
    
    # 保留中文字符，字母、数字和下划线，替换其他非法符号
    name = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9_]', '_', name)
    
    return name

def main(folder_path, new_gdb_path):
    # 创建新的 GDB（如果不存在）
    if not arcpy.Exists(new_gdb_path):
        arcpy.CreateFileGDB_management(os.path.dirname(new_gdb_path), os.path.basename(new_gdb_path))
        arcpy.AddMessage(f"成功创建新的 GDB: {new_gdb_path}")
    else:
        arcpy.AddMessage(f"GDB 已经存在: {new_gdb_path}")

    # 遍历主文件夹及其子文件夹中的所有文件
    for root, dirs, files in os.walk(folder_path):
        arcpy.AddMessage(f"\n正在处理文件夹: {root}")

        # 处理所有 .shp 文件
        for file in files:
            if file.endswith(".shp"):
                shp_path = os.path.join(root, file)
                target_feature_class = os.path.join(new_gdb_path, os.path.splitext(file)[0])
                
                # 规范化文件名
                normalized_name = normalize_name(os.path.splitext(file)[0])
                target_feature_class = os.path.join(new_gdb_path, normalized_name)

                # 覆盖目标中同名要素类
                if arcpy.Exists(target_feature_class):
                    arcpy.AddMessage(f"覆盖存在的要素类: {target_feature_class}")
                
                arcpy.CopyFeatures_management(shp_path, target_feature_class)
                arcpy.AddMessage(f"已复制 .shp: {shp_path} 到 {new_gdb_path}")

        # 处理所有 .gdb 文件夹
        for dir in dirs:
            if dir.endswith(".gdb"):
                gdb_path = os.path.join(root, dir)
                arcpy.AddMessage(f"\n正在处理 GDB: {gdb_path}")

                # 设置当前 GDB 作为工作空间
                arcpy.env.workspace = gdb_path

                # 列出 GDB 中的所有要素类
                feature_classes = arcpy.ListFeatureClasses()

                # 遍历每个要素类并复制到新的 GDB
                for feature_class in feature_classes:
                    target_feature_class = os.path.join(new_gdb_path, os.path.basename(feature_class))

                    # 复制时如果目标存在则覆盖
                    if arcpy.Exists(target_feature_class):
                        arcpy.AddMessage(f"覆盖存在的要素类: {target_feature_class}")
                    arcpy.Copy_management(feature_class, target_feature_class)
                    arcpy.AddMessage(f"已复制: {feature_class} 到 {new_gdb_path}")
    
    arcpy.AddMessage("\n所有文件和 GDB 中的要素类已成功复制到新的 GDB。")


# 如果此脚本被直接运行
if __name__ == "__main__":
    folder_path = arcpy.GetParameterAsText(0)  # 用户输入的文件夹路径
    new_gdb_path = arcpy.GetParameterAsText(1)  # 用户输入的目标 GDB 路径
    main(folder_path, new_gdb_path)