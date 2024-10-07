import arcpy
workspace = arcpy.GetParameterAsText(0)  # 参数索引0表示第一个输入参数
arcpy.env.workspace = workspace

standard_fields = ['XZQDM', 'XZQMC', 'HCBSM', 'TBMJ', 'ZLDWDM', 'ZLDWMC', 'DLBM', 'DLMC', 
                   'LCSDLBM', 'QSXZ', 'CZCSXM', 'JCLX', 'XZB', 'YZB', 'TBBSM', 'GJNYYPDL', 
                   'GJNYYPTZ', 'GJLDFGLX', 'LCSDLMC', 'HSDLBM', 'HSDLMC', 'HSHZBFGLX', 
                   'WHSYY', 'BZ', 'TTQ', 'PDYJ', 'TBFGBZ','OBJECTID','SHAPE','SHAPE_LENGTH',
                   'SHAPE_AREA']

valid_hsdlbm_values = ['0101', '0102', '0103', '0201', '0201K', '0202', '0202K', '0204', '0204K', '0301', '0301K', 
                       '0302', '0302K', '0304', '0305', '0307', '0307K', '0401', '0403', '0404', '0508', '05H1', 
                       '0601', '0602', '0701', '0702', '0809', '0810', '0810A', '08H1', '08H2', '08H2A', '09', '1001', 
                       '1002', '1003', '1004', '1005', '1006', '1007', '1008', '1009', '1101', '1102','1103', '1104', 
                       '1104A', '1104K', '1106', '1107', '1107A', '1109', '1201', '1202', '1206', '1207']

valid_pdyj_values = ['2023年一上', '林草湿监测', '国家内业预判', '双方举证认定', '2023年三上', '自主新增图斑']

feature_classes = arcpy.ListFeatureClasses()

for feature_class in feature_classes:
    arcpy.AddMessage(f"\n检查要素文件: {feature_class}")
    
    # 检查字段——检查字段是否齐全
    current_fields = [field.name.upper() for field in arcpy.ListFields(feature_class)]
    missing_fields = [field for field in standard_fields if field.upper() not in current_fields]
    if missing_fields:
        arcpy.AddMessage(f"{feature_class} 缺失的字段: {', '.join(missing_fields)}")
    else:
        arcpy.AddMessage(f"{feature_class} 没有缺失字段。\n")

    # 检查字段——检查字段是否多余
    extra_fields = [field for field in current_fields if field not in standard_fields]
    if extra_fields:
        arcpy.AddMessage(f"多余字段: {extra_fields}\n")
    else:
        arcpy.AddMessage(f"{feature_class} 没有多余字段。\n")

    # 检查字段——TTQ
    arcpy.AddMessage(f"正在检查字段——TTQ")
    if 'TTQ' in current_fields:
        total_records = 0
        empty_ttq_count = 0
        with arcpy.da.SearchCursor(feature_class, ['TTQ', 'PDYJ']) as cursor:
            for row in cursor:
                total_records += 1
                ttq_value = row[0]
                pdyj_value = row[1]
                
                # 统计空值或空格的 TTQ 值
                if ttq_value is None or ttq_value.strip() == '':
                    empty_ttq_count += 1
                    continue  # 跳过空值或空格的 TTQ 记录

                # 继续检查有效的 TTQ 值
                if pdyj_value != '2023年一上':
                    arcpy.AddMessage("推土区未继承2023年一上。")
                if ttq_value != 'TD':
                    arcpy.AddMessage("推土字段未按要求填写。")

        # 如果所有 TTQ 字段都是空值或空格，则输出警告
        if empty_ttq_count == total_records:
            arcpy.AddMessage("警告：核实是否无推土区。")
    else:
        arcpy.AddMessage(f"{feature_class} 中没有 TTQ 字段。")
    arcpy.AddMessage(f"已完成 TTQ 字段的检查。\n")

    # 检查字段——PDYJ
    arcpy.AddMessage(f"正在检查字段——PDYJ")
    if 'PDYJ' in current_fields:
        invalid_values = set()
        has_null_value_reported = False
        pdyj_has_issues = False
        with arcpy.da.SearchCursor(feature_class, ['PDYJ']) as cursor:
            for row in cursor:
                value = row[0]
                if (value is None or value == '') and not has_null_value_reported:
                    arcpy.AddMessage(f"要素类 {feature_class} PDYJ中存在空值。")
                    has_null_value_reported = True
                    pdyj_has_issues = True
                elif value not in valid_pdyj_values and value not in invalid_values:
                    invalid_values.add(value)
                    pdyj_has_issues = True
        if pdyj_has_issues:
            if invalid_values:
                arcpy.AddMessage(f"要素类 {feature_class} PDYJ中存在不合法值: {list(invalid_values)}")
            arcpy.AddMessage(f"要素类 {feature_class} 中 PDYJ 字段检查完成，但存在问题。")
        else:
            arcpy.AddMessage(f"要素类 {feature_class} 中 PDYJ 字段填写正常。")
    else:
        arcpy.AddMessage(f"要素类 {feature_class} 中没有 PDYJ 字段。")
    arcpy.AddMessage(f"已完成 PDYJ 字段的检查。\n")

    # 检查字段——TBMJ是否为双精度
    arcpy.AddMessage(f"正在检查字段—TBMJ")
    if 'TBMJ' in current_fields:
        tbmj_field = arcpy.ListFields(feature_class, 'TBMJ')[0]  # 获取 TBMJ 字段的详细信息
        if tbmj_field.type == 'Double':
            arcpy.AddMessage(f"要素类 {feature_class} 中 TBMJ 字段为双精度。")
        else:
            arcpy.AddMessage(f"要素类 {feature_class} 中 TBMJ 字段不是双精度，其类型为: {tbmj_field.type}")
    else:
        arcpy.AddMessage(f"要素类 {feature_class} 中没有 TBMJ 字段。")
    arcpy.AddMessage(f"已完成 {feature_class} TBMJ的检查。\n")

    # 检查 HSDLBM 字段是否按照三调要求填写
    arcpy.AddMessage(f"正在检查字段—HSDLBM")
    if 'HSDLBM' in current_fields:
        invalid_values = set()
        has_null_value_reported = False
        hsdlbm_has_issues = False
        with arcpy.da.SearchCursor(feature_class, ['HSDLBM']) as cursor:
            for row in cursor:
                value = row[0]
                if (value is None or value == '') and not has_null_value_reported:
                    arcpy.AddMessage(f"要素类 {feature_class} 中 HSDLBM 存在空值。")
                    has_null_value_reported = True  # 只输出一次空值信息
                    hsdlbm_has_issues = True
                elif value not in valid_hsdlbm_values and value not in invalid_values:
                    invalid_values.add(value)  # 收集不合法值
                    hsdlbm_has_issues = True
        if hsdlbm_has_issues:
            if invalid_values:
                arcpy.AddMessage(f"要素类 {feature_class} 中 HSDLBM 存在不合法值: {list(invalid_values)}")
            arcpy.AddMessage(f"要素类 {feature_class} 中 HSDLBM 字段检查完成，但存在问题。")
        else:
            arcpy.AddMessage(f"要素类 {feature_class} 中 HSDLBM 字段正常。")
    else:
        arcpy.AddMessage(f"要素类 {feature_class} 中没有 HSDLBM 字段。")
    arcpy.AddMessage(f"已完成 {feature_class} 的检查。\n")
    
arcpy.AddMessage(f"已完成所有要素类的检查。")