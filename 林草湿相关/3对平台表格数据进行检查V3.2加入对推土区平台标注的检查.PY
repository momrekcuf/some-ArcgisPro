import arcpy
import pandas as pd
import os
from tkinter import Tk, messagebox

# 不显示 Tkinter 根窗口
root = Tk()
root.withdraw()

# 函数：添加字段
def add_fields(feature_class):
    fields = [
        ("CTBH", "TEXT", 100),
        ("BGJZZT", "TEXT", 100),
        ("BGLYJG", "TEXT", 100),
        ("BGLYDL", "TEXT", 100),
        ("BGLYZBFG", "TEXT", 100),
        ("BGGZJG", "TEXT", 100),
        ("BGGZDL", "TEXT", 100),
        ("BGGZJZLX", "TEXT", 100),
        ("BGGZSM", "TEXT", 250),
        ("BGGZWHS", "TEXT", 100),
        ("BGDLBM", "TEXT", 100),
        ("BGHS", "TEXT", 250),
        ("BGHCYJ_GFX", "TEXT", 250),
        ("TJGJ", "TEXT", 100),
        ("TJCTBH", "TEXT", 100)
    ]

    for field in fields:
        arcpy.AddField_management(feature_class, field[0], field[1], field_length=field[2])

    arcpy.AddMessage("字段创建完成")


# 函数：计算CTBH字段
def calculate_ctbh(feature_class):
    with arcpy.da.UpdateCursor(feature_class, ["TBFGBZ", "HCBSM", "CTBH"]) as cursor:
        for row in cursor:
            tbf_value = row[0]
            hcb_value = row[1]
            if tbf_value and tbf_value.startswith("草图"):
                try:
                    num = int(tbf_value[-1])
                    row[2] = f"{hcb_value}-{num}"
                except (ValueError, IndexError):
                    row[2] = f"{hcb_value}-1"
            else:
                row[2] = f"{hcb_value}-1"
            cursor.updateRow(row)
    arcpy.AddMessage("CTBH计算完成")


# 函数：挂接、检查CTBH并更新字段
def match_and_update_fields(feature_class, excel_df, bu_column_index):
    # 将Excel的CTBH列预处理为字典，键为CTBH，值为索引
    ctbh_dict = {ctbh: index for index, ctbh in enumerate(excel_df.iloc[:, 8])}

    with arcpy.da.UpdateCursor(feature_class, [
        "CTBH", "BGJZZT", "BGLYJG", "BGLYDL", "BGLYZBFG", "BGGZJG", "BGGZDL", 
        "BGGZJZLX", "BGGZSM", "BGGZWHS", "BGHS"
    ]) as cursor:
        for row in cursor:
            ctbh_value = row[0]

            # 使用字典查找匹配
            if ctbh_value in ctbh_dict:
                match_index = ctbh_dict[ctbh_value]

                # 更新相关字段
                row[1] = excel_df.iloc[match_index, 19] if pd.notna(excel_df.iloc[match_index, 19]) else ""
                row[2] = excel_df.iloc[match_index, 20] if pd.notna(excel_df.iloc[match_index, 20]) else ""
                row[3] = excel_df.iloc[match_index, 22] if pd.notna(excel_df.iloc[match_index, 22]) else ""
                row[4] = excel_df.iloc[match_index, 26] if pd.notna(excel_df.iloc[match_index, 26]) else ""
                row[5] = excel_df.iloc[match_index, 28] if pd.notna(excel_df.iloc[match_index, 28]) else ""
                row[6] = excel_df.iloc[match_index, 30] if pd.notna(excel_df.iloc[match_index, 30]) else ""
                row[7] = excel_df.iloc[match_index, 31] if pd.notna(excel_df.iloc[match_index, 31]) else ""
                row[8] = excel_df.iloc[match_index, 32] if pd.notna(excel_df.iloc[match_index, 32]) else ""
                row[9] = excel_df.iloc[match_index, 33] if pd.notna(excel_df.iloc[match_index, 33]) else ""

                # 更新BGHS字段为匹配
                row[10] = "匹配"

                # 更新Excel中第BU列为匹配
                excel_df.iloc[match_index, bu_column_index] = "匹配"

                cursor.updateRow(row)

            else:
                # 如果没有匹配，则BGHS字段为不匹配，且第BU列更新为不匹配
                row[10] = "不匹配"
                # 更新BU列
                ctbh_index = excel_df.index[excel_df.iloc[:, 8] == ctbh_value].tolist()
                if ctbh_index:
                    excel_df.iloc[ctbh_index[0], bu_column_index] = "不匹配"
                
                cursor.updateRow(row)
                
    arcpy.AddMessage("CTBH挂接和字段更新完成")


# 函数：计算BGDLBM字段
def calculate_bgdlbm(feature_class):
    with arcpy.da.UpdateCursor(feature_class, ["BGGZJG", "LCSDLMC", "DLBM", "BGDLBM", "GJNYYPDL", "BGGZDL"]) as cursor:
        for row in cursor:
            bggzjg_value = row[0]  # 检查BGGZJG
            lcsdlmc_value = row[1]
            dlbm_value = row[2]
            gjn_dl_value = row[4]
            bggzdl_value = row[5]

            # 重置BGDLBM
            row[3] = ""  # 确保BGDLBM初始为空

            # 检查BGGZJG的值，并计算BGDLBM
            if bggzjg_value == "认定2023年“一上”成果":
                row[3] = dlbm_value if pd.notna(dlbm_value) else ""
            elif bggzjg_value == "认定林草湿成果":
                if lcsdlmc_value == "乔木林地":
                    row[3] = "0301"
                elif lcsdlmc_value == "竹林地":
                    row[3] = "0302"
                elif lcsdlmc_value == "灌木林地":
                    row[3] = "0305"
                else:
                    row[3] = "0307"
            elif bggzjg_value == "认定国家内业预判成果":
                row[3] = gjn_dl_value if pd.notna(gjn_dl_value) else ""
            elif bggzjg_value == "不认定":
                row[3] = bggzdl_value.split('-')[0] if pd.notna(bggzdl_value) else ""

            cursor.updateRow(row)
    arcpy.AddMessage("BGDLBM字段计算完成")

# 函数：计算BGHCYJ_GFX字段
def calculate_bg_hcyj_gfx(feature_class):
    with arcpy.da.UpdateCursor(feature_class, ["BGGZJG", "BGLYJG", "BGLYDL", "BGGZDL", "BGJZZT", "GJNYYPDL", "DLBM", "BGHCYJ_GFX","BGHS"]) as cursor:
        for row in cursor:
            bggzjg_value = row[0]  # BGGZJG
            bglyjg_value = row[1]  # BGLYJG
            bglydl_value = row[2]  # BGLYDL
            bggzdl_value = row[3]  # BGGZDL
            bgjzzt_value = row[4]  # BGJZZT
            gjn_yypdl_value = row[5]  # GJNYYPDL
            dlbm_value = row[6]  # DLBM
            bg_hcyj_gfx_value = ""  # 重置BGHCYJ_GFX
            bghs_value = row[8] if row[8] else ""  # 保持BGHS原有内容

            # 1. 检查不一致性
            if bggzjg_value != bglyjg_value or (bglydl_value and bglydl_value.strip() and bggzdl_value and bggzdl_value.strip() and bglydl_value != bggzdl_value):
                bg_hcyj_gfx_value += "两局认定结果填报不一致；"

            # 2. 外业图斑审查
            if bgjzzt_value == "已外业":
                if "外业图斑需线上审查" not in bg_hcyj_gfx_value:
                    bg_hcyj_gfx_value += "外业图斑需线上审查；"
                if "外业图斑需线上审查" not in bghs_value:
                    bghs_value += "；外业图斑需线上审查；"  
            elif bgjzzt_value == "未外业":
                 # 初始化前四位变量为空字符串，确保后续条件可以正常执行
                bggzdl_prefix = ""
                bglydl_prefix = ""

                # 检查 BGGZDL 和 BGLYDL 不为空，分别提取前4位
                if bggzdl_value and bggzdl_value.strip():
                    bggzdl_prefix = bggzdl_value[:4]
                if bglydl_value and bglydl_value.strip():
                    bglydl_prefix = bglydl_value[:4]

                # 进行条件检查
                if bggzjg_value == "认定国家内业预判成果":
                    if gjn_yypdl_value in ["QT", "ZY"]:
                        bg_hcyj_gfx_value += "平台上国家认定为QT或ZY未举证；"
                    elif (bggzdl_prefix and bggzdl_prefix.strip() and gjn_yypdl_value[:4] != bggzdl_prefix) or (bglydl_prefix and bglydl_prefix.strip() and gjn_yypdl_value[:4] != bglydl_prefix):
                        bg_hcyj_gfx_value += "平台上认定国家内业预判时，地类填报有误；"
                elif bggzjg_value == "不认定":
                    bg_hcyj_gfx_value += "未三选一且未举证，核实不认定是否填写准确、是否为三上地类；"
                elif bggzjg_value == "认定2023年“一上”成果":
                    if (bggzdl_prefix and bggzdl_prefix.strip() and dlbm_value[:4] != bggzdl_prefix) or (bglydl_prefix and bglydl_prefix.strip() and dlbm_value[:4] != bglydl_prefix):
                        bg_hcyj_gfx_value += "平台认定一上成果时，地类填报有误；"

            # 更新BGHCYJ_GFX字段和在BGHS加入需平台核查的外业图斑
            row[7] = bg_hcyj_gfx_value.strip()  # 去除末尾多余的分号
            row[8] = bghs_value.strip()  # 去除末尾多余的分号
            cursor.updateRow(row)
    arcpy.AddMessage("BGHCYJ_GFX字段计算完成和在BGHS加入外业图斑审查备注")

# 函数：检查PDYJ与系统选择一致性以及相关一致性检查
def update_bghcyj_gfx(feature_class):
    with arcpy.da.UpdateCursor(feature_class, ["BGDLBM", "HSDLBM", "BGHCYJ_GFX", "BGGZJG", "BGLYJG", "PDYJ", "DLBM", "BGHS", "BGJZZT", "TTQ", "BGGZSM"]) as cursor:
        for row in cursor:
            bgdlbm_value = row[0]  # BGDLBM
            hsd_lbm_value = row[1]  # HSDLBM
            bg_hcyj_gfx_value = row[2]  # BGHCYJ_GFX
            bggzjg_value = row[3]  # BGGZJG
            bglyjg_value = row[4]  # BGLYJG
            pdyj_value = row[5]  # PDYJ
            dlbm_value = row[6]  # DLBM
            bg_hs_value = row[7]  # BGHS
            bgjzzt_value = row[8]  # BGJZZT
            ttq_value = row[9]  # TTQ
            bggzsm_value = row[10]  # BGGZSM

            # 1. 检查HSDLBM是否与筛选的BGDLBM不一致
            if bgdlbm_value and bgdlbm_value not in ["QT", "ZY"] and bgdlbm_value.strip():
                if hsd_lbm_value and bgdlbm_value != hsd_lbm_value:
                    bg_hcyj_gfx_value += "HSDLBM与系统填报不一致；"
            
            # 2. 检查BGLYJG与BGGZJG一致的情况下，对PDYJ值进行判断
            if bglyjg_value == bggzjg_value:
                if bggzjg_value == "认定2023年“一上”成果" and pdyj_value not in ["2023年一上", "双方举证认定"]:
                    bg_hcyj_gfx_value += "PDYJ与系统选择不一致；"
                elif bggzjg_value == "认定国家内业预判成果" and pdyj_value not in ["国家内业预判", "双方举证认定"]:
                    bg_hcyj_gfx_value += "PDYJ与系统选择不一致；"
                elif bggzjg_value == "认定林草湿成果" and pdyj_value not in ["林草湿监测", "双方举证认定"]:
                    bg_hcyj_gfx_value += "PDYJ与系统选择不一致；"
                elif bggzjg_value == "不认定" and pdyj_value not in ["双方举证认定","2023年三上"]:
                    bg_hcyj_gfx_value += "PDYJ与系统选择不一致；"

            # 3. 检查DLBM不以'03%'开头，而HSDLBM以'03%'开头的情况
            if not dlbm_value.startswith("03") and hsd_lbm_value.startswith("03"):
                bg_hs_value += "林地流入图斑，需人工核查；"
            
            # 4. 筛选出PDYJ为“三上”的图斑，在BGHS内加入内容：认定为三上成果需人工核实
            if pdyj_value == "2023年三上":
                bg_hs_value += "认定为三上成果需人工核实；"
            
            # 5. 检查平台举证和PDYJ标注举证的一致性，更新BGHCYJ_GFX
            if (bgjzzt_value == "已外业" and pdyj_value != "双方举证认定") or (bgjzzt_value == "未外业" and pdyj_value == "双方举证认定"):
                bg_hcyj_gfx_value += "PDYJ举证标注与平台已举证不匹配；"
            
            # 6. 检查平台推土区是否按矢量备注
            if ttq_value == "TD" and (not bggzsm_value or bggzsm_value.strip() == ''):  # 检查TTQ字段是否为"TD",同时检查BGGZSM是否为空、空白或空格
                bg_hcyj_gfx_value += "矢量标注为推土、平台未备注；"

            # 更新BGHCYJ_GFX和BGHS
            row[2] = bg_hcyj_gfx_value
            row[7] = bg_hs_value
            cursor.updateRow(row)

    arcpy.AddMessage("BGHCYJ_GFX字段和BGHS字段更新完成")

# 函数：更新TJGJ和TJCTBH字段
def update_tjgj_and_tjctbh(feature_class):
    # 需要检核的字段列表
    required_fields = ["BGHCYJ_GFX", "HCYJ_GFX", "PDYJ", "PDYJ_JC", "BGHS", "TJGJ", "TJCTBH", "TBFGBZ"]

    # 检查字段是否存在于 feature_class 中
    existing_fields = [field.name for field in arcpy.ListFields(feature_class)]
    missing_fields = [field for field in required_fields if field not in existing_fields]
    
    # 如果有缺失的字段，输出提示并返回
    if missing_fields:
        messagebox.showerror(
            "字段缺失",
            f"字段 {', '.join(missing_fields)} 缺失。\n"
            "发现错误，请先运行检查插件：\n"
            "1. 检查BYZTB字段规范性并计算面积\n"
            "2. 是否符合三选一检查"
        )
        arcpy.AddMessage("字段缺失，程序终止。")

    # 如果所有字段存在，执行更新操作
    with arcpy.da.UpdateCursor(feature_class, required_fields) as cursor:
        for row in cursor:
            bg_hcyj_gfx_value = row[0]  # BGHCYJ_GFX
            hcyj_gfx_value = row[1]     # HCYJ_GFX
            pdyj_value = row[2]         # PDYJ
            pdyj_jc_value = row[3]      # PDYJ_JC
            bg_hs_value = row[4]        # BGHS
            tjgj_value = row[5]         # TJGJ
            tjctbh_value = row[6]       # TJCTBH
            tbfgbz_value = row[7]       # TBFGBZ

            # 1. 筛选条件检查
            if (not bg_hcyj_gfx_value or bg_hcyj_gfx_value.strip() == '') and (not hcyj_gfx_value or hcyj_gfx_value.strip() == '') and pdyj_value in ('2023年一上', '国家内业预判', '林草湿监测') and pdyj_jc_value == pdyj_value and bg_hs_value == '匹配':
                row[5] = "报国家批次一"  # 更新TJGJ字段

                # 更新TJCTBH字段
                if tbfgbz_value and tbfgbz_value.startswith("草图"):
                    try:
                        num = int(tbfgbz_value[-1])  # 获取数字部分
                        row[6] = str(num)  # 设置TJCTBH为数字
                    except (ValueError, IndexError):
                        row[6] = "1"  # 如果获取失败，默认设置为1
                else:
                    row[6] = "1"  # 如果为空或者不是草图，默认设置为1

            cursor.updateRow(row)

    arcpy.AddMessage("TJGJ和TJCTBH字段更新完成")


# 最后最后再导出数据到Excel表格
def export_to_excel(feature_class, output_location):
    # 定义输出Excel文件的名称
    output_excel_name = f"导出批量填报表格_{os.path.basename(feature_class)}.xlsx"
    output_excel_path = os.path.join(output_location, output_excel_name)

    # 使用arcpy的SearchCursor读取所有字段的数据
    fields = [f.name for f in arcpy.ListFields(feature_class)]
    data = []

    with arcpy.da.SearchCursor(feature_class, fields) as cursor:
        for row in cursor:
            data.append(row)

    # 创建DataFrame并保存为Excel文件
    df = pd.DataFrame(data, columns=fields)
    df.to_excel(output_excel_path, index=False)

    arcpy.AddMessage(f"所有数据已导出至Excel文件: {output_excel_path}")


# 主函数
def main():
    arcpy.AddMessage("脚本开始执行")

    # 用户选择输入矢量文件和Excel表格
    feature_class = arcpy.GetParameterAsText(0)
    excel_file = arcpy.GetParameterAsText(1)
    output_location = arcpy.GetParameterAsText(2)

    # 获取Excel中的所有Sheet名称
    sheet_names = pd.ExcelFile(excel_file).sheet_names
    sheet_name = arcpy.GetParameterAsText(3)  # 用户手动输入
    if sheet_name not in sheet_names:
        arcpy.AddError(f"选择的Sheet名称不在Excel文件中，请选择有效的Sheet名称: {sheet_names}")
        return

    # 读取指定Sheet的Excel文件
    excel_df = pd.read_excel(excel_file, sheet_name=sheet_name)

    # 设置第BU列的列索引 (假设BU列是第70列)
    bu_column_index = 70  # 将BU列的实际索引替换为你需要的索引值

    # 运行各个处理步骤
    add_fields(feature_class)
    calculate_ctbh(feature_class)
    match_and_update_fields(feature_class, excel_df, bu_column_index)  # 传入bu_column_index参数
    calculate_bgdlbm(feature_class)

    # 计算BGHCYJ_GFX字段
    calculate_bg_hcyj_gfx(feature_class)
    
    # 检查PDYJ与系统选择一致性以及相关一致性检查
    update_bghcyj_gfx(feature_class)

    # 更新TJGJ和TJCTBH字段
    update_tjgj_and_tjctbh(feature_class)

    # 输出结果
    output_name = os.path.splitext(os.path.basename(feature_class))[0] + "_JC.shp"
    output_path = os.path.join(output_location, output_name)
    arcpy.CopyFeatures_management(feature_class, output_path)
    arcpy.AddMessage(f"处理完成，结果输出至: {output_path}")

    # 保存Excel文件
    output_excel = os.path.join(output_location, "Updated_" + os.path.basename(excel_file))
    excel_df.to_excel(output_excel, index=False)
    arcpy.AddMessage(f"Excel文件更新完成，保存至: {output_excel}")

    # 最后最后导出所有数据到Excel
    export_to_excel(feature_class, output_location)


if __name__ == "__main__":
    main()