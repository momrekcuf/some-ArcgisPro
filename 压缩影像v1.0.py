#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
栅格导出工具 - 重构版
支持自定义像元大小和DEFLATE压缩
作者: GIS工具开发
版本: 0.1.0
"""

# ============================ 导入模块 ============================
import os
import sys
import arcpy
import tempfile
import shutil
import subprocess
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import traceback
import json
import importlib.util
import glob
import warnings
warnings.filterwarnings("ignore")

# ============================ GDAL管理器 ============================
class GDALManager:
    """GDAL管理器"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback or self._default_log
        self.gdal_path = None
        self.gdal_available = False
        self.gdal_python_available = False
        self.gdal_command_available = False
        
    def _default_log(self, message, level="INFO"):
        """默认日志函数"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def detect_gdal(self):
        """检测GDAL可用性"""
        self.log_message("开始检测GDAL...")
        
        # 检查Python GDAL包
        self.gdal_python_available = self._check_python_gdal()
        if self.gdal_python_available:
            self.log_message("✓ Python GDAL包可用", "SUCCESS")
        else:
            self.log_message("✗✗ Python GDAL包不可用", "WARNING")
        
        # 检查gdal_translate命令
        self.gdal_command_available, self.gdal_path = self._check_gdal_command()
        if self.gdal_command_available:
            self.log_message(f"✓ gdal_translate命令可用 ({self.gdal_path})", "SUCCESS")
        else:
            self.log_message("✗✗ gdal_translate命令不可用", "WARNING")
        
        # 总体检测结果
        self.gdal_available = self.gdal_python_available or self.gdal_command_available
        
        if self.gdal_available:
            self.log_message("✓ GDAL可用，支持DEFLATE压缩", "SUCCESS")
        else:
            self.log_message("✗✗ GDAL不可用，将使用ArcGIS压缩", "WARNING")
        
        return self.gdal_available
    
    def _check_python_gdal(self):
        """检查Python GDAL包"""
        try:
            spec = importlib.util.find_spec("osgeo")
            if spec is not None:
                from osgeo import gdal
                version = gdal.__version__
                self.log_message(f"  GDAL版本: {version}")
                return True
        except ImportError as e:
            self.log_message(f"  导入GDAL失败: {str(e)}")
        
        return False
    
    def _check_gdal_command(self):
        """检查gdal_translate命令"""
        # 检查常见安装位置
        import glob
        common_paths = [
            r"C:\Program Files\GDAL",
            r"C:\Program Files (x86)\GDAL",
            r"C:\OSGeo4W\bin",
            r"C:\OSGeo4W64\bin",
            r"C:\apps\gdal",
            os.path.join(os.path.dirname(sys.executable), "Library", "bin"),
            os.path.join(os.path.dirname(sys.executable), "Scripts"),
        ]
        
        # 检查这些路径
        for path in common_paths:
            expanded_paths = glob.glob(path)
            for expanded_path in expanded_paths:
                gdal_translate = os.path.join(expanded_path, "gdal_translate.exe")
                if os.path.exists(gdal_translate):
                    return True, expanded_path
        
        # 在PATH中查找
        try:
            result = subprocess.run(["where", "gdal_translate.exe"], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                gdal_path = os.path.dirname(result.stdout.strip().split('\n')[0])
                return True, gdal_path
        except:
            pass
        
        return False, None
    
    def get_gdal_translate_path(self):
        """获取gdal_translate路径"""
        if self.gdal_path and self.gdal_command_available:
            gdal_translate = os.path.join(self.gdal_path, "gdal_translate.exe")
            if os.path.exists(gdal_translate):
                return gdal_translate
        
        # 在PATH中查找
        try:
            result = subprocess.run(["where", "gdal_translate.exe"], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def log_message(self, message, level="INFO"):
        """记录日志消息"""
        self.log_callback(message, level)

# ============================ 可滚动框架 ============================
class ScrollableFrame(ttk.Frame):
    """可滚动的框架"""
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # 创建Canvas和滚动条
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        # 创建内部框架
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 绑定事件
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # 将内部框架添加到Canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # 配置Canvas
        self.canvas.configure(
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set
        )
        
        # 绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)
        
        # 布局
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 配置网格权重
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # 绑定配置事件
        self.scrollable_frame.bind("<Configure>", self._configure_canvas)
        self.canvas.bind("<Configure>", self._configure_canvas)
    
    def _configure_canvas(self, event=None):
        """配置Canvas大小"""
        # 更新滚动区域
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 确保内部框架至少和Canvas一样宽
        width = self.canvas.winfo_width()
        if width > 0:
            self.canvas.itemconfig(1, width=width)
    
    def _on_mousewheel(self, event):
        """鼠标滚轮垂直滚动"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_shift_mousewheel(self, event):
        """Shift+鼠标滚轮水平滚动"""
        self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")

# ============================ 栅格导出器 ============================
class RasterExporter:
    """栅格导出器"""
    
    def __init__(self, log_callback=None, gdal_manager=None):
        self.log_callback = log_callback or self._default_log
        self.gdal_manager = gdal_manager
        self.temp_dir = None
        
    def _default_log(self, message, level="INFO"):
        """默认日志函数"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def copy_temp_files_to_output(self, temp_dir, output_path, base_name):
        """
        将临时目录中的所有文件复制到输出目录，并按指定名称重命名
        
        参数:
        temp_dir: 临时目录路径
        output_path: 输出文件路径
        base_name: 输出文件的基础名称（不含扩展名）
        
        返回:
        bool: 是否成功
        """
        try:
            output_dir = os.path.dirname(output_path)
            output_base_name = os.path.splitext(os.path.basename(output_path))[0]
            
            self.log_callback(f"复制临时文件到输出目录...")
            self.log_callback(f"临时目录: {temp_dir}")
            self.log_callback(f"输出目录: {output_dir}")
            self.log_callback(f"输出基础名称: {output_base_name}")
            
            # 获取临时目录中的所有文件
            if not os.path.exists(temp_dir):
                self.log_callback(f"错误: 临时目录不存在: {temp_dir}", "ERROR")
                return False
            
            temp_files = glob.glob(os.path.join(temp_dir, "*"))
            if not temp_files:
                self.log_callback(f"警告: 临时目录中没有文件", "WARNING")
                return False
            
            self.log_callback(f"找到 {len(temp_files)} 个临时文件")
            
            # 确定主文件（通常是.tif文件）
            main_file = None
            for file_path in temp_files:
                if file_path.lower().endswith('.tif') or file_path.lower().endswith('.tiff'):
                    main_file = file_path
                    break
            
            if not main_file:
                # 如果没有找到.tif文件，使用第一个文件作为主文件
                main_file = temp_files[0]
                self.log_callback(f"未找到.tif文件，使用 {os.path.basename(main_file)} 作为主文件", "WARNING")
            
            # 复制所有文件到输出目录
            for file_path in temp_files:
                file_name = os.path.basename(file_path)
                
                # 确定新文件名
                if file_path == main_file:
                    # 主文件使用指定的输出名称
                    new_file_name = output_base_name + os.path.splitext(file_name)[1]
                else:
                    # 辅助文件保持与主文件的关联关系
                    temp_base_name = os.path.splitext(os.path.basename(main_file))[0]
                    if file_name.startswith(temp_base_name):
                        # 如果文件名以临时主文件名开头，替换为输出主文件名
                        new_file_name = file_name.replace(temp_base_name, output_base_name, 1)
                    else:
                        # 否则保持原文件名
                        new_file_name = file_name
                
                new_file_path = os.path.join(output_dir, new_file_name)
                
                try:
                    shutil.copy2(file_path, new_file_path)
                    self.log_callback(f"✓ 复制: {file_name} -> {new_file_name}")
                except Exception as e:
                    self.log_callback(f"✗✗ 复制失败 {file_name}: {str(e)}", "ERROR")
            
            self.log_callback("✓ 所有文件复制完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.log_callback(f"复制临时文件失败: {str(e)}", "ERROR")
            return False
    
    def export_raster(self, input_raster, output_path, **kwargs):
        """
        导出栅格
        
        参数:
        input_raster: 输入栅格路径
        output_path: 输出文件路径
        **kwargs: 其他参数
        
        返回:
        bool: 是否成功
        """
        start_time = time.time()
        
        try:
            # 解析参数
            cell_size_x = kwargs.get('cell_size_x')
            cell_size_y = kwargs.get('cell_size_y')
            compression_type = kwargs.get('compression_type', 'LZW').upper()
            compression_level = kwargs.get('compression_level', 6)
            predictor = kwargs.get('predictor', 2)
            tile_size = kwargs.get('tile_size', 256)
            resample_method = kwargs.get('resample_method', 'NEAREST')
            build_pyramids = kwargs.get('build_pyramids', True)
            calculate_stats = kwargs.get('calculate_stats', True)
            maintain_nodata = kwargs.get('maintain_nodata', True)
            use_temp_copy = kwargs.get('use_temp_copy', True)  # 新增参数：是否使用临时目录复制方式
            
            # 验证输入文件
            if not os.path.exists(input_raster):
                self.log_callback(f"错误: 输入栅格不存在: {input_raster}", "ERROR")
                return False
            
            # 创建输出目录
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self.log_callback(f"创建输出目录: {output_dir}")
            
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="raster_export_")
            self.log_callback(f"创建临时目录: {self.temp_dir}")
            
            # 步骤1: 处理重采样
            if cell_size_x is not None and cell_size_y is not None:
                self.log_callback(f"执行重采样: {cell_size_x} x {cell_size_y}")
                resampled_path = os.path.join(self.temp_dir, "resampled.tif")
                if not self._resample_raster(input_raster, resampled_path, 
                                           cell_size_x, cell_size_y, resample_method):
                    return False
                process_raster = resampled_path
            else:
                # 即使不重采样，也复制到临时目录以便统一处理
                temp_raster_path = os.path.join(self.temp_dir, "source.tif")
                try:
                    shutil.copy2(input_raster, temp_raster_path)
                    # 复制相关的辅助文件
                    base_name = os.path.splitext(input_raster)[0]
                    for ext in ['.tfw', '.aux.xml', '.ovr', '.rrd', '.prj', '.xml']:
                        aux_file = base_name + ext
                        if os.path.exists(aux_file):
                            shutil.copy2(aux_file, os.path.join(self.temp_dir, "source" + ext))
                except Exception as e:
                    self.log_callback(f"复制到临时目录失败: {str(e)}", "WARNING")
                    # 如果复制失败，直接使用原始文件
                    process_raster = input_raster
                else:
                    process_raster = temp_raster_path
            
            # 步骤2: 导出栅格
            self.log_callback(f"应用压缩: {compression_type}")
            
            if use_temp_copy:
                # 使用新的方式：直接复制临时目录中的所有文件
                self.log_callback("使用临时文件复制模式")
                
                # 对临时目录中的文件进行后处理（金字塔和统计信息）
                if build_pyramids or calculate_stats:
                    self.log_callback("对临时文件执行后处理...")
                    try:
                        arcpy.management.BuildPyramidsandStatistics(
                            in_raster_dataset=process_raster,
                            skip_existing=True,
                            build_pyramids=build_pyramids,
                            calculate_statistics=calculate_stats,
                            estimate_statistics=False
                        )
                        self.log_callback("临时文件后处理完成")
                    except Exception as e:
                        self.log_callback(f"临时文件后处理失败: {str(e)}", "WARNING")
                
                # 复制临时目录中的所有文件到输出目录
                success = self.copy_temp_files_to_output(self.temp_dir, output_path, 
                                                        os.path.splitext(os.path.basename(output_path))[0])
                
                if success:
                    # 验证输出文件
                    output_main_file = output_path
                    if not os.path.exists(output_main_file):
                        # 如果主文件不存在，检查是否有其他扩展名
                        tif_files = glob.glob(os.path.splitext(output_path)[0] + ".*")
                        if tif_files:
                            output_main_file = tif_files[0]
                    
                    if os.path.exists(output_main_file):
                        file_size = os.path.getsize(output_main_file)
                        self.log_callback(f"✓ 导出成功! 文件大小: {self.format_size(file_size)}", "SUCCESS")
                        return True
                    else:
                        self.log_callback("✗✗ 导出失败: 输出文件不存在", "ERROR")
                        return False
                else:
                    return False
                    
            else:
                # 原有的导出逻辑
                if compression_type == "DEFLATE":
                    # 检查GDAL是否可用
                    if self.gdal_manager and self.gdal_manager.gdal_available:
                        success = self._export_with_gdal(process_raster, output_path, 
                                                       compression_level, predictor, tile_size)
                    else:
                        self.log_callback("GDAL不可用，自动切换到LZW压缩", "WARNING")
                        success = self._export_with_arcgis(process_raster, output_path, 
                                                         "LZW", compression_level)
                else:
                    success = self._export_with_arcgis(process_raster, output_path, 
                                                     compression_type, compression_level)
                
                if success:
                    # 步骤3: 后处理
                    if build_pyramids or calculate_stats:
                        self.log_callback("执行后处理...")
                        self._postprocess_raster(output_path, build_pyramids, calculate_stats)
                    
                    return True
                else:
                    return False
                    
        except Exception as e:
            self.log_callback(f"导出过程中出错: {str(e)}", "ERROR")
            return False
        finally:
            # 清理临时文件
            self._cleanup_temp_files()
    
    def _resample_raster(self, input_raster, output_path, cell_size_x, cell_size_y, method):
        """重采样栅格"""
        try:
            # 验证重采样方法
            valid_methods = ["NEAREST", "BILINEAR", "CUBIC", "MAJORITY"]
            if method not in valid_methods:
                method = "NEAREST"
                self.log_callback(f"警告: 重采样方法无效，使用默认值: {method}", "WARNING")
            
            # 检查输入文件是否存在
            if not arcpy.Exists(input_raster):
                self.log_callback(f"错误: 输入文件无法访问: {input_raster}", "ERROR")
                return False
            
            arcpy.management.Resample(
                in_raster=input_raster,
                out_raster=output_path,
                cell_size=f"{cell_size_x} {cell_size_y}",
                resampling_type=method
            )
            return True
        except Exception as e:
            self.log_callback(f"重采样失败: {str(e)}", "ERROR")
            return False
    
    def _export_with_gdal(self, input_raster, output_path, compression_level, predictor, tile_size):
        """使用GDAL导出栅格"""
        try:
            # 获取gdal_translate路径
            gdal_translate = None
            if self.gdal_manager:
                gdal_translate = self.gdal_manager.get_gdal_translate_path()
            
            if gdal_translate and os.path.exists(gdal_translate):
                cmd = [gdal_translate, '-of', 'GTiff']
            else:
                cmd = ['gdal_translate', '-of', 'GTiff']
            
            # 添加压缩选项
            cmd.extend(['-co', f'COMPRESS=DEFLATE'])
            cmd.extend(['-co', f'ZLEVEL={compression_level}'])
            cmd.extend(['-co', f'PREDICTOR={predictor}'])
            cmd.extend(['-co', f'TILED=YES'])
            cmd.extend(['-co', f'BLOCKXSIZE={tile_size}'])
            cmd.extend(['-co', f'BLOCKYSIZE={tile_size}'])
            cmd.extend(['-co', 'BIGTIFF=IF_SAFER'])
            
            # 添加输入输出文件
            cmd.append(input_raster)
            cmd.append(output_path)
            
            self.log_callback(f"执行GDAL命令: {' '.join(cmd)}")
            
            # 执行命令
            env = os.environ.copy()
            if self.gdal_manager and self.gdal_manager.gdal_path:
                env['PATH'] = self.gdal_manager.gdal_path + ';' + env['PATH']
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, env=env)
            
            if result.returncode == 0:
                self.log_callback("✓ GDAL导出成功!", "SUCCESS")
                if result.stdout:
                    self.log_callback(f"GDAL输出: {result.stdout}")
                return True
            else:
                self.log_callback(f"✗✗ GDAL导出失败: {result.stderr}", "ERROR")
                return False
                
        except FileNotFoundError as e:
            self.log_callback("✗✗ 未找到gdal_translate命令", "ERROR")
            self.log_callback("请安装GDAL或设置正确的GDAL路径", "ERROR")
            return False
        except Exception as e:
            self.log_callback(f"✗✗ GDAL导出异常: {str(e)}", "ERROR")
            return False
    
    def _export_with_arcgis(self, input_raster, output_path, compression_type, compression_level):
        """使用ArcGIS导出栅格"""
        try:
            # 保存原始环境设置
            original_compression = arcpy.env.compression
            
            try:
                # 设置压缩环境
                if compression_type.upper() != "NONE":
                    if compression_type.upper() in ["LZW", "JPEG", "PACKBITS", "LZ77"]:
                        arcpy.env.compression = f"{compression_type.upper()}"
                        self.log_callback(f"使用ArcGIS {compression_type} 压缩")
                    else:
                        self.log_callback(f"警告: ArcGIS不支持{compression_type}压缩，使用LZW替代", "WARNING")
                        arcpy.env.compression = "LZW"
                
                # 检查输入文件
                if not arcpy.Exists(input_raster):
                    self.log_callback(f"错误: ArcGIS无法访问文件: {input_raster}", "ERROR")
                    return False
                
                # 导出栅格
                arcpy.management.CopyRaster(
                    in_raster=input_raster,
                    out_rasterdataset=output_path,
                    config_keyword="",
                    background_value=None,
                    nodata_value=None,
                    onebit_to_eightbit="NONE",
                    colormap_to_RGB="NONE",
                    pixel_type="32_BIT_FLOAT",
                    scale_pixel_value="NONE",
                    RGB_to_Colormap="NONE"
                )
                
                self.log_callback("✓ ArcGIS导出成功!", "SUCCESS")
                return True
                
            finally:
                # 恢复环境设置
                arcpy.env.compression = original_compression
                
        except Exception as e:
            self.log_callback(f"✗✗ ArcGIS导出失败: {str(e)}", "ERROR")
            return False
    
    def _postprocess_raster(self, raster_path, build_pyramids, calculate_stats):
        """后处理栅格"""
        try:
            if build_pyramids or calculate_stats:
                arcpy.management.BuildPyramidsandStatistics(
                    in_raster_dataset=raster_path,
                    skip_existing=True,
                    build_pyramids=build_pyramids,
                    calculate_statistics=calculate_stats,
                    estimate_statistics=False
                )
                self.log_callback("后处理完成")
        except Exception as e:
            self.log_callback(f"后处理失败: {str(e)}", "WARNING")
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                self.log_callback(f"清理临时目录: {self.temp_dir}")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            self.log_callback(f"清理临时文件失败: {str(e)}", "WARNING")

# ============================ 图形用户界面 ============================
class RasterExporterGUI:
    """带GUI的栅格导出工具"""
    
    def __init__(self):
        self.root = None
        self.main_frame = None
        self.scrollable_frame = None
        self.output_folder_var = None
        self.output_name_var = None
        self.input_file_var = None
        self.log_text = None
        self.progress_bar = None
        self.status_var = None
        self.stop_flag = False
        self.gdal_manager = GDALManager(log_callback=self.log_message)
        self.config_file = os.path.join(os.path.dirname(__file__), "raster_export_config.json")
        self.window_width = 1200
        self.window_height = 850
        self.min_width = 1000
        self.min_height = 700
        
    def run(self):
        """运行GUI"""
        self.root = tk.Tk()
        self.root.title("栅格导出工具 v4.0")
        
        # 设置窗口大小和最小大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算窗口位置（居中）
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        self.root.minsize(self.min_width, self.min_height)
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
        # 检查GDAL
        self.check_gdal_available()
        
        # 启动主循环
        self.root.mainloop()
    
    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定义样式
        style.configure("Title.TLabel", font=("Arial", 18, "bold"), foreground="#2c3e50")
        style.configure("Section.TLabel", font=("Arial", 12, "bold"), foreground="#34495e")
        style.configure("Status.TLabel", font=("Arial", 10), foreground="#7f8c8d")
        style.configure("Normal.TLabel", font=("Arial", 10))
        style.configure("Bold.TLabel", font=("Arial", 10, "bold"))
        
        # 按钮样式
        style.configure("Primary.TButton", font=("Arial", 11, "bold"), padding=10)
        style.configure("Success.TButton", font=("Arial", 11, "bold"), padding=10, foreground="green")
        style.configure("Danger.TButton", font=("Arial", 11, "bold"), padding=10, foreground="red")
        style.configure("Info.TButton", font=("Arial", 10), padding=8)
        
        # 输入框样式
        style.configure("Large.TEntry", font=("Arial", 10), padding=5)
        
        # 组合框样式
        style.configure("Large.TCombobox", font=("Arial", 10))
        
        # Checkbutton样式
        style.configure("Normal.TCheckbutton", font=("Arial", 10))
    
    def create_widgets(self):
        """创建界面控件"""
        # 创建可滚动的主框架
        self.main_frame = ScrollableFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 获取内部框架引用
        self.scrollable_frame = self.main_frame.scrollable_frame
        
        # 配置内部框架的网格权重
        for i in range(8):
            self.scrollable_frame.rowconfigure(i, weight=1 if i in [5] else 0)
        for i in range(3):
            self.scrollable_frame.columnconfigure(i, weight=1)
        
        # 标题
        title_label = ttk.Label(self.scrollable_frame, text="栅格导出工具", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="n")
        
        # GDAL状态显示
        self.gdal_status_var = tk.StringVar(value="正在检测GDAL...")
        tk.Label(self.scrollable_frame, textvariable=self.gdal_status_var, 
                foreground="blue", font=("Arial", 10, "bold")).grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky="w")
        
        # 文件选择部分
        self.create_file_selection_section(row=2)
        
        # 像元大小部分
        self.create_cell_size_section(row=3, column=0)
        
        # 压缩设置部分
        self.create_compression_section(row=3, column=1)
        
        # 其他选项部分
        self.create_options_section(row=3, column=2)
        
        # GDAL管理部分
        self.create_gdal_section(row=4)
        
        # 日志输出
        self.create_log_section(row=5)
        
        # 状态栏
        self.create_status_bar(row=6)
        
        # 按钮栏
        self.create_button_bar(row=7)
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始日志
        self.log_message("=" * 80)
        self.log_message("栅格导出工具 v4.0")
        self.log_message("=" * 80)
        self.log_message("就绪，请选择输入栅格文件...")
    
    def create_file_selection_section(self, row):
        """创建文件选择部分"""
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="文件选择", padding=15)
        file_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(0, 15))
        
        # 输入文件
        ttk.Label(file_frame, text="输入栅格文件:", style="Normal.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.input_file_var = tk.StringVar()
        input_frame = ttk.Frame(file_frame)
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        input_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(input_frame, textvariable=self.input_file_var, style="Large.TEntry").grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(input_frame, text="浏览...", command=self.browse_input_file, style="Info.TButton", width=10).grid(row=0, column=1, sticky="e")
        
        # 文件信息显示
        self.file_info_var = tk.StringVar(value="")
        tk.Label(file_frame, textvariable=self.file_info_var, foreground="blue", font=("Arial", 9)).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 12))
        
        # 输出文件夹
        ttk.Label(file_frame, text="输出文件夹:", style="Normal.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 8))
        self.output_folder_var = tk.StringVar(value="")
        output_folder_frame = ttk.Frame(file_frame)
        output_folder_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        output_folder_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(output_folder_frame, textvariable=self.output_folder_var, style="Large.TEntry").grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(output_folder_frame, text="浏览...", command=self.browse_output_folder, style="Info.TButton", width=10).grid(row=0, column=1, sticky="e")
        
        # 输出文件名
        ttk.Label(file_frame, text="输出文件名 (不含扩展名):", style="Normal.TLabel").grid(row=5, column=0, sticky="w", pady=(0, 8))
        self.output_name_var = tk.StringVar(value="exported_raster")
        ttk.Entry(file_frame, textvariable=self.output_name_var, style="Large.TEntry", width=30).grid(row=6, column=0, sticky="w", pady=(0, 10))
    
    def create_cell_size_section(self, row, column):
        """创建像元大小部分"""
        cell_frame = ttk.LabelFrame(self.scrollable_frame, text="像元大小设置", padding=15)
        cell_frame.grid(row=row, column=column, sticky="nsew", padx=(0, 10), pady=(0, 15))
        
        ttk.Label(cell_frame, text="X像元大小:", style="Normal.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.cell_size_x_var = tk.StringVar()
        ttk.Entry(cell_frame, textvariable=self.cell_size_x_var, style="Large.TEntry", width=15).grid(row=1, column=0, sticky="w", pady=(0, 10))
        
        ttk.Label(cell_frame, text="Y像元大小:", style="Normal.TLabel").grid(row=0, column=1, sticky="w", padx=(20, 0), pady=(0, 8))
        self.cell_size_y_var = tk.StringVar()
        ttk.Entry(cell_frame, textvariable=self.cell_size_y_var, style="Large.TEntry", width=15).grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(0, 10))
        
        ttk.Button(cell_frame, text="获取原始大小", command=self.get_original_cell_size, style="Info.TButton", width=15).grid(row=2, column=0, columnspan=2, pady=(8, 0))
    
    def create_compression_section(self, row, column):
        """创建压缩设置部分"""
        comp_frame = ttk.LabelFrame(self.scrollable_frame, text="压缩设置", padding=15)
        comp_frame.grid(row=row, column=column, sticky="nsew", padx=(0, 10), pady=(0, 15))
        
        ttk.Label(comp_frame, text="压缩类型:", style="Normal.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.compression_type_var = tk.StringVar(value="LZW")
        compression_combo = ttk.Combobox(comp_frame, textvariable=self.compression_type_var, 
                                       values=["LZW", "DEFLATE", "JPEG", "PACKBITS", "LZ77", "NONE"], 
                                       width=15, state="readonly", style="Large.TCombobox")
        compression_combo.grid(row=1, column=0, sticky="w", pady=(0, 10))
        compression_combo.bind("<<ComboboxSelected>>", self.on_compression_type_changed)
        
        ttk.Label(comp_frame, text="压缩级别 (1-9):", style="Normal.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.compression_level_var = tk.IntVar(value=6)
        ttk.Spinbox(comp_frame, from_=1, to=9, textvariable=self.compression_level_var, 
                   width=5, font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=(0, 10))
        
        ttk.Label(comp_frame, text="分块大小:", style="Normal.TLabel").grid(row=0, column=1, sticky="w", padx=(20, 0), pady=(0, 8))
        self.tile_size_var = tk.IntVar(value=256)
        tile_size_combo = ttk.Combobox(comp_frame, textvariable=self.tile_size_var, 
                                      values=[128, 256, 512, 1024], width=10, state="readonly", style="Large.TCombobox")
        tile_size_combo.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(0, 10))
        
        ttk.Label(comp_frame, text="预测器:", style="Normal.TLabel").grid(row=2, column=1, sticky="w", padx=(20, 0), pady=(0, 8))
        self.predictor_var = tk.StringVar(value="水平差分")
        predictor_combo = ttk.Combobox(comp_frame, textvariable=self.predictor_var, 
                                     values=["无", "水平差分", "浮点"], width=10, state="readonly", style="Large.TCombobox")
        predictor_combo.grid(row=3, column=1, sticky="w", padx=(20, 0), pady=(0, 10))
        
        # 重采样方法
        ttk.Label(comp_frame, text="重采样方法:", style="Normal.TLabel").grid(row=4, column=0, sticky="w", pady=(12, 8))
        self.resample_method_var = tk.StringVar(value="NEAREST")
        resample_combo = ttk.Combobox(comp_frame, textvariable=self.resample_method_var, 
                                    values=["NEAREST", "BILINEAR", "CUBIC", "MAJORITY"], 
                                    width=15, state="readonly", style="Large.TCombobox")
        resample_combo.grid(row=5, column=0, sticky="w", pady=(0, 5))
    
    def create_options_section(self, row, column):
        """创建其他选项部分"""
        options_frame = ttk.LabelFrame(self.scrollable_frame, text="其他选项", padding=15)
        options_frame.grid(row=row, column=column, sticky="nsew", pady=(0, 15))
        
        self.build_pyramids_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="构建金字塔", variable=self.build_pyramids_var, 
                       style="Normal.TCheckbutton").grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        self.calculate_stats_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="计算统计信息", variable=self.calculate_stats_var, 
                       style="Normal.TCheckbutton").grid(row=1, column=0, sticky="w", pady=(0, 8))
        
        self.maintain_nodata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="保持NoData值", variable=self.maintain_nodata_var, 
                       style="Normal.TCheckbutton").grid(row=2, column=0, sticky="w", pady=(0, 8))
        
        # 新增：使用临时文件复制模式选项
        self.use_temp_copy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="使用临时文件复制模式", variable=self.use_temp_copy_var, 
                       style="Normal.TCheckbutton").grid(row=3, column=0, sticky="w", pady=(12, 8))
        
        ttk.Label(options_frame, text="输出格式:", style="Normal.TLabel").grid(row=4, column=0, sticky="w", pady=(12, 8))
        self.output_format_var = tk.StringVar(value="TIFF")
        format_combo = ttk.Combobox(options_frame, textvariable=self.output_format_var, 
                                  values=["TIFF", "IMG", "JPEG2000", "PNG", "JPEG"], 
                                  width=10, state="readonly", style="Large.TCombobox")
        format_combo.grid(row=5, column=0, sticky="w", pady=(0, 5))
    
    def create_gdal_section(self, row):
        """创建GDAL管理部分"""
        gdal_frame = ttk.LabelFrame(self.scrollable_frame, text="GDAL管理", padding=10)
        gdal_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        button_frame = ttk.Frame(gdal_frame)
        button_frame.grid(row=0, column=0, sticky="w", pady=(5, 0))
        
        ttk.Button(button_frame, text="检测GDAL", command=self.check_gdal_available, 
                  style="Info.TButton").grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        ttk.Button(button_frame, text="安装GDAL", command=self.install_gdal, 
                  style="Info.TButton").grid(row=0, column=1, sticky="w", padx=(0, 10))
        
        ttk.Button(button_frame, text="GDAL安装指南", command=self.show_gdal_guide, 
                  style="Info.TButton").grid(row=0, column=2, sticky="w")
    
    def create_log_section(self, row):
        """创建日志输出部分"""
        log_frame = ttk.LabelFrame(self.scrollable_frame, text="日志输出", padding=10)
        log_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(0, 15))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=120, font=("Consolas", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # 添加标签颜色
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
    
    def create_status_bar(self, row):
        """创建状态栏"""
        status_frame = ttk.Frame(self.scrollable_frame)
        status_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        
        # 进度条
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate', length=300)
        self.progress_bar.pack(side="right", padx=(10, 0))
    
    def create_button_bar(self, row):
        """创建按钮栏"""
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(button_frame, text="导出栅格", command=self.start_export, 
                  style="Primary.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(button_frame, text="停止", command=self.stop_export, 
                  style="Danger.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(button_frame, text="清空日志", command=self.clear_log, 
                  style="Info.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(button_frame, text="测试文件", command=self.test_raster_file, 
                  style="Info.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(button_frame, text="退出", command=self.root.quit, 
                  style="Info.TButton").pack(side="left")
    
    # ======================= 工具方法 =======================
    def browse_input_file(self):
        """浏览输入文件"""
        filetypes = [
            ("栅格文件", "*.tif;*.tiff;*.img;*.jpg;*.jpeg;*.png;*.jp2;*.bmp;*.gif"),
            ("TIFF文件", "*.tif;*.tiff"),
            ("IMG文件", "*.img"),
            ("JPEG文件", "*.jpg;*.jpeg"),
            ("PNG文件", "*.png"),
            ("所有文件", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="选择输入栅格文件",
            filetypes=filetypes
        )
        
        if filename:
            self.input_file_var.set(filename)
            self.log_message(f"已选择输入文件: {filename}")
            self.display_file_info(filename)
    
    def display_file_info(self, filename):
        """显示文件信息"""
        try:
            if not os.path.exists(filename):
                self.file_info_var.set("文件不存在")
                return
            
            file_size = os.path.getsize(filename)
            size_str = self.format_size(file_size)
            file_ext = os.path.splitext(filename)[1].lower()
            
            try:
                if arcpy.Exists(filename):
                    desc = arcpy.Describe(filename)
                    if hasattr(desc, 'width') and hasattr(desc, 'height'):
                        width = desc.width
                        height = desc.height
                        info_str = f"大小: {size_str} | 尺寸: {width}×{height} | 格式: {file_ext}"
                    else:
                        info_str = f"大小: {size_str} | 格式: {file_ext}"
                else:
                    info_str = f"大小: {size_str} | 格式: {file_ext}"
            except:
                info_str = f"大小: {size_str} | 格式: {file_ext}"
            
            self.file_info_var.set(info_str)
            
        except Exception as e:
            self.file_info_var.set(f"文件: {os.path.basename(filename)}")
    
    def browse_output_folder(self):
        """浏览输出文件夹"""
        foldername = filedialog.askdirectory(title="选择输出文件夹")
        
        if foldername:
            self.output_folder_var.set(foldername)
            self.log_message(f"已选择输出文件夹: {foldername}")
    
    def get_original_cell_size(self):
        """获取原始栅格的像元大小"""
        input_file = self.input_file_var.get()
        
        if not input_file or not os.path.exists(input_file):
            self.log_message("请先选择输入栅格文件", "WARNING")
            return
        
        try:
            self.log_message(f"尝试读取文件: {input_file}")
            
            # 方法1: 尝试使用arcpy.Raster
            try:
                raster = arcpy.Raster(input_file)
                if hasattr(raster, 'meanCellWidth') and hasattr(raster, 'meanCellHeight'):
                    cell_x = raster.meanCellWidth
                    cell_y = raster.meanCellHeight
                    
                    self.cell_size_x_var.set(f"{cell_x:.6f}")
                    self.cell_size_y_var.set(f"{cell_y:.6f}")
                    
                    self.log_message(f"✓ 获取像元大小: {cell_x:.6f} x {cell_y:.6f}", "SUCCESS")
                    self.log_message(f"  图像尺寸: {raster.width} x {raster.height}")
                    return
            except Exception as e1:
                self.log_message(f"arcpy.Raster方法失败: {str(e1)[:100]}", "WARNING")
            
            # 方法2: 尝试使用arcpy.Describe
            try:
                if arcpy.Exists(input_file):
                    desc = arcpy.Describe(input_file)
                    if hasattr(desc, 'meanCellWidth') and hasattr(desc, 'meanCellHeight'):
                        cell_x = desc.meanCellWidth
                        cell_y = desc.meanCellHeight
                        
                        self.cell_size_x_var.set(f"{cell_x:.6f}")
                        self.cell_size_y_var.set(f"{cell_y:.6f}")
                        
                        self.log_message(f"✓ 获取像元大小: {cell_x:.6f} x {cell_y:.6f}", "SUCCESS")
                        if hasattr(desc, 'width'):
                            self.log_message(f"  图像尺寸: {desc.width} x {desc.height}")
                        return
            except Exception as e2:
                self.log_message(f"arcpy.Describe方法失败: {str(e2)[:100]}", "WARNING")
            
            self.log_message("无法获取像元大小信息", "WARNING")
            
        except Exception as e:
            self.log_message(f"获取像元大小失败: {str(e)}", "ERROR")
    
    def test_raster_file(self):
        """测试栅格文件是否可读"""
        input_file = self.input_file_var.get()
        
        if not input_file or not os.path.exists(input_file):
            messagebox.showwarning("警告", "请先选择输入栅格文件")
            return
        
        self.log_message(f"\n测试文件: {input_file}")
        
        # 测试方法1: arcpy.Raster
        self.log_message("测试1: 使用arcpy.Raster...")
        try:
            raster = arcpy.Raster(input_file)
            self.log_message(f"  ✓ 成功创建arcpy.Raster对象", "SUCCESS")
            self.log_message(f"    宽度: {raster.width if hasattr(raster, 'width') else 'N/A'}")
            self.log_message(f"    高度: {raster.height if hasattr(raster, 'height') else 'N/A'}")
            if hasattr(raster, 'meanCellWidth'):
                self.log_message(f"    像元宽度: {raster.meanCellWidth}")
            if hasattr(raster, 'meanCellHeight'):
                self.log_message(f"    像元高度: {raster.meanCellHeight}")
            if hasattr(raster, 'bandCount'):
                self.log_message(f"    波段数: {raster.bandCount}")
        except Exception as e:
            self.log_message(f"  ✗✗ arcpy.Raster失败: {str(e)[:100]}", "ERROR")
        
        # 测试方法2: arcpy.Describe
        self.log_message("测试2: 使用arcpy.Describe...")
        try:
            if arcpy.Exists(input_file):
                desc = arcpy.Describe(input_file)
                self.log_message(f"  ✓ 成功创建arcpy.Describe对象", "SUCCESS")
                self.log_message(f"    数据类型: {desc.dataType}")
                self.log_message(f"    格式: {desc.format if hasattr(desc, 'format') else 'N/A'}")
                if hasattr(desc, 'width'):
                    self.log_message(f"    宽度: {desc.width}")
                if hasattr(desc, 'height'):
                    self.log_message(f"    高度: {desc.height}")
            else:
                self.log_message(f"  ✗✗ arcpy.Exists返回False", "ERROR")
        except Exception as e:
            self.log_message(f"  ✗✗ arcpy.Describe失败: {str(e)[:100]}", "ERROR")
        
        self.log_message("文件测试完成")
    
    def check_gdal_available(self):
        """检查GDAL是否可用"""
        self.log_message("开始检测GDAL...")
        
        def detect_in_thread():
            try:
                gdal_available = self.gdal_manager.detect_gdal()
                
                if gdal_available:
                    self.gdal_status_var.set("✓ GDAL可用，支持DEFLATE压缩")
                else:
                    self.gdal_status_var.set("✗✗ GDAL不可用，将使用ArcGIS压缩")
            except Exception as e:
                self.log_message(f"GDAL检测失败: {str(e)}", "ERROR")
                self.gdal_status_var.set("✗✗ GDAL检测失败")
        
        thread = threading.Thread(target=detect_in_thread)
        thread.daemon = True
        thread.start()
    
    def install_gdal(self):
        """安装GDAL"""
        self.log_message("开始安装GDAL...")
        
        # 禁用按钮
        self.update_buttons_state(False)
        self.status_var.set("正在安装GDAL...")
        self.progress_bar.start(10)
        
        def install_in_thread():
            try:
                import subprocess
                python_path = sys.executable
                
                # 构建pip命令
                pip_cmd = [python_path, "-m", "pip", "install", "GDAL", "--upgrade"]
                self.log_message(f"执行命令: {' '.join(pip_cmd)}")
                
                result = subprocess.run(pip_cmd, capture_output=True, text=True, shell=True, timeout=120)
                
                if result.returncode == 0:
                    if "already satisfied" in result.stdout.lower():
                        self.log_message("✓ GDAL已安装", "SUCCESS")
                    else:
                        self.log_message("✓ GDAL安装成功", "SUCCESS")
                    
                    # 重新检测
                    self.gdal_manager.detect_gdal()
                    self.gdal_status_var.set("✓ GDAL已安装并可用")
                    
                    messagebox.showinfo("成功", "GDAL安装成功！")
                else:
                    error_msg = result.stderr or result.stdout
                    self.log_message(f"✗✗ GDAL安装失败: {error_msg[:200]}", "ERROR")
                    messagebox.showwarning("警告", "GDAL安装失败，请查看日志获取详细信息。")
                
            except subprocess.TimeoutExpired:
                self.log_message("✗✗ GDAL安装超时", "ERROR")
                messagebox.showerror("错误", "GDAL安装超时")
            except Exception as e:
                self.log_message(f"✗✗ GDAL安装异常: {str(e)}", "ERROR")
                messagebox.showerror("错误", f"GDAL安装失败: {str(e)}")
            finally:
                # 恢复按钮状态
                self.update_buttons_state(True)
                self.status_var.set("就绪")
                self.progress_bar.stop()
        
        thread = threading.Thread(target=install_in_thread)
        thread.daemon = True
        thread.start()
    
    def show_gdal_guide(self):
        """显示GDAL安装指南"""
        guide_text = """
GDAL安装指南：

1. 自动安装（推荐）：
   - 点击"安装GDAL"按钮
   - 工具会自动在ArcGIS Pro环境中安装GDAL
   - 安装过程需要几分钟时间

2. 手动安装：
   a. 打开ArcGIS Pro的Python包管理器
   b. 搜索"GDAL"并安装
   
   或者在ArcGIS Pro的Python窗口中运行：
   import subprocess
   import sys
   python_path = sys.executable
   subprocess.run([python_path, "-m", "pip", "install", "GDAL"])

3. 通过conda安装：
   - 打开ArcGIS Pro的Python命令行
   - 运行: conda install -c conda-forge gdal

安装后，请点击"检测GDAL"按钮验证安装。
        """
        
        guide_window = tk.Toplevel(self.root)
        guide_window.title("GDAL安装指南")
        guide_window.geometry("700x450")
        
        text_widget = scrolledtext.ScrolledText(guide_window, wrap=tk.WORD, width=80, height=25, font=("Consolas", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, guide_text)
        text_widget.configure(state='disabled')
        
        ttk.Button(guide_window, text="关闭", command=guide_window.destroy, style="Info.TButton").pack(pady=10)
    
    def on_compression_type_changed(self, event=None):
        """压缩类型改变事件"""
        compression_type = self.compression_type_var.get()
        
        if compression_type == "DEFLATE":
            if not self.gdal_manager.gdal_available:
                self.log_message("警告: GDAL不可用，DEFLATE压缩将不可用", "WARNING")
                response = messagebox.askyesno("GDAL不可用", 
                    "未找到GDAL，无法使用DEFLATE压缩。\n是否切换为LZW压缩？")
                if response:
                    self.compression_type_var.set("LZW")
    
    def start_export(self):
        """开始导出"""
        if not self.validate_inputs():
            return
        
        # 检查压缩类型和GDAL
        compression_type = self.compression_type_var.get()
        if compression_type == "DEFLATE" and not self.gdal_manager.gdal_available:
            response = messagebox.askyesno("GDAL不可用", 
                "未找到GDAL，无法使用DEFLATE压缩。\n是否使用LZW压缩替代？")
            if response:
                self.compression_type_var.set("LZW")
            else:
                self.log_message("导出已取消", "WARNING")
                return
        
        # 禁用导出按钮，启用停止按钮
        self.update_buttons_state(False)
        
        # 启动进度条
        self.progress_bar.start(10)
        self.status_var.set("正在导出...")
        
        # 在新线程中执行导出
        self.stop_flag = False
        export_thread = threading.Thread(target=self.export_raster_thread)
        export_thread.daemon = True
        export_thread.start()
    
    def stop_export(self):
        """停止导出"""
        self.stop_flag = True
        self.status_var.set("正在停止...")
        self.log_message("正在停止导出操作...", "WARNING")
    
    def export_raster_thread(self):
        """导出栅格的线程函数"""
        try:
            # 收集参数
            input_raster = self.input_file_var.get()
            output_folder = self.output_folder_var.get()
            output_name = self.output_name_var.get()
            output_format = self.output_format_var.get()
            
            # 确定输出路径
            format_extensions = {
                "TIFF": ".tif",
                "IMG": ".img",
                "JPEG2000": ".jp2",
                "PNG": ".png",
                "JPEG": ".jpg"
            }
            
            extension = format_extensions.get(output_format, ".tif")
            output_path = os.path.join(output_folder, f"{output_name}{extension}")
            
            # 检查文件是否已存在
            if os.path.exists(output_path):
                response = messagebox.askyesno("确认", f"文件 {output_path} 已存在，是否覆盖？")
                if not response:
                    self.log_message("导出已取消", "WARNING")
                    self.on_export_complete(False)
                    return
            
            # 解析像元大小
            cell_size_x = None
            cell_size_y = None
            
            try:
                cell_size_x_str = self.cell_size_x_var.get()
                cell_size_y_str = self.cell_size_y_var.get()
                
                if cell_size_x_str and cell_size_x_str.strip():
                    cell_size_x = float(cell_size_x_str)
                if cell_size_y_str and cell_size_y_str.strip():
                    cell_size_y = float(cell_size_y_str)
            except ValueError as e:
                self.log_message(f"像元大小格式错误: {str(e)}", "ERROR")
                cell_size_x = None
                cell_size_y = None
            
            # 解析其他参数
            compression_type = self.compression_type_var.get()
            compression_level = self.compression_level_var.get()
            tile_size = self.tile_size_var.get()
            predictor = self.predictor_var.get()
            resample_method = self.resample_method_var.get()
            build_pyramids = self.build_pyramids_var.get()
            calculate_stats = self.calculate_stats_var.get()
            maintain_nodata = self.maintain_nodata_var.get()
            use_temp_copy = self.use_temp_copy_var.get()
            
            # 映射预测器值
            predictor_map = {"无": 1, "水平差分": 2, "浮点": 3}
            predictor_value = predictor_map.get(predictor, 2)
            
            # 显示导出参数
            self.log_message("=" * 80)
            self.log_message("开始导出栅格...")
            self.log_message(f"输入文件: {input_raster}")
            self.log_message(f"输出文件: {output_path}")
            
            if cell_size_x and cell_size_y:
                self.log_message(f"像元大小: {cell_size_x} x {cell_size_y}")
            else:
                self.log_message("像元大小: 使用原始大小")
            
            self.log_message(f"压缩设置: {compression_type} (级别: {compression_level})")
            self.log_message(f"重采样方法: {resample_method}")
            self.log_message(f"临时文件复制模式: {'启用' if use_temp_copy else '禁用'}")
            self.log_message("-" * 40)
            
            # 创建导出器
            exporter = RasterExporter(
                log_callback=self.log_message,
                gdal_manager=self.gdal_manager
            )
            
            # 检查停止标志
            if self.stop_flag:
                self.log_message("导出被用户取消", "WARNING")
                self.on_export_complete(False)
                return
            
            # 执行导出
            start_time = time.time()
            
            success = exporter.export_raster(
                input_raster=input_raster,
                output_path=output_path,
                cell_size_x=cell_size_x,
                cell_size_y=cell_size_y,
                resample_method=resample_method,
                compression_type=compression_type,
                compression_level=compression_level,
                predictor=predictor_value,
                tile_size=tile_size,
                build_pyramids=build_pyramids,
                calculate_stats=calculate_stats,
                maintain_nodata=maintain_nodata,
                use_temp_copy=use_temp_copy
            )
            
            elapsed_time = time.time() - start_time
            
            if success:
                # 检查输出目录中的文件
                output_dir = os.path.dirname(output_path)
                output_base_name = os.path.splitext(os.path.basename(output_path))[0]
                
                # 查找所有输出文件
                output_files = []
                for ext in ['.tif', '.tiff', '.tfw', '.aux.xml', '.ovr', '.rrd', '.prj', '.xml', '.jpg', '.png', '.jp2', '.img']:
                    pattern = os.path.join(output_dir, f"{output_base_name}*{ext}")
                    files = glob.glob(pattern)
                    output_files.extend(files)
                
                if output_files:
                    total_size = 0
                    for file_path in output_files:
                        if os.path.exists(file_path):
                            total_size += os.path.getsize(file_path)
                    
                    self.log_message(f"✓ 导出成功! 耗时: {elapsed_time:.1f}秒", "SUCCESS")
                    self.log_message(f"  生成文件数: {len(output_files)}")
                    self.log_message(f"  总文件大小: {exporter.format_size(total_size)}")
                    
                    # 显示生成的文件列表
                    self.log_message("  生成的文件:")
                    for file_path in output_files:
                        file_size = os.path.getsize(file_path)
                        file_name = os.path.basename(file_path)
                        self.log_message(f"    - {file_name} ({exporter.format_size(file_size)})")
                    
                    if messagebox.askyesno("成功", f"导出完成!\n生成文件数: {len(output_files)}\n总大小: {exporter.format_size(total_size)}\n\n是否打开输出文件夹？"):
                        self.open_output_folder(output_dir)
                else:
                    self.log_message("导出完成，但未找到输出文件", "WARNING")
            else:
                self.log_message("✗✗ 导出失败!", "ERROR")
            
            self.log_message("=" * 80)
            
            # 更新UI
            self.on_export_complete(success)
            
        except Exception as e:
            self.log_message(f"导出过程中发生错误: {str(e)}", "ERROR")
            self.log_message(traceback.format_exc(), "ERROR")
            self.on_export_complete(False)
    
    def on_export_complete(self, success):
        """导出完成处理"""
        # 停止进度条
        self.progress_bar.stop()
        
        # 更新状态
        if success:
            self.status_var.set("导出完成")
        else:
            self.status_var.set("导出失败")
        
        # 启用/禁用按钮
        self.update_buttons_state(True)
        
        # 重置停止标志
        self.stop_flag = False
    
    def update_buttons_state(self, enabled):
        """更新按钮状态"""
        # 这里简化处理，实际应用中应该获取具体的按钮引用
        # 由于界面控件较多，这里只做基本的状态更新
        self.root.update_idletasks()
    
    def validate_inputs(self):
        """验证输入"""
        # 检查输入文件
        input_file = self.input_file_var.get()
        if not input_file:
            messagebox.showerror("错误", "请选择输入栅格文件")
            return False
        
        if not os.path.exists(input_file):
            messagebox.showerror("错误", f"输入文件不存在:\n{input_file}")
            return False
        
        # 检查输出文件夹
        output_folder = self.output_folder_var.get()
        if not output_folder:
            messagebox.showerror("错误", "请选择输出文件夹")
            return False
        
        # 检查输出文件名
        output_name = self.output_name_var.get()
        if not output_name:
            messagebox.showerror("错误", "请输入输出文件名")
            return False
        
        # 检查像元大小
        try:
            cell_x_str = self.cell_size_x_var.get()
            cell_y_str = self.cell_size_y_var.get()
            
            if cell_x_str and cell_x_str.strip() and cell_y_str and cell_y_str.strip():
                cell_x = float(cell_x_str)
                cell_y = float(cell_y_str)
                
                if cell_x <= 0 or cell_y <= 0:
                    messagebox.showerror("错误", "像元大小必须大于0")
                    return False
        except ValueError:
            if cell_x_str and cell_x_str.strip() and cell_y_str and cell_y_str.strip():
                messagebox.showerror("错误", "像元大小必须是有效的数字")
                return False
        
        # 检查压缩级别
        try:
            comp_level = self.compression_level_var.get()
            if comp_level < 1 or comp_level > 9:
                messagebox.showerror("错误", "压缩级别必须在1-9之间")
                return False
        except:
            pass
        
        return True
    
    def open_output_folder(self, folder_path):
        """打开输出文件夹"""
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            self.log_message(f"无法打开文件夹: {str(e)}", "WARNING")
    
    def log_message(self, message, level="INFO"):
        """记录日志消息"""
        if not self.log_text:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "ERROR":
            tag = "error"
            prefix = f"[{timestamp}] [错误] "
        elif level == "WARNING":
            tag = "warning"
            prefix = f"[{timestamp}] [警告] "
        elif level == "SUCCESS":
            tag = "success"
            prefix = f"[{timestamp}] [成功] "
        else:
            tag = "info"
            prefix = f"[{timestamp}] "
        
        self.log_text.insert(tk.END, prefix + message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()
    
    def clear_log(self):
        """清空日志"""
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
    
    def on_closing(self):
        """关闭窗口事件"""
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self.root.quit()
            self.root.destroy()
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

# ============================ 主函数 ============================
def main():
    """主函数"""
    # 检查ArcGIS环境
    try:
        import arcpy
        print("ArcGIS环境检测成功")
    except ImportError as e:
        print(f"警告: 未找到ArcPy库: {str(e)}")
        print("请确保在ArcGIS Pro的Python环境中运行此脚本")
        response = input("是否继续？(y/n): ")
        if response.lower() != 'y':
            return
    
    # 运行GUI
    app = RasterExporterGUI()
    app.run()

if __name__ == "__main__":
    main()