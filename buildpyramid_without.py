import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Scrollbar
from tkinter import ttk
import arcpy
import threading

class PyramidBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("金字塔构建器")
        
        self.file_listbox = Listbox(root, selectmode=tk.MULTIPLE, width=50, height=15)
        self.file_listbox.pack(pady=10)

        self.scrollbar = Scrollbar(root)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.file_listbox.yview)

        self.select_button = tk.Button(root, text="选择影像文件", command=self.select_files)
        self.select_button.pack(pady=5)

        self.delete_button = tk.Button(root, text="删除选中影像", command=self.delete_selected_files)
        self.delete_button.pack(pady=5)

        self.start_button = tk.Button(root, text="开始构建", command=self.start_building)
        self.start_button.pack(pady=5)

        self.cancel_button = tk.Button(root, text="取消构建", command=self.cancel_building)
        self.cancel_button.pack(pady=5)

        self.status_label = tk.Label(root, text="状态: 等待中")
        self.status_label.pack(pady=5)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=5)

        self.building = False

    def select_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择影像文件",
            filetypes=[("TIFF files", "*.tif"), ("All files", "*.*")]
        )
        for file_path in file_paths:
            self.file_listbox.insert(tk.END, file_path)

    def delete_selected_files(self):
        selected_indices = self.file_listbox.curselection()
        for index in reversed(selected_indices):
            self.file_listbox.delete(index)

    def build_pyramids(self, file_paths):
        total_files = len(file_paths)
        for i, file_path in enumerate(file_paths):
            if not self.building:
                break
            try:
                self.status_label.config(text=f"正在构建: {file_path}")
                self.progress['value'] = (i / total_files) * 100
                self.root.update_idletasks()

                arcpy.BuildPyramids_management(
                    file_path, "-1", "NONE", "NEAREST", "JPEG", "100", "SKIP_EXISTING"
                )
                print(f"金字塔构建成功: {file_path}")
            except arcpy.ExecuteError:
                print(f"执行错误: {arcpy.GetMessages(2)}")
            except Exception as e:
                print(f"发生错误: {e}")

        self.status_label.config(text="状态: 完成")
        self.progress['value'] = 100
        messagebox.showinfo("完成", "所有金字塔构建完成。")

    def start_building(self):
        file_paths = [self.file_listbox.get(i) for i in range(self.file_listbox.size())]
        if not file_paths:
            messagebox.showwarning("警告", "列表中没有影像文件。")
            return

        self.building = True
        threading.Thread(target=self.build_pyramids, args=(file_paths,)).start()

    def cancel_building(self):
        self.building = False
        self.status_label.config(text="状态: 构建已取消")
        print("构建已取消。")

def main():
    root = tk.Tk()
    app = PyramidBuilderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()