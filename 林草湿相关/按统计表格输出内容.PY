import arcpy
import pandas as pd
import os
from tkinter import messagebox, Tk

# 创建隐形的根窗口
root = Tk()
root.withdraw()

def main(feature_class, output_folder):
    # 创建字典来存储每个 XZQDM 的统计数据
    stats = {}

    # 初始化 log 函数
    def add_message_to_log(message):
        arcpy.AddMessage(message)

    # 获取要素类名称
    feature_name = os.path.basename(feature_class).split('.')[0]

    # 自动生成文件名
    output_excel = os.path.join(output_folder, f"{feature_name}_统计结果.xlsx")
    output_txt = os.path.join(output_folder, f"{feature_name}_地类变化统计结果.txt")

    # 建设用地、水面及其他的代码列表
    jsyd = [
        '0508', '05H1', '0601', '0602', '0701', '0702', '0809', '0810', '0810A', '08H1', '08H2', '08H2A', 
        '09', '1001', '1002', '1003', '1004', '1005', '1007', '1008', '1009', '1109', '1201'
    ]

    smqt = [
        '1006', '1101', '1102', '1103', '1104', '1104A', '1104K', '1106', '1107', '1107A', '1204', '1205', '1206', '1207'
    ]
    
    # 检查是否存在 'TBMJ_JC' 字段
    field_names = [field.name for field in arcpy.ListFields(feature_class)]
    if 'TBMJ_JC' not in field_names:
        add_message_to_log("字段 'TBMJ_JC' 不存在，正在创建...")
        arcpy.AddField_management(feature_class, 'TBMJ_JC', 'DOUBLE')
        add_message_to_log("字段 'TBMJ_JC' 已创建")

    # 弹出对话框询问用户是否重新计算TBMJ_JC
    message = "是否需要在TBMJ_JC字段重新计算椭球面积？"
    title = "重新计算椭球面积"
    response = messagebox.askyesno(title, message)

    if response:  # 计算 TBMJ_JC 字段
        add_message_to_log("正在重新计算椭球面积...")
        with arcpy.da.UpdateCursor(feature_class, ['TBMJ_JC', 'SHAPE@']) as cursor:
            for row in cursor:
                area = row[1].getArea("GEODESIC", "SQUAREMETERS") * 0.0015
                row[0] = round(area, 2)  # 保留两位小数
                cursor.updateRow(row)
    else:
        add_message_to_log("保留现有的 TBMJ_JC 值。")

    # 汇总各个区域的面积与图斑个数
    add_message_to_log("正在统计面积和个数")

    with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM', 'XZQDM', 'XZQMC']) as cursor:
        for row in cursor:
            tbmj_jc = row[0] if row[0] is not None else 0
            dlbm = row[1].strip() if row[1] is not None else ''
            hsdlbm = row[2].strip() if row[2] is not None else ''
            xzqdm = row[3].strip() if row[3] is not None else ''
            xzqmc = row[4].strip() if row[4] is not None else ''

            # 按 XZQDM 为空，初始化字典
            if xzqdm not in stats:
                stats[xzqdm] = {
                    'XZQMC': xzqmc,
                    '与变更一致面积': 0,
                    '与变更一致个数': 0,
                    '与变更不一致面积': 0,
                    '与变更不一致个数': 0,
                    '林地二级类变化面积': 0,
                    '林地二级类变化个数': 0,
                    '林地流入面积': 0,
                    '林地流入个数': 0,
                    '林地流出面积': 0,
                    '林地流出个数': 0,
                    '耕地流入面积': 0,
                    '耕地流入个数': 0,
                    '耕地流出面积': 0,
                    '耕地流出个数': 0,
                    '新增建设用地面积': 0,
                    '新增建设用地个数': 0
                }

            # 统计各个条件的面积与个数
            if dlbm == hsdlbm:
                stats[xzqdm]['与变更一致面积'] += tbmj_jc
                stats[xzqdm]['与变更一致个数'] += 1
            else:
                stats[xzqdm]['与变更不一致面积'] += tbmj_jc
                stats[xzqdm]['与变更不一致个数'] += 1

            if dlbm != hsdlbm and dlbm.startswith('03') and hsdlbm.startswith('03'):
                stats[xzqdm]['林地二级类变化面积'] += tbmj_jc
                stats[xzqdm]['林地二级类变化个数'] += 1

            if not dlbm.startswith('03') and hsdlbm.startswith('03'):
                stats[xzqdm]['林地流入面积'] += tbmj_jc
                stats[xzqdm]['林地流入个数'] += 1

            if dlbm.startswith('03') and not hsdlbm.startswith('03'):
                stats[xzqdm]['林地流出面积'] += tbmj_jc
                stats[xzqdm]['林地流出个数'] += 1

            if not dlbm.startswith('01') and hsdlbm.startswith('01'):
                stats[xzqdm]['耕地流入面积'] += tbmj_jc
                stats[xzqdm]['耕地流入个数'] += 1

            if dlbm.startswith('01') and not hsdlbm.startswith('01'):
                stats[xzqdm]['耕地流出面积'] += tbmj_jc
                stats[xzqdm]['耕地流出个数'] += 1
            
            if dlbm not in jsyd and hsdlbm in jsyd:
                stats[xzqdm]['新增建设用地面积'] += tbmj_jc
                stats[xzqdm]['新增建设用地个数'] += 1

    # 输出为 Excel 表格
    add_message_to_log("开始输出统计结果到 Excel 文件...")

    # 将字典转换为 pandas DataFrame
    df = pd.DataFrame.from_dict(stats, orient='index')

    # 输出到 Excel
    df.to_excel(output_excel, index=False)

    add_message_to_log(f"统计结果已输出到: {output_excel}")

    # 汇总各个区域的面积与图斑个数
    add_message_to_log("正在统计地类面积的变化情况")
    dlbm_stats = {'01': 0, '03': 0, '02': 0, '04': 0, 'jsyd': 0, 'smqt': 0, '0301': 0, '0302': 0, '0305': 0, '0307': 0}
    hsdlbm_stats = {'01': 0, '03': 0, '02': 0, '04': 0, 'jsyd': 0, 'smqt': 0, '0301': 0, '0302': 0, '0305': 0, '0307': 0}

    with arcpy.da.SearchCursor(feature_class, ['TBMJ_JC', 'DLBM', 'HSDLBM']) as cursor:
        for row in cursor:
            tbmj_jc = row[0] if row[0] is not None else 0
            dlbm = row[1].strip() if row[1] is not None else ''
            hsdlbm = row[2].strip() if row[2] is not None else ''
           
            if dlbm.startswith('01'):
                dlbm_stats['01'] += tbmj_jc
            if dlbm.startswith('03'):
                dlbm_stats['03'] += tbmj_jc
            if dlbm.startswith('02'):
                dlbm_stats['02'] += tbmj_jc
            if dlbm.startswith('04'):
                dlbm_stats['04'] += tbmj_jc
            if dlbm in jsyd:
                dlbm_stats['jsyd'] += tbmj_jc
            if dlbm in smqt:
                dlbm_stats['smqt'] += tbmj_jc

            if hsdlbm.startswith('01'):
                hsdlbm_stats['01'] += tbmj_jc
            if hsdlbm.startswith('03'):
                hsdlbm_stats['03'] += tbmj_jc
            if hsdlbm.startswith('02'):
                hsdlbm_stats['02'] += tbmj_jc
            if hsdlbm.startswith('04'):
                hsdlbm_stats['04'] += tbmj_jc
            if hsdlbm in jsyd:
                hsdlbm_stats['jsyd'] += tbmj_jc
            if hsdlbm in smqt:
                hsdlbm_stats['smqt'] += tbmj_jc

            if dlbm in ['0301', '0302', '0305', '0307']:
                dlbm_stats[dlbm] += tbmj_jc
            if hsdlbm in ['0301', '0302', '0305', '0307']:
                hsdlbm_stats[hsdlbm] += tbmj_jc

    # 输出为 TXT 文件
    add_message_to_log("开始输出统计结果到 TXT 文件...")

    land_type_names = {
    '01': '耕地',
    '03': '林地',
    '02': '园地',
    '04': '草地',
    'jsyd': '建设用地',
    'smqt': '水面及其他地类',
    '0301': '乔木林地',
    '0302': '竹林地',
    '0305': '灌木林地',
    '0307': '其他林地'
    }

    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("1、变更一上地类统计结果：\n")
        f.write(f"{land_type_names['01']}面积：{round(dlbm_stats['01']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['03']}面积：{round(dlbm_stats['03']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['02']}面积：{round(dlbm_stats['02']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['04']}面积：{round(dlbm_stats['04']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['jsyd']}面积：{round(dlbm_stats['jsyd']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['smqt']}面积：{round(dlbm_stats['smqt']/10000, 2)} 万亩\n")
        
        # 一上整体情况输出
        f.write(f"\n变更调查“一上”{land_type_names['01']}面积{round(dlbm_stats['01']/10000, 2)}万亩，")
        f.write(f"{land_type_names['03']}面积{round(dlbm_stats['03']/10000, 2)}万亩，")
        f.write(f"{land_type_names['02']}面积{round(dlbm_stats['02']/10000, 2)}万亩，")
        f.write(f"{land_type_names['04']}面积{round(dlbm_stats['04']/10000, 2)}万亩，")
        f.write(f"{land_type_names['jsyd']}面积{round(dlbm_stats['jsyd']/10000, 2)}万亩，")
        f.write(f"{land_type_names['smqt']}面积{round(dlbm_stats['smqt']/10000, 2)}万亩。\n")

        f.write("\n2、不一致图斑处置后统计结果：\n")
        f.write(f"{land_type_names['03']}面积：{round(hsdlbm_stats['03']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['01']}面积：{round(hsdlbm_stats['01']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['02']}面积：{round(hsdlbm_stats['02']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['04']}面积：{round(hsdlbm_stats['04']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['jsyd']}面积：{round(hsdlbm_stats['jsyd']/10000, 2)} 万亩\n")
        f.write(f"{land_type_names['smqt']}面积：{round(hsdlbm_stats['smqt']/10000, 2)} 万亩\n")

        # 处置后整体情况输出
        f.write(f"\n全市认定后{land_type_names['03']}面积{round(hsdlbm_stats['03']/10000, 2)}万亩，")
        f.write(f"{land_type_names['01']}面积{round(hsdlbm_stats['01']/10000, 2)}万亩，")
        f.write(f"{land_type_names['02']}面积{round(hsdlbm_stats['02']/10000, 2)}万亩，")
        f.write(f"{land_type_names['04']}面积{round(hsdlbm_stats['04']/10000, 2)}万亩，")
        f.write(f"{land_type_names['jsyd']}面积{round(hsdlbm_stats['jsyd']/10000, 2)}万亩，")
        f.write(f"{land_type_names['smqt']}面积{round(hsdlbm_stats['smqt']/10000, 2)}万亩。\n")
        
        f.write("\n3、地类净变化统计结果：\n")
        for land_type in ['03', '01', '02', '04', 'jsyd', 'smqt']:
            dlbm_total = dlbm_stats[land_type]
            hsdlbm_total = hsdlbm_stats[land_type]
            difference = dlbm_total - hsdlbm_total
            
            if difference < 0:
                result = "增加"
            else:
                result = "减少"

            f.write(f"{land_type_names[land_type]}净{result}{abs(round(difference))}亩，")

        # 统计林地二级类型的净变化
        f.write("\n4、乔木林地、竹林地、灌木林地及其他林地净增加/减少情况：\n")
        for land_code in ['0301', '0302', '0305', '0307']:
            dlbm_total = dlbm_stats.get(land_code, 0)
            hsdlbm_total = hsdlbm_stats.get(land_code, 0)
            difference = dlbm_total - hsdlbm_total
            
            if difference < 0:
                result = "增加"
            else:
                result = "减少"

            f.write(f"{land_type_names[land_code]}净{result}{abs(round(difference))}亩，")

    add_message_to_log(f"TXT文件已输出到: {output_txt}")

if __name__ == "__main__":
    feature_class = arcpy.GetParameterAsText(0)  # 输入的要素类
    output_folder = arcpy.GetParameterAsText(1)  # 输出的文件夹
    main(feature_class, output_folder)