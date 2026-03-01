import arcpy
import os

workspace = arcpy.GetParameterAsText(0)
arcpy.env.workspace = workspace

feature_classes = arcpy.ListFeatureClasses()

field_pdyj = "PDYJ"
field_hsdlbm = "HSDLBM"
field_dlbm = "DLBM"
field_lcsdlmc = "LCSDLMC"
field_gjnyypdl = "GJNYYPDL"
field_gjnypptz = "GJNYYPTZ"
field_pdyj_check = "判读依据检查"

for fc in feature_classes:
    arcpy.AddMessage(f"正在处理要素类：{fc}")
    
    # 创建'判读依据检查'字段
    field_list = [f.name.upper() for f in arcpy.ListFields(fc)]
    if field_pdyj_check.upper() not in field_list:
        arcpy.AddField_management(fc, field_pdyj_check, "TEXT", field_length=100)
    
    # 更新'判读依据检查'字段
    with arcpy.da.UpdateCursor(fc, [field_hsdlbm, field_dlbm, field_pdyj, field_lcsdlmc, field_gjnyypdl, field_gjnypptz, field_pdyj_check]) as cursor:
        for row in cursor:
            hsdlbm = row[0]
            dlbm = row[1]
            pdyj = row[2]
            lcsdlmc = row[3]
            gjnyypdl = row[4]
            gjnypptz = row[5]
            pdyj_check = row[6]
            
            # 规则1: “2023年一上”的一致性核实情况，PDYJ不包含“双方举证认定”或“2023年三上”
            if not pdyj_check and hsdlbm == dlbm and pdyj not in ['双方举证认定', '2023年三上']:
                row[6] = '2023年一上'
                cursor.updateRow(row)
                continue  # 跳过后续规则
            
            # 新规则: 如果标注了“双方举证认定”或“2023年三上”，直接继承
            if not pdyj_check and pdyj in ['双方举证认定', '2023年三上']:
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
                    row[6] += '、国家内业预判'
                else:  # 如果为空
                    row[6] = '国家内业预判'
                cursor.updateRow(row)

            # 规则4: GJNYYPTZ为一级类的一致性核实情况
            if not pdyj_check:
                if hsdlbm in ['0101', '0102', '0103'] and gjnypptz == '01':
                    if row[6]:
                        row[6] += '、国家内业预判'
                    else:
                        row[6] = '国家内业预判'
                elif hsdlbm in ['0201', '0201K', '0202', '0202K', '0204', '0204K'] and gjnypptz == '02':
                    if row[6]:
                        row[6] += '、国家内业预判'
                    else:
                        row[6] = '国家内业预判'
                elif hsdlbm in ['0401', '0403', '0404'] and gjnypptz == '04':
                    if row[6]:
                        row[6] += '、国家内业预判'
                    else:
                        row[6] = '国家内业预判'
                elif hsdlbm in ['0508', '05H1', '0601', '0602', '0701', '0702', '0809', '0810', '0810A', '08H1', '08H2', '08H2A', '09', '1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008', '1009', '1109', '1201', '1202'] and gjnypptz == 'JS':
                    if row[6]:
                        row[6] += '、国家内业预判'
                    else:
                        row[6] = '国家内业预判'
                elif hsdlbm in ['1101', '1102', '1103', '1104', '1104A', '1104K', '1106', '1107', '1107A'] and gjnypptz == 'SM':
                    if row[6]:
                        row[6] += '、国家内业预判'
                    else:
                        row[6] = '国家内业预判'
                elif hsdlbm in ['1206', '1207', '1006', '1107'] and gjnypptz in ['QT', 'QTYD']:
                    if row[6]:
                        row[6] += '、国家内业预判'
                    else:
                        row[6] = '国家内业预判'
                cursor.updateRow(row)

    arcpy.AddMessage(f"要素类 {fc} 已完成检查")