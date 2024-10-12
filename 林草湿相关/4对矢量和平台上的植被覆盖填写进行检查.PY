import arcpy
import os

field_hshzbfglx = "HSHZBFGLX"
field_bglyzbfg = "BGLYZBFG"
field_hsdlbm = "HSDLBM"
field_zbfgjc_gfx = "ZBFGJC_GFX"

def add_field_if_not_exists(fc, field_name, field_type="TEXT", field_length=250):
    # 检查字段是否存在，如果不存在则添加
    field_list = [f.name.upper() for f in arcpy.ListFields(fc)]
    if field_name.upper() not in field_list:
        arcpy.AddField_management(fc, field_name, field_type, field_length=field_length)
        arcpy.AddMessage(f"已创建字段: {field_name}")
    else:
        arcpy.AddMessage(f"字段 {field_name} 已存在")

def check_zbfg(fc):
    arcpy.AddMessage(f"正在处理要素类：{fc}")

    # 添加字段
    add_field_if_not_exists(fc, field_zbfgjc_gfx)
    
    # 定义所需的字段
    fields = [field_hsdlbm, field_hshzbfglx, field_bglyzbfg, field_zbfgjc_gfx]

    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        for row in cursor:
            hsdlbm = row[0]  # HSDLBM字段
            hsh_zbfglx = row[1]  # HSHZBFGLX字段
            bgly_zbfg = row[2]  # BGLYZBFG字段
            zbfgjc_gfx = row[3]  # ZBFGJC_GFX字段

            # 初始化字段值为空，如果没有值则给它赋值为空字符串，便于后续拼接内容
            if not zbfgjc_gfx:
                zbfgjc_gfx = ""

            # HSDLBM为空值报错：HSDLBM是否为空或空白
            if not hsdlbm or not hsdlbm.strip():
                zbfgjc_gfx += 'HSDLBM填写为空，请核实；'

            # 检查矢量中HSDLBM与HSHZBFGLX的冲突逻辑
            if hsdlbm and hsdlbm.strip():
                # 检查HSHZBFGLX是否为空值或空白
                if hsh_zbfglx and hsh_zbfglx.strip():
                    hsh_zbfglx_prefix = hsh_zbfglx[:4]

                    # HSDLBM为0301的冲突检查
                    if hsdlbm == "0301" and hsh_zbfglx_prefix not in ['1110', '1111', '1112', '1113']:
                        zbfgjc_gfx += '矢量HSHZBFGLX填写与HSDLBM冲突；'

                    # HSDLBM为0302的冲突检查
                    if hsdlbm == "0302" and hsh_zbfglx_prefix not in ['1130', '1131', '1132']:
                        zbfgjc_gfx += '矢量HSHZBFGLX填写与HSDLBM冲突；'

                    # HSDLBM为0305的冲突检查
                    if hsdlbm == "0305" and hsh_zbfglx_prefix not in ['1300', '1310', '1311', '1312', '1313', '1314', '1320']:
                        zbfgjc_gfx += '矢量HSHZBFGLX填写与HSDLBM冲突；'

                    # HSDLBM为0307的冲突检查
                    if hsdlbm == "0307" and hsh_zbfglx_prefix not in ['1200', '1210', '1220', '1230', '1400', '1410', '1420', '4000']:
                        zbfgjc_gfx += '矢量HSHZBFGLX填写与HSDLBM冲突；'

                # 如果HSDLBM的开头不为03，检查非林地的标注问题
                if not hsdlbm.startswith("03") and hsh_zbfglx and hsh_zbfglx.strip():
                    zbfgjc_gfx += 'HSDLBM为非林地，矢量上暂不允许标注植被覆盖；'

            # 检查HSDLBM与平台填报BGLYZBFG的冲突逻辑
            if hsdlbm and hsdlbm.strip():
                
                # 空值不参与检查：BGLYZBFG是否为空值或空白
                if bgly_zbfg and bgly_zbfg.strip():
                    bgly_zbfg_prefix = bgly_zbfg[:4]
                
                    # HSDLBM为0301的BGLYZBFG冲突检查
                    if hsdlbm == "0301" and bgly_zbfg_prefix not in ['1110', '1111', '1112', '1113']:
                        zbfgjc_gfx += '平台填写植被覆盖与HSDLBM冲突；'

                    # HSDLBM为0302的BGLYZBFG冲突检查
                    if hsdlbm == "0302" and bgly_zbfg_prefix not in ['1130', '1131', '1132']:
                        zbfgjc_gfx += '平台填写植被覆盖与HSDLBM冲突；'

                    # HSDLBM为0305的BGLYZBFG冲突检查
                    if hsdlbm == "0305" and bgly_zbfg_prefix not in ['1300', '1310', '1311', '1312', '1313', '1314', '1320']:
                        zbfgjc_gfx += '平台填写植被覆盖与HSDLBM冲突；'

                    # HSDLBM为0307的BGLYZBFG冲突检查
                    if hsdlbm == "0307" and bgly_zbfg_prefix not in ['1200', '1210', '1220', '1230', '1400', '1410', '1420', '4000']:
                        zbfgjc_gfx += '平台填写植被覆盖与HSDLBM冲突；'

                # 如果HSDLBM的开头不为03，检查非林地的植被覆盖标注问题
                if not hsdlbm.startswith("03") and bgly_zbfg and bgly_zbfg.strip():
                    zbfgjc_gfx += 'HSDLBM为非林地，平台上暂不允许标注植被覆盖；'

            # 平台和矢量的一致性：比较BGLYZBFG和HSHZBFGLX的前4位
            if bgly_zbfg and bgly_zbfg.strip() and hsh_zbfglx and hsh_zbfglx.strip():
                bgly_zbfg_prefix = bgly_zbfg[:4]
                hsh_zbfglx_prefix = hsh_zbfglx[:4]
                
                if bgly_zbfg_prefix != hsh_zbfglx_prefix:
                    zbfgjc_gfx += '矢量填写植被覆盖与平台填写植被覆盖不一致；'

            # 更新ZBFGJC_GFX字段
            row[3] = zbfgjc_gfx
            cursor.updateRow(row)

    arcpy.AddMessage(f"要素类处理完成，并输出结果到ZBFGJC_GFX字段：{fc}")

# 调用输入的文件夹
workspace = arcpy.GetParameterAsText(0)  
arcpy.env.workspace = workspace

# 遍历工作空间中的所有文件夹和子文件夹
for root, dirs, files in os.walk(workspace):
    # 处理gdb中的要素类
    gdbs = [os.path.join(root, d) for d in dirs if d.endswith('.gdb')]
    for gdb in gdbs:
        arcpy.env.workspace = gdb
        feature_classes = arcpy.ListFeatureClasses()
        for fc in feature_classes:
            check_zbfg(fc)

    # 处理shp文件
    shp_files = [os.path.join(root, f) for f in files if f.endswith('.shp')]
    for shp in shp_files:
        check_zbfg(shp)