import arcpy
import os

# 获取用户选择的工作空间
workspace = arcpy.GetParameterAsText(0)

# 设置工作空间环境
arcpy.env.workspace = workspace

# 定义需要检查的字段
field_pdyj = "PDYJ"
field_hsdlbm = "HSDLBM"
field_dlbm = "DLBM"
field_lcsdlmc = "LCSDLMC"
field_gjnyypdl = "GJNYYPDL"
field_gjnypptz = "GJNYYPTZ"
field_pdyj_check = "PDYJ_JC" #用PDYJ_JC取代判读依据检查
field_hcyj = "HCYJ_GFX"

耕地_hsdlbm = ['0101', '1002', '0103']
耕地_dlbm = ['0101', '1002', '0103']
忽略_pdyj = ['双方举证认定', '2023年三上','自主新增图斑']  #暂未使用

# 定义一个函数来处理要素类
def process_feature_class(fc):
    arcpy.AddMessage(f"正在处理要素类：{fc}")
    
    # 创建'判读依据检查'字段
    field_list = [f.name.upper() for f in arcpy.ListFields(fc)]
    if field_pdyj_check.upper() not in field_list:
        arcpy.AddField_management(fc, field_pdyj_check, "TEXT", field_length=100)
    # 如果字段已存在，初始化该字段为空值
    else: 
        arcpy.CalculateField_management(fc, field_pdyj_check, "''", "PYTHON3")
        arcpy.AddMessage(f"字段 {field_pdyj_check} 已初始化为空值")
    
    # 更新'判读依据检查'字段
    with arcpy.da.UpdateCursor(fc, [field_hsdlbm, field_dlbm, field_pdyj, field_lcsdlmc, field_gjnyypdl, field_gjnypptz, field_pdyj_check, field_hcyj]) as cursor:
        for row in cursor:
            hsdlbm = row[0]
            dlbm = row[1]
            pdyj = row[2]
            lcsdlmc = row[3]
            gjnyypdl = row[4]
            gjnypptz = row[5]
            pdyj_check = row[6]
            hcyj = row[7]

            # 检查 pdyj_check 是否为空字符串或 None
            if pdyj_check is None or pdyj_check.strip() == '' or pdyj:
                pdyj_check = None  # 将空字符串视为 None 处理

            # 新规则: DLBM不为耕地类，HSDLBM为耕地类，PDYJ不为'2023年三上'
            if dlbm not in 耕地_dlbm and hsdlbm in 耕地_hsdlbm and pdyj != '2023年三上':
                row[6] = '新增耕地需外业举证'
                if row[7]:
                    row[7] += ';新增耕地需外业举证'
                else:
                    row[7] = '新增耕地需外业举证'
                cursor.updateRow(row)
                continue  # 跳过后续规则

            # 规则1: “2023年一上”的一致性核实情况，PDYJ不包含“双方举证认定”或“2023年三上”
            if not pdyj_check and hsdlbm == dlbm and pdyj not in ['双方举证认定', '2023年三上','自主新增图斑']:
                row[6] = '2023年一上'
                cursor.updateRow(row)
                continue  # 跳过后续规则
            
            # 新规则: 如果标注了“双方举证认定”或“2023年三上”，直接继承
            if not pdyj_check and pdyj in ['双方举证认定', '2023年三上','自主新增图斑']:
                row[6] = pdyj
                cursor.updateRow(row)
                continue  # 跳过后续规则
            
            # 规则2: '林草湿监测'的一致性核实情况
            if not pdyj_check:
                if hsdlbm == '0301' and lcsdlmc == '乔木林地':
                    row[6] = '林草湿监测'
                elif hsdlbm == '0302' and lcsdlmc == '竹林地':
                    row[6] = '林草湿监测'
                elif hsdlbm == '0305' and lcsdlmc == '灌木林地':
                    row[6] = '林草湿监测'
                elif hsdlbm == '0307' and lcsdlmc == '其他林地':
                    row[6] = '林草湿监测'
                cursor.updateRow(row)
            
            # 规则3: 林地类GJNYYPDL的一致性核实情况
            if not pdyj_check and hsdlbm == gjnyypdl:
                if row[6]:  # 如果已有值
                    continue
                else:  # 如果为空
                    row[6] = '国家内业预判'
                cursor.updateRow(row)

            # 规则4: GJNYYPTZ为一级类的一致性核实情况
            if not pdyj_check:
                if hsdlbm in ['0101', '0102', '0103'] and gjnypptz == '01':
                    if row[6]:
                        row[6] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[6] = '未经举证判读为国家预判的QT类'
                    if row[7]:
                        row[7] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[7] = '未经举证判读为国家预判的QT类'
                elif hsdlbm in ['0201', '0201K', '0202', '0202K', '0204', '0204K'] and gjnypptz == '02':
                    if row[6]:
                        row[6] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[6] = '未经举证判读为国家预判的QT类'
                    if row[7]:
                        row[7] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[7] = '未经举证判读为国家预判的QT类'
                elif hsdlbm in ['0401', '0403', '0404'] and gjnypptz == '04':
                    if row[6]:
                        row[6] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[6] = '未经举证判读为国家预判的QT类'
                    if row[7]:
                        row[7] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[7] = '未经举证判读为国家预判的QT类'
                elif hsdlbm in ['0508', '05H1', '0601', '0602', '0701', '0702', '0809', '0810', '0810A', '08H1', '08H2', '08H2A', '09', '1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008', '1009', '1109', '1201', '1202'] and gjnypptz in ['QT', 'QTYD', 'JS']:
                    if row[6]:
                        row[6] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[6] = '未经举证判读为国家预判的QT类'
                    if row[7]:
                        row[7] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[7] = '未经举证判读为国家预判的QT类'
                elif hsdlbm in ['1101', '1102', '1103', '1104', '1104A', '1104K', '1106', '1107', '1107A'] and gjnypptz == 'SM':
                    if row[6]:
                        row[6] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[6] = '未经举证判读为国家预判的QT类'
                    if row[7]:
                        row[7] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[7] = '未经举证判读为国家预判的QT类'
                elif hsdlbm in ['1206', '1207', '1006', '1107'] and gjnypptz in ['QT', 'QTYD']:
                    if row[6]:
                        row[6] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[6] = '未经举证判读为国家预判的QT类'
                    if row[7]:
                        row[7] += ';未经举证判读为国家预判的QT类'
                    else:
                        row[7] = '未经举证判读为国家预判的QT类'
                cursor.updateRow(row)

    arcpy.AddMessage(f"要素类 {fc} 已完成检查")

# 遍历工作空间中的所有文件夹和子文件夹
def process_workspace(workspace):
    for root, dirs, files in os.walk(workspace):
        arcpy.env.workspace = root

        # 处理gdb中的要素类
        gdbs = [os.path.join(root, d) for d in dirs if d.endswith('.gdb')]
        for gdb in gdbs:
            arcpy.env.workspace = gdb
            feature_classes = arcpy.ListFeatureClasses()
            for fc in feature_classes:
                process_feature_class(fc)

        # 处理shp文件
        shp_files = [os.path.join(root, f) for f in files if f.endswith('.shp')]
        for shp in shp_files:
            process_feature_class(shp)

# 执行主程序
if __name__ == '__main__':
    process_workspace(workspace)
    arcpy.AddMessage("检查完成")