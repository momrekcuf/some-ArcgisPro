import arcpy

workspace = arcpy.GetParameterAsText(0)  # 参数索引0表示第一个输入参数
arcpy.env.workspace = workspace

standard_fields = ['XZQDM', 'XZQMC', 'HCBSM', 'TBMJ', 'ZLDWDM', 'ZLDWMC', 'DLBM', 'DLMC', 
                   'LCSDLBM', 'QSXZ', 'CZCSXM', 'JCLX', 'XZB', 'YZB', 'TBBSM', 'GJNYYPDL', 
                   'GJNYYPTZ', 'GJLDFGLX', 'LCSDLMC', 'HSDLBM', 'HSDLMC', 'HSHZBFGLX', 
                   'WHSYY', 'BZ', 'TTQ', 'PDYJ', 'TBFGBZ', 'OBJECTID', 'SHAPE', 'SHAPE_LENGTH',
                   'SHAPE_AREA', 'HCYJ_GFX', 'TBMJ_JC']  # 新增字段

valid_hsdlbm_values = ['0101', '0102', '0103', '0201', '0201K', '0202', '0202K', '0204', '0204K', '0301', '0301K', 
                       '0302', '0302K', '0304', '0305', '0307', '0307K', '0401', '0403', '0404', '0508', '05H1', 
                       '0601', '0602', '0701', '0702', '0809', '0810', '0810A', '08H1', '08H2', '08H2A', '09', '1001', 
                       '1002', '1003', '1004', '1005', '1006', '1007', '1008', '1009', '1101', '1102', '1103', '1104', 
                       '1104A', '1104K', '1106', '1107', '1107A', '1109', '1201', '1202', '1204','1205','1206', '1207']

valid_pdyj_values = ['2023年一上', '林草湿监测', '国家内业预判', '双方举证认定', '2023年三上', '自主新增图斑']

feature_classes = arcpy.ListFeatureClasses()

for feature_class in feature_classes:
    arcpy.AddMessage(f"\n检查要素文件: {feature_class}")
    
    # 检查并添加 HCYJ_GFX 字段
    current_fields = [field.name.upper() for field in arcpy.ListFields(feature_class)]
    if 'HCYJ_GFX' not in current_fields:
        arcpy.AddField_management(feature_class, 'HCYJ_GFX', 'TEXT', field_length=250)
        arcpy.AddMessage(f"{feature_class} 中已添加字段 HCYJ_GFX。")
    
    if 'TBMJ_JC' not in current_fields:
        arcpy.AddField_management(feature_class, 'TBMJ_JC', 'DOUBLE')
        arcpy.AddMessage(f"{feature_class} 中已添加字段 TBMJ_JC。")

    # 检查字段是否齐全
    missing_fields = [field for field in standard_fields if field.upper() not in current_fields]
    if missing_fields:
        arcpy.AddMessage(f"{feature_class} 缺失的字段: {', '.join(missing_fields)}")
    else:
        arcpy.AddMessage(f"{feature_class} 没有缺失字段。\n")

    # 检查字段是否多余
    extra_fields = [field for field in current_fields if field not in standard_fields]
    if extra_fields:
        arcpy.AddMessage(f"多余字段: {extra_fields}\n")
    else:
        arcpy.AddMessage(f"{feature_class} 没有多余字段。\n")

    # 更新 HCYJ_GFX 字段（基于行索引）
    def update_hcyj_gfx(fc, row_idx, message):
        with arcpy.da.UpdateCursor(fc, ['HCYJ_GFX']) as cursor:
            for i, row in enumerate(cursor):
                if i == row_idx:
                    if row[0] is None:
                        row[0] = message
                    else:
                        row[0] += f"; {message}"
                    cursor.updateRow(row)

    # 检查字段——TTQ
    arcpy.AddMessage(f"正在检查字段——TTQ")
    if 'TTQ' in current_fields:
        total_records = 0
        empty_ttq_count = 0
        with arcpy.da.SearchCursor(feature_class, ['TTQ', 'PDYJ']) as cursor:
            for row_idx, row in enumerate(cursor):
                total_records += 1
                ttq_value = row[0]
                pdyj_value = row[1]
                
                # 跳过空值或空格的 TTQ 记录
                if ttq_value is None or ttq_value.strip() == '':
                    empty_ttq_count += 1
                    continue  

                # 继续检查有效的 TTQ 值
                if pdyj_value != '2023年一上' and pdyj_value != '双方举证认定':
                    message = "推土区未继承2023年一上。"
                    arcpy.AddMessage(message)
                    update_hcyj_gfx(feature_class, row_idx, message)

                if ttq_value != 'TD':
                    message = "推土字段未按要求填写。"
                    arcpy.AddMessage(message)
                    update_hcyj_gfx(feature_class, row_idx, message)
         # 如果所有 TTQ 字段都是空值或空格，则输出警告
        if empty_ttq_count == total_records:
            arcpy.AddMessage("警告：核实是否无推土区。")
            
    else:
        arcpy.AddMessage(f"{feature_class} 中没有 TTQ 字段。")
    arcpy.AddMessage(f"已完成 TTQ 字段的检查。\n")

    # 检查字段——PDYJ
    arcpy.AddMessage(f"正在检查字段——PDYJ")
    if 'PDYJ' in current_fields:
        with arcpy.da.SearchCursor(feature_class, ['PDYJ']) as cursor:
            for row_idx, row in enumerate(cursor):
                value = row[0]
                if value is None or value == '':
                    message = "PDYJ中存在空值。"
                    arcpy.AddMessage(message)
                    update_hcyj_gfx(feature_class, row_idx, message)
                elif value not in valid_pdyj_values:
                    message = f"PDYJ中存在不合法值: {value}"
                    arcpy.AddMessage(message)
                    update_hcyj_gfx(feature_class, row_idx, message)
    else:
        arcpy.AddMessage(f"{feature_class} 中没有 PDYJ 字段。")
    arcpy.AddMessage(f"已完成 PDYJ 字段的检查。\n")

    # 检查 HSDLBM 字段是否按照三调要求填写
    arcpy.AddMessage(f"正在检查字段—HSDLBM")
    if 'HSDLBM' in current_fields:
        with arcpy.da.SearchCursor(feature_class, ['HSDLBM']) as cursor:
            for row_idx, row in enumerate(cursor):
                value = row[0]
                if value is None or value == '':
                    message = "HSDLBM 存在空值。"
                    arcpy.AddMessage(message)
                    update_hcyj_gfx(feature_class, row_idx, message)
                elif value not in valid_hsdlbm_values:
                    message = f"HSDLBM 存在不合法值: {value}"
                    arcpy.AddMessage(message)
                    update_hcyj_gfx(feature_class, row_idx, message)
    else:
        arcpy.AddMessage(f"{feature_class} 中没有 HSDLBM 字段。")
    arcpy.AddMessage(f"已完成 {feature_class} 的检查。\n")

     # 计算 TBMJ_JC
    arcpy.AddMessage("计算 TBMJ_JC 字段")
    with arcpy.da.UpdateCursor(feature_class, ['TBMJ_JC', 'SHAPE@']) as cursor:
        for row in cursor:
            area = row[1].getArea("GEODESIC", "SQUAREMETERS") * 0.0015
            row[0] = round(area, 2)  # 保留两位小数
            cursor.updateRow(row)

    # 汇总 TBMJ_JC 的总面积
    total_area = 0
    with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC']) as cursor:
        for row in cursor:
            total_area += row[0] if row[0] is not None else 0

    arcpy.AddMessage(f"提交图斑面积总计 {total_area} 亩。\n")

    # 汇总根据 DLBM 和 HSDLBM 的条件
    areas = {
    "一致": 0,
    "不一致": 0,
    "林地二级类变化": 0,
    "林地流入": 0,
    "林地流出": 0,
    "耕地流入": 0,
    "耕地流出": 0
}

# 第一遍循环：计算与变更调查一致的面积
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 与变更调查一致
        if dlbm == hsdlbm:
            areas["一致"] += tbmj_jc

# 第二遍循环：计算与变更调查不一致的面积
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 与变更调查不一致
        if dlbm != hsdlbm:
            areas["不一致"] += tbmj_jc

# 第三遍循环：计算林地二级类变化
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 林地二级类变化
        if dlbm != hsdlbm and dlbm.startswith('03') and hsdlbm.startswith('03'):
            areas["林地二级类变化"] += tbmj_jc

# 第四遍循环：计算林地流入
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 林地流入
        if not dlbm.startswith('03') and hsdlbm.startswith('03'):
            areas["林地流入"] += tbmj_jc

# 第五遍循环：计算林地流出
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 林地流出
        if dlbm.startswith('03') and not hsdlbm.startswith('03'):
            areas["林地流出"] += tbmj_jc

# 第六遍循环：计算耕地流入
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 耕地流入
        if not dlbm.startswith('01') and hsdlbm.startswith('01'):
            areas["耕地流入"] += tbmj_jc

# 第七遍循环：计算耕地流出
with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
    for row in cursor:
        tbmj_jc = row[0] if row[0] is not None else 0
        dlbm = row[1].strip() if row[1] is not None else ''
        hsdlbm = row[2].strip() if row[2] is not None else ''

        # 耕地流出
        if dlbm.startswith('01') and not hsdlbm.startswith('01'):
            areas["耕地流出"] += tbmj_jc

    # 输出汇总结果
    arcpy.AddMessage(f"与变更调查一致的面积为 {areas['一致']} 亩。")
    arcpy.AddMessage(f"与变更调查不一致的面积为 {areas['不一致']} 亩。")
    arcpy.AddMessage(f"林地二级类变化为 {areas['林地二级类变化']} 亩。")
    arcpy.AddMessage(f"林地流入 {areas['林地流入']} 亩。")
    arcpy.AddMessage(f"林地流出 {areas['林地流出']} 亩。")
    arcpy.AddMessage(f"耕地流入 {areas['耕地流入']} 亩。")
    arcpy.AddMessage(f"耕地流出 {areas['耕地流出']} 亩。")

arcpy.AddMessage(f"已完成所有要素类的检查。")