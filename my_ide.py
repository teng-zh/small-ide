import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QListWidget, 
                             QMenuBar, QMenu, QFileDialog, QTabWidget, 
                             QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QToolBar, QStatusBar, QPlainTextEdit, QLineEdit, QSplitter, 
                             QTreeWidget, QTreeWidgetItem, QMessageBox, QPushButton, 
                             QListWidget, QListWidgetItem)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QFile, QTextStream, QTimer, QProcess
from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciLexerCPP, QsciLexerJava, QsciLexerHTML, QsciLexerJavaScript

class ResourceExplorer(QWidget):
    """资源管理器类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ide = parent
        self.initUI()
    
    def initUI(self):
        """初始化资源管理器界面"""
        self.layout = QVBoxLayout(self)
        
        # 树视图
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "大小", "类型", "修改日期"])
        self.tree.setColumnWidth(0, 200)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # 添加根目录
        self.populate_tree()
        
        self.layout.addWidget(self.tree)
    
    def populate_tree(self):
        """填充树视图"""
        self.tree.clear()
        
        # 获取根目录
        if sys.platform == "win32":
            # Windows系统获取所有驱动器
            drives = []
            for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                # 使用字符串拼接避免f-string末尾反斜杠问题
                drive_letter = d + ":"
                drive_path = drive_letter + "\\"
                if os.path.exists(drive_path):
                    drives.append(drive_path)
            
            for drive in drives:
                item = QTreeWidgetItem(self.tree, [drive])
                self.tree.addTopLevelItem(item)
                self.add_subdirectories(item, drive)
        else:
            # Linux/Mac系统使用根目录
            root_item = QTreeWidgetItem(self.tree, ["/"])
            self.tree.addTopLevelItem(root_item)
            self.add_subdirectories(root_item, "/")
    
    def add_subdirectories(self, parent_item, path):
        """添加子目录"""
        try:
            entries = os.listdir(path)
            for entry in entries:
                entry_path = os.path.join(path, entry)
                if os.path.isdir(entry_path):
                    item = QTreeWidgetItem(parent_item, [entry])
                    parent_item.addChild(item)
                    # 只添加一级子目录，避免加载过慢
        except PermissionError:
            pass
    
    def on_item_double_clicked(self, item, column):
        """双击项目处理"""
        # 构建完整路径
        path = self.get_full_path(item)
        
        if os.path.isfile(path):
            # 打开文件
            if self.parent_ide:
                self.parent_ide.open_specific_file(path)
        elif os.path.isdir(path):
            # 展开或折叠目录
            if item.isExpanded():
                self.tree.collapseItem(item)
            else:
                # 加载子目录
                self.load_subdirectories(item, path)
                self.tree.expandItem(item)
    
    def get_full_path(self, item):
        """获取项目的完整路径"""
        path = item.text(0)
        parent = item.parent()
        while parent:
            path = os.path.join(parent.text(0), path)
            parent = parent.parent()
        return path
    
    def load_subdirectories(self, item, path):
        """加载子目录"""
        # 清空现有子项
        item.takeChildren()
        
        try:
            entries = os.listdir(path)
            for entry in entries:
                entry_path = os.path.join(path, entry)
                if os.path.isdir(entry_path):
                    child_item = QTreeWidgetItem(item, [entry])
                    item.addChild(child_item)
                    # 预加载一级子目录
                    self.add_subdirectories(child_item, entry_path)
                elif os.path.isfile(entry_path):
                    # 添加文件
                    size = os.path.getsize(entry_path)
                    item_type = os.path.splitext(entry)[1]
                    mod_time = os.path.getmtime(entry_path)
                    child_item = QTreeWidgetItem(item, [entry, str(size), item_type, str(mod_time)])
                    item.addChild(child_item)
        except PermissionError:
            pass

class TerminalWidget(QWidget):
    """终端部件类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dir = os.getcwd()  # 当前工作目录
        self.history = []  # 命令历史记录
        self.history_index = 0  # 历史记录索引
        self.initUI()
        self.start_process()
    
    def initUI(self):
        """初始化终端界面"""
        self.layout = QVBoxLayout(self)
        
        # 终端输出显示
        self.output = QPlainTextEdit()
        self.output.setReadOnly(False)
        self.output.setStyleSheet("background-color: black; color: white; font-family: Consolas, monospace;")
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)  # 不自动换行
        self.layout.addWidget(self.output)
        
        # 设置焦点
        self.output.setFocus()
        
        # 显示欢迎信息和初始提示符
        self.output.appendPlainText(f"PowerShell 终端 - 当前目录: {self.current_dir}")
        self.output.appendPlainText("输入命令并按回车执行...")
        self.output.appendPlainText("")
        self.show_prompt()
    
    def show_prompt(self):
        """显示PowerShell风格的命令提示符"""
        prompt = f"PS {self.current_dir}>\ "
        self.output.appendPlainText(prompt)
        self.output.ensureCursorVisible()
    
    def handle_key_press(self, event):
        """处理键盘事件，支持命令历史导航"""
        from PyQt6.QtCore import Qt
        
        if event.key() == Qt.Key.Key_Up:
            # 向上导航历史
            if self.history_index > 0:
                self.history_index -= 1
                self.input_line.setText(self.history[self.history_index])
        elif event.key() == Qt.Key.Key_Down:
            # 向下导航历史
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.input_line.setText(self.history[self.history_index])
            else:
                # 到达历史末尾，清空输入
                self.history_index = len(self.history)
                self.input_line.clear()
        else:
            # 其他按键，调用默认处理
            super(QLineEdit, self.input_line).keyPressEvent(event)
    
    def start_process(self):
        """启动终端进程"""
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        # 连接信号
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_error)
        self.process.finished.connect(self.process_finished)
        
        # 启动shell - 使用NoLogo选项隐藏PowerShell启动信息
        if sys.platform == "win32":
            self.process.start("powershell.exe", ["-NoLogo"])
        else:
            self.process.start("bash")
    
    def read_output(self):
        """读取标准输出"""
        try:
            # 尝试使用UTF-8解码
            output = self.process.readAllStandardOutput().data().decode('utf-8')
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试使用GBK解码（Windows默认编码）
            try:
                output = self.process.readAllStandardOutput().data().decode('gbk')
            except UnicodeDecodeError:
                # 如果都失败，使用替换字符
                output = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        
        # 显示输出
        self.output.insertPlainText(output)
        self.output.ensureCursorVisible()
    
    def read_error(self):
        """读取标准错误"""
        try:
            # 尝试使用UTF-8解码
            error = self.process.readAllStandardError().data().decode('utf-8')
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试使用GBK解码（Windows默认编码）
            try:
                error = self.process.readAllStandardError().data().decode('gbk')
            except UnicodeDecodeError:
                # 如果都失败，使用替换字符
                error = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.output.insertPlainText(error)
        self.output.ensureCursorVisible()
    
    def send_command(self, command):
        """发送命令"""
        # 保存命令到历史记录
        self.history.append(command)
        self.history_index = len(self.history)
        
        # 执行命令
        self.process.write((command + "\n").encode())
        self.output.ensureCursorVisible()
        
        # 如果是cd命令，更新当前目录
        if command.startswith("cd "):
            # 提取目录
            new_dir = command[3:].strip()
            if new_dir:
                # 处理相对路径和绝对路径
                if os.path.isabs(new_dir):
                    self.current_dir = new_dir
                else:
                    self.current_dir = os.path.abspath(os.path.join(self.current_dir, new_dir))
                # 确保目录存在
                if not os.path.exists(self.current_dir):
                    self.current_dir = os.getcwd()
    
    def process_finished(self):
        """进程结束处理"""
        self.output.appendPlainText("\nProcess finished.")
        self.output.setReadOnly(True)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        from PyQt6.QtCore import Qt
        
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # 获取当前行内容
            cursor = self.output.textCursor()
            cursor.movePosition(cursor.MoveOperation.StartOfLine)
            cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
            line = cursor.selectedText()
            
            # 提取命令（去掉提示符）
            if line.startswith(f"PS {self.current_dir}>\ "):
                command = line[len(f"PS {self.current_dir}>\ "):].strip()
                self.send_command(command)
                # 显示新的提示符
                self.show_prompt()
        elif event.key() == Qt.Key.Key_Up:
            # 向上导航历史
            if self.history_index > 0:
                self.history_index -= 1
                # 更新当前行
                self.update_current_line(self.history[self.history_index])
        elif event.key() == Qt.Key.Key_Down:
            # 向下导航历史
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.update_current_line(self.history[self.history_index])
            else:
                # 到达历史末尾，清空当前行
                self.history_index = len(self.history)
                self.update_current_line("")
        else:
            # 其他按键，调用默认处理
            super().keyPressEvent(event)
    
    def update_current_line(self, text):
        """更新当前行内容"""
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(f"PS {self.current_dir}>\ {text}")
        # 将光标移动到行尾
        cursor.movePosition(cursor.MoveOperation.EndOfLine)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

class MyIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.tab_widget = None
        self.auto_save_timer = None
        self.auto_save_interval = 30000  # 30秒自动保存
        
        # 初始化设置
        self.settings_file = "ide_settings.json"
        self.settings = self.load_settings()
        
        self.initUI()
        self.init_auto_save()
        
        # 检查是否需要自动打开changes.log
        self.check_auto_open_changes_log()
        
        # 检查是否存在自动保存文件
        self.check_autosave_files()
        
    def initUI(self):
        self.setWindowTitle("MyIDE")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        # 打开设置对话框
        self.settings_action = QAction("IDE设置", self)
        self.settings_action.setShortcut("Ctrl+, ")
        self.settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(self.settings_action)
        
        # 语法检查菜单
        self.check_menu = menubar.addMenu("检查")
        
        self.check_syntax_action = QAction("检查语法", self)
        self.check_syntax_action.setShortcut("F7")
        self.check_syntax_action.triggered.connect(self.check_syntax)
        self.check_menu.addAction(self.check_syntax_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        # 添加主题子菜单
        theme_menu = view_menu.addMenu("主题")
        
        # 亮色模式
        self.light_theme_action = QAction("亮色模式", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.triggered.connect(lambda: self.switch_theme("light"))
        theme_menu.addAction(self.light_theme_action)
        
        # 暗色模式
        self.dark_theme_action = QAction("暗色模式", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(lambda: self.switch_theme("dark"))
        theme_menu.addAction(self.dark_theme_action)
        
        # 创建工具栏
        self.toolbar = self.addToolBar("工具栏")
        
        # 添加HTML运行按钮
        self.run_html_action = QAction("在浏览器中打开", self)
        self.run_html_action.setShortcut("F5")
        self.run_html_action.triggered.connect(self.run_html_in_browser)
        self.toolbar.addAction(self.run_html_action)
        self.run_html_action.setVisible(False)  # 默认隐藏
        
        # 添加Python运行按钮
        self.run_python_action = QAction("运行Python文件", self)
        self.run_python_action.setShortcut("F6")
        self.run_python_action.triggered.connect(self.run_python_file)
        self.toolbar.addAction(self.run_python_action)
        self.run_python_action.setVisible(False)  # 默认隐藏
        
        # 语言菜单 - 实现层级结构
        self.language_menu = menubar.addMenu("语言")
        
        # 创建语言分类和具体语言
        self.language_dict = {
            "None (Normal Text)": None,
            "A": ["ActionScript", "Ada", "Apache", "Asm", "NASM"],
            "B": ["Bash", "Batch", "BibTeX"],
            "C": ["C", "C++", "C#", "CMake", "CSS"],
            "D": ["D", "Diff"],
            "E": ["Eiffel", "Erlang"],
            "F": ["Fortran", "F#"],
            "Gui4Cli": None,
            "H": ["HTML", "Haskell"],
            "I": ["INI", "Inno Setup"],
            "J": ["Java", "JavaScript", "JSON", "JSON5"],
            "KIXtart": None,
            "L": ["LaTeX", "Lisp"],
            "M": ["Makefile", "Markdown", "Matlab"],
            "N": ["Nim", "NSIS", "NASM"],
            "O": ["Objective-C", "Octave"],
            "P": ["Pascal", "Perl", "PHP", "PowerShell", "Python"],
            "R": ["R", "Rust"],
            "S": ["SQL", "Scala", "Scheme"],
            "T": ["Tcl", "TeX"],
            "V": ["VBScript", "Verilog"],
            "XML": None,
            "VAML": None,
            "自定义语言": ["Markdown (preinstalled)", "Markdown (preinstalled dark mode)"],
            "用户自定义": None
        }
        
        # 构建语言菜单
        self.build_language_menu()
        
        # 创建标签页控件，设置为Notepad++风格
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.setMovable(True)  # 允许标签页拖动
        
        # 设置中心部件
        self.setCentralWidget(self.tab_widget)
        
        # 创建资源管理器停靠窗口
        self.resource_dock = QDockWidget("资源管理器", self)
        self.resource_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.resource_explorer = ResourceExplorer(self)
        self.resource_dock.setWidget(self.resource_explorer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.resource_dock)
        
        # 创建终端停靠窗口
        self.terminal_dock = QDockWidget("终端", self)
        self.terminal_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        
        # 创建终端标签页
        self.terminal_tab = QTabWidget()
        self.terminal_tab.setTabsClosable(True)
        self.terminal_tab.tabCloseRequested.connect(self.close_terminal_tab)
        
        # 添加第一个终端
        self.add_terminal_tab()
        
        # 添加新终端按钮
        self.new_terminal_btn = QPushButton("+ 新建终端")
        self.new_terminal_btn.clicked.connect(self.add_terminal_tab)
        self.terminal_tab.setCornerWidget(self.new_terminal_btn)
        
        self.terminal_dock.setWidget(self.terminal_tab)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.terminal_dock)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 状态栏信息 - Notepad++风格
        self.status_info = {
            "pos": QLabel("Ln: 1, Col: 1"),
            "length": QLabel("length: 0, lines: 1"),
            "type": QLabel("Normal text file"),
            "eol": QLabel("Unix (LF)"),
            "encoding": QLabel("UTF-8"),
            "mode": QLabel("INS"),
            "language": QLabel("语言: ")
        }
        
        # 当前语言显示
        self.current_language_label = QLabel("None (Normal Text)")
        self.statusBar().addPermanentWidget(self.current_language_label)
        
        # 添加状态栏组件 - 左侧信息
        self.statusBar().addWidget(self.status_info["pos"])
        self.statusBar().addWidget(QLabel(" | "))
        self.statusBar().addWidget(self.status_info["length"])
        self.statusBar().addWidget(QLabel(" | "))
        self.statusBar().addWidget(self.status_info["type"])
        
        # 添加中间信息
        self.statusBar().addWidget(QLabel(" | "))
        self.statusBar().addWidget(self.status_info["eol"])
        self.statusBar().addWidget(QLabel(" | "))
        self.statusBar().addWidget(self.status_info["encoding"])
        self.statusBar().addWidget(QLabel(" | "))
        self.statusBar().addWidget(self.status_info["mode"])
        
        # 右侧状态栏组件 - 显示当前语言
        self.statusBar().addPermanentWidget(QLabel("语言: "))
        self.statusBar().addPermanentWidget(self.current_language_label)
        
        # 创建问题选项卡
        self.problems_dock = QDockWidget("问题", self)
        self.problems_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        # 创建问题列表
        self.problems_list = QListWidget()
        self.problems_list.setStyleSheet("font-family: Consolas, monospace;")
        self.problems_dock.setWidget(self.problems_list)
        
        # 添加问题选项卡
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.problems_dock)
        
        # 默认隐藏问题选项卡
        self.problems_dock.hide()
        
        # 添加视图菜单选项，用于显示/隐藏问题选项卡
        view_menu.addAction(self.problems_dock.toggleViewAction())
        
        # 创建第一个编辑器标签
        self.new_file()
        
        # 设置默认隐藏终端和资源管理器
        self.resource_dock.hide()
        self.terminal_dock.hide()
        
        # 添加视图菜单选项，用于显示/隐藏终端和资源管理器
        view_menu.addAction(self.resource_dock.toggleViewAction())
        view_menu.addAction(self.terminal_dock.toggleViewAction())
        
        # 延迟主题设置，确保所有UI组件已经初始化
        QTimer.singleShot(100, lambda: self.apply_initial_theme())
    
    def setup_editor(self):
        # 创建自定义编辑器类，继承QsciScintilla以实现括号自动补全
        class CustomEditor(QsciScintilla):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.brace_pairs = {
                    '(': ')',
                    '[': ']',
                    '{': '}',
                    '<': '>',
                    '"': '"',
                    "'": "'"
                }
                self.parent_ide = parent
            
            def keyPressEvent(self, event):
                # 标记为已修改
                self.setModified(True)
                
                from PyQt6.QtCore import Qt
                
                # 处理回车键，实现智能缩进
                if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                    # 获取当前光标位置
                    line, col = self.getCursorPosition()
                    
                    # 获取当前行内容
                    current_line = self.text(line)
                    
                    # 计算当前行的缩进
                    indent = len(current_line) - len(current_line.lstrip())
                    
                    # 检查当前行是否以左大括号结尾，或者光标在左右大括号之间
                    stripped_line = current_line.strip()
                    
                    # 检查光标是否在左右大括号之间
                    cursor_in_braces = False
                    if len(stripped_line) >= 2 and stripped_line[-1] == '}' and '{' in stripped_line:
                        # 找到左大括号的位置
                        open_brace_pos = stripped_line.rfind('{')
                        if open_brace_pos < len(stripped_line) - 1:
                            cursor_in_braces = True
                    
                    # 如果当前行以左大括号结尾，或者光标在左右大括号之间
                    if stripped_line.endswith('{') or cursor_in_braces:
                        # 智能缩进处理
                        
                        # 计算新的缩进级别
                        new_indent = indent + self.indentationWidth()
                        
                        # 获取缩进字符串（使用空格）
                        indent_str = ' ' * indent
                        new_indent_str = ' ' * new_indent
                        
                        # 插入新行
                        self.insert('\n' + new_indent_str + '\n' + indent_str)
                        
                        # 将光标移动到中间的新行
                        self.setCursorPosition(line + 1, new_indent)
                        
                        # 更新状态栏
                        self.update_status()
                        return
                    
                # 处理括号补全
                key = event.text()
                if key in self.brace_pairs:
                    # 获取当前光标位置和上下文
                    line, col = self.getCursorPosition()
                    
                    # 智能处理流操作符和函数调用
                    if key == '<' or key == '>':
                        # 获取当前行内容
                        current_line = self.text(line)
                        
                        # 检查是否是流操作符或函数调用
                        if col > 0:
                            # 检查前一个字符
                            prev_char = current_line[col-1] if col <= len(current_line) else ''
                            
                            # 检查当前行是否包含流操作符相关的关键字
                            line_lower = current_line.lower()
                            is_stream_operation = any(keyword in line_lower for keyword in ['cout', 'cerr', 'cin', 'clog', '<<', '>>'])
                            
                            # 如果前一个字符是<或>，或者是流操作符相关，或者是在函数调用中
                            if prev_char == '<' or prev_char == '>' or is_stream_operation:
                                # 不自动补全，直接插入字符
                                super().keyPressEvent(event)
                                self.update_status()
                                return
                            
                            # 检查是否在函数调用中，比如func<type>(...)
                            if col > 1:
                                # 检查前两个字符，看是否是模板或函数调用
                                prev_two_chars = current_line[col-2:col] if col >= 2 else ''
                                if prev_two_chars.isalnum() or prev_two_chars.endswith('('):
                                    # 可能是模板或函数调用，不自动补全
                                    super().keyPressEvent(event)
                                    self.update_status()
                                    return
                    
                    # 普通括号补全
                    super().keyPressEvent(event)
                    self.insert(self.brace_pairs[key])
                    self.setCursorPosition(line, col + 1)
                    # 处理完括号补全后，直接返回，不再执行其他处理
                    self.update_status()
                    return
                else:
                    # 移除直接的HTML标签自动补全，让代码提示功能处理
                    # 这样所有补全都会通过代码提示（下拉列表）呈现给用户
                    pass
                
                # 其他按键，调用默认处理
                super().keyPressEvent(event)
                # 更新状态栏
                self.update_status()
            
            def mouseReleaseEvent(self, event):
                super().mouseReleaseEvent(event)
                # 更新状态栏
                self.update_status()
            
            def focusInEvent(self, event):
                super().focusInEvent(event)
                # 更新状态栏
                self.update_status()
            
            def update_status(self):
                # 更新光标位置
                line, col = self.getCursorPosition()
                if hasattr(self.parent_ide, 'status_info'):
                    # 更新行号列号
                    self.parent_ide.status_info["pos"].setText(f"Ln: {line+1}, Col: {col+1}")
                    
                    # 更新文件长度和行数
                    text = self.text()
                    length = len(text)
                    lines = len(text.split('\n'))
                    self.parent_ide.status_info["length"].setText(f"length: {length}, lines: {lines}")
        
        # 创建编辑器，传递父IDE引用
        editor = CustomEditor(self)
        
        # 设置字体和大小
        font = editor.font()
        font.setFamily("Consolas")
        font.setPointSize(12)
        editor.setFont(font)
        editor.setMarginsFont(font)
        
        # 设置边距
        editor.setMarginWidth(0, 50)  # 行号边距
        editor.setMarginLineNumbers(0, True)
        editor.setMarginsBackgroundColor(Qt.GlobalColor.lightGray)
        
        # 设置语法高亮
        lexer = QsciLexerPython()
        lexer.setFont(font)
        editor.setLexer(lexer)
        
        # 设置自动缩进 - 优化版本
        editor.setAutoIndent(True)
        editor.setIndentationsUseTabs(False)  # 使用空格而不是制表符
        editor.setTabWidth(4)  # 制表符宽度
        editor.setIndentationWidth(4)  # 缩进宽度
        editor.setBackspaceUnindents(True)  # 退格键取消缩进
        editor.setTabIndents(True)  # Tab键缩进
        editor.setIndentationGuides(True)  # 显示缩进指南
        
        # 设置智能缩进规则
        try:
            editor.setBraceIndentMode(QsciScintilla.BraceIndentMode.BraceIndent)  # 括号缩进模式
        except AttributeError:
            pass  # 忽略不支持的方法
        
        # 设置换行时的缩进
        editor.setWrapIndentMode(QsciScintilla.WrapIndentMode.WrapIndentSame)  # 换行缩进与当前行相同
        
        # 设置括号匹配
        editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        
        # 移除自动补全功能
        # 不再显示任何代码提示下拉列表
        
        # 设置换行
        editor.setWrapMode(QsciScintilla.WrapMode.WrapWord)
        editor.setWrapVisualFlags(QsciScintilla.WrapVisualFlag.WrapFlagByText)
        
        # 设置光标样式
        editor.setCaretWidth(2)
        editor.setCaretLineVisible(False)  # 移除编辑行高亮
        editor.setCaretLineBackgroundColor(Qt.GlobalColor.yellow)
        
        # 移除下划线样式配置，简化实现，专注于问题选项卡中的详细错误信息
        
        # 添加文本改变事件监听，用于实时语法检查
        editor.textChanged.connect(lambda: self.check_syntax(editor=editor))
        
        return editor
    
    def load_settings(self):
        """加载设置文件"""
        default_settings = {
            "changes_log_opened": False,
            "theme": "light",  # 默认使用亮色模式
            "auto_save_interval": 30000,  # 30秒自动保存
            "show_line_numbers": True,  # 显示行号
            "show_indentation_guides": True,  # 显示缩进指南
            "show_caret_line": False,  # 显示光标行
            "show_whitespace": False,  # 显示空格
            "show_eol_markers": False,  # 显示行尾标记
            "show_ruler": False,  # 显示标尺
            "ruler_column": 80,  # 标尺位置
            "use_tabs": False,  # 使用空格而不是制表符
            "tab_width": 4,  # 制表符宽度
            "indentation_width": 4,  # 缩进宽度
            "indent_on_tab": True,  # Tab键缩进
            "unindent_on_backspace": True,  # 退格键取消缩进
            "auto_complete_brackets": True,  # 自动补全括号
            "auto_complete_quotes": True,  # 自动补全引号
            "brace_matching": True,  # 括号匹配
            "caret_style": 0,  # 光标样式：0=竖线
            "caret_width": 2,  # 光标宽度
            "line_height": 12,  # 行高
            "caret_blink": True,  # 光标闪烁
            "caret_blink_rate": 500,  # 光标闪烁速度
            "show_status_bar": True,  # 显示状态栏
            "show_toolbar": False,  # 显示工具栏
            "show_full_path": False,  # 显示完整文件路径
            "wrap_mode": 1,  # 换行模式：1=按单词换行
            "wrap_visual": True,  # 显示换行标记
            "wrap_indent_mode": 1,  # 换行缩进模式：1=与当前行相同
            "folding_enabled": True,  # 启用代码折叠
            "folding_margin": True,  # 显示折叠边距
            "folding_style": 2,  # 折叠样式：2=树状
            "syntax_check_enabled": True,  # 启用语法检查
            "syntax_check_interval": 1000,  # 语法检查间隔
            "show_warnings": True,  # 显示警告
            "show_errors": True,  # 显示错误
            "default_encoding": 0,  # 默认文件编码：0=UTF-8
            "auto_detect_encoding": True,  # 自动检测编码
            "add_newline_at_end": True,  # 保存时自动添加换行符
            "font_family": "Consolas",  # 字体
            "font_size": 12,  # 字体大小
            "terminal_font_size": 12,  # 终端字体大小
            "terminal_font_family": "Consolas",  # 终端字体
            "resource_explorer_visible": False,  # 资源管理器可见性
            "terminal_visible": False,  # 终端可见性
            "problems_visible": False  # 问题选项卡可见性
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载设置失败: {e}")
                return default_settings
        else:
            return default_settings
    
    def open_settings_dialog(self):
        """打开IDE设置对话框"""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                                    QCheckBox, QSpinBox, QPushButton, QGroupBox, QLineEdit,
                                    QTabWidget)
        
        # 创建设置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("IDE设置")
        dialog.resize(700, 600)  # 增加对话框大小
        
        # 创建主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(10)  # 设置布局间距
        main_layout.setContentsMargins(15, 15, 15, 15)  # 设置布局边距
        
        # 创建标签页
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        tab_widget.setMinimumSize(650, 500)
        
        # 1. 外观设置
        appearance_tab = QWidget()
        tab_widget.addTab(appearance_tab, "外观")
        
        appearance_layout = QVBoxLayout(appearance_tab)
        
        # 主题设置
        theme_group = QGroupBox("主题")
        theme_layout = QHBoxLayout(theme_group)  # 使用水平布局
        theme_layout.setSpacing(10)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["亮色模式", "暗色模式"])
        # 设置当前主题
        current_theme = self.settings.get("theme", "light")
        self.theme_combo.setCurrentIndex(0 if current_theme == "light" else 1)
        theme_layout.addWidget(QLabel("选择主题:"))
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()  # 添加伸缩项，使控件靠左对齐
        appearance_layout.addWidget(theme_group)
        
        # 字体设置
        font_group = QGroupBox("字体")
        font_layout = QGridLayout(font_group)  # 使用网格布局
        font_layout.setSpacing(10)
        font_layout.setColumnStretch(1, 1)  # 第二列可伸缩
        
        font_layout.addWidget(QLabel("字体名称:"), 0, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.font_family_edit = QLineEdit(self.settings.get("font_family", "Consolas"))
        font_layout.addWidget(self.font_family_edit, 0, 1)
        
        font_layout.addWidget(QLabel("字体大小:"), 1, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.settings.get("font_size", 12))
        font_layout.addWidget(self.font_size_spin, 1, 1)
        appearance_layout.addWidget(font_group)
        
        # 2. 编辑设置
        editor_tab = QWidget()
        tab_widget.addTab(editor_tab, "编辑器")
        
        editor_layout = QVBoxLayout(editor_tab)
        
        # 显示设置
        display_group = QGroupBox("显示")
        display_layout = QGridLayout(display_group)  # 使用网格布局
        display_layout.setSpacing(15)
        display_layout.setColumnStretch(1, 1)
        display_layout.setColumnStretch(3, 1)
        
        # 第一行
        self.show_line_numbers_check = QCheckBox("显示行号")
        self.show_line_numbers_check.setChecked(self.settings.get("show_line_numbers", True))
        display_layout.addWidget(self.show_line_numbers_check, 0, 0, 1, 2)
        
        self.show_indentation_guides_check = QCheckBox("显示缩进指南")
        self.show_indentation_guides_check.setChecked(self.settings.get("show_indentation_guides", True))
        display_layout.addWidget(self.show_indentation_guides_check, 0, 2, 1, 2)
        
        # 第二行
        self.show_caret_line_check = QCheckBox("显示光标行")
        self.show_caret_line_check.setChecked(self.settings.get("show_caret_line", False))
        display_layout.addWidget(self.show_caret_line_check, 1, 0, 1, 2)
        
        self.show_whitespace_check = QCheckBox("显示空格")
        self.show_whitespace_check.setChecked(self.settings.get("show_whitespace", False))
        display_layout.addWidget(self.show_whitespace_check, 1, 2, 1, 2)
        
        # 第三行
        self.show_eol_markers_check = QCheckBox("显示行尾标记")
        self.show_eol_markers_check.setChecked(self.settings.get("show_eol_markers", False))
        display_layout.addWidget(self.show_eol_markers_check, 2, 0, 1, 2)
        
        self.show_ruler_check = QCheckBox("显示标尺")
        self.show_ruler_check.setChecked(self.settings.get("show_ruler", False))
        display_layout.addWidget(self.show_ruler_check, 2, 2, 1, 2)
        
        # 第四行 - 标尺位置
        ruler_layout = QHBoxLayout()
        ruler_layout.addWidget(QLabel("标尺位置:"))
        self.ruler_column_spin = QSpinBox()
        self.ruler_column_spin.setRange(10, 200)
        self.ruler_column_spin.setValue(self.settings.get("ruler_column", 80))
        ruler_layout.addWidget(self.ruler_column_spin)
        ruler_layout.addStretch()
        display_layout.addLayout(ruler_layout, 3, 0, 1, 4)
        editor_layout.addWidget(display_group)
        
        # 缩进设置
        indent_group = QGroupBox("缩进")
        indent_layout = QGridLayout(indent_group)  # 使用网格布局
        indent_layout.setSpacing(15)
        indent_layout.setColumnStretch(1, 1)
        indent_layout.setColumnStretch(3, 1)
        
        # 第一行
        self.use_tabs_check = QCheckBox("使用制表符")
        self.use_tabs_check.setChecked(self.settings.get("use_tabs", False))
        indent_layout.addWidget(self.use_tabs_check, 0, 0, 1, 4)
        
        # 第二行
        indent_layout.addWidget(QLabel("制表符宽度:"), 1, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tab_width_spin = QSpinBox()
        self.tab_width_spin.setRange(1, 8)
        self.tab_width_spin.setValue(self.settings.get("tab_width", 4))
        indent_layout.addWidget(self.tab_width_spin, 1, 1)
        
        indent_layout.addWidget(QLabel("缩进宽度:"), 1, 2, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.indentation_width_spin = QSpinBox()
        self.indentation_width_spin.setRange(1, 8)
        self.indentation_width_spin.setValue(self.settings.get("indentation_width", 4))
        indent_layout.addWidget(self.indentation_width_spin, 1, 3)
        
        # 第三行
        self.indent_on_tab_check = QCheckBox("Tab键缩进")
        self.indent_on_tab_check.setChecked(self.settings.get("indent_on_tab", True))
        indent_layout.addWidget(self.indent_on_tab_check, 2, 0, 1, 2)
        
        self.unindent_on_backspace_check = QCheckBox("退格键取消缩进")
        self.unindent_on_backspace_check.setChecked(self.settings.get("unindent_on_backspace", True))
        indent_layout.addWidget(self.unindent_on_backspace_check, 2, 2, 1, 2)
        
        editor_layout.addWidget(indent_group)
        
        # 自动补全设置
        auto_complete_group = QGroupBox("自动补全")
        auto_complete_layout = QGridLayout(auto_complete_group)  # 使用网格布局
        auto_complete_layout.setSpacing(15)
        auto_complete_layout.setColumnStretch(1, 1)
        auto_complete_layout.setColumnStretch(3, 1)
        
        # 第一行
        self.auto_complete_brackets_check = QCheckBox("自动补全括号")
        self.auto_complete_brackets_check.setChecked(self.settings.get("auto_complete_brackets", True))
        auto_complete_layout.addWidget(self.auto_complete_brackets_check, 0, 0, 1, 2)
        
        self.brace_matching_check = QCheckBox("括号匹配")
        self.brace_matching_check.setChecked(self.settings.get("brace_matching", True))
        auto_complete_layout.addWidget(self.brace_matching_check, 0, 2, 1, 2)
        
        # 第二行
        self.auto_complete_quotes_check = QCheckBox("自动补全引号")
        self.auto_complete_quotes_check.setChecked(self.settings.get("auto_complete_quotes", True))
        auto_complete_layout.addWidget(self.auto_complete_quotes_check, 1, 0, 1, 4)
        
        editor_layout.addWidget(auto_complete_group)
        
        # 光标设置
        cursor_group = QGroupBox("光标")
        cursor_layout = QGridLayout(cursor_group)  # 使用网格布局
        cursor_layout.setSpacing(15)
        cursor_layout.setColumnStretch(1, 1)
        cursor_layout.setColumnStretch(3, 1)
        
        # 第一行
        cursor_layout.addWidget(QLabel("光标样式:"), 0, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.caret_style_combo = QComboBox()
        self.caret_style_combo.addItems(["竖线", "块状", "下划线"])
        self.caret_style_combo.setCurrentIndex(self.settings.get("caret_style", 0))
        cursor_layout.addWidget(self.caret_style_combo, 0, 1)
        
        cursor_layout.addWidget(QLabel("光标宽度:"), 0, 2, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.caret_width_spin = QSpinBox()
        self.caret_width_spin.setRange(1, 5)
        self.caret_width_spin.setValue(self.settings.get("caret_width", 2))
        cursor_layout.addWidget(self.caret_width_spin, 0, 3)
        
        # 第二行
        self.caret_blink_check = QCheckBox("光标闪烁")
        self.caret_blink_check.setChecked(self.settings.get("caret_blink", True))
        cursor_layout.addWidget(self.caret_blink_check, 1, 0, 1, 2)
        
        cursor_layout.addWidget(QLabel("光标闪烁速度:"), 1, 2, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.caret_blink_rate_spin = QSpinBox()
        self.caret_blink_rate_spin.setRange(100, 2000)
        self.caret_blink_rate_spin.setValue(self.settings.get("caret_blink_rate", 500))
        cursor_layout.addWidget(self.caret_blink_rate_spin, 1, 3)
        
        # 第三行
        cursor_layout.addWidget(QLabel("行高:"), 2, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.line_height_spin = QSpinBox()
        self.line_height_spin.setRange(10, 30)
        self.line_height_spin.setValue(self.settings.get("line_height", 12))
        cursor_layout.addWidget(self.line_height_spin, 2, 1)
        
        editor_layout.addWidget(cursor_group)
        
        # 显示扩展设置
        display_ext_group = QGroupBox("显示扩展")
        display_ext_layout = QGridLayout(display_ext_group)  # 使用网格布局
        display_ext_layout.setSpacing(15)
        display_ext_layout.setColumnStretch(1, 1)
        display_ext_layout.setColumnStretch(3, 1)
        
        # 第一行
        self.show_status_bar_check = QCheckBox("显示状态栏")
        self.show_status_bar_check.setChecked(self.settings.get("show_status_bar", True))
        display_ext_layout.addWidget(self.show_status_bar_check, 0, 0, 1, 2)
        
        self.show_toolbar_check = QCheckBox("显示工具栏")
        self.show_toolbar_check.setChecked(self.settings.get("show_toolbar", False))
        display_ext_layout.addWidget(self.show_toolbar_check, 0, 2, 1, 2)
        
        # 第二行
        self.show_full_path_check = QCheckBox("显示完整文件路径")
        self.show_full_path_check.setChecked(self.settings.get("show_full_path", False))
        display_ext_layout.addWidget(self.show_full_path_check, 1, 0, 1, 4)
        
        editor_layout.addWidget(display_ext_group)
        
        # 换行设置
        wrap_group = QGroupBox("换行")
        wrap_layout = QGridLayout(wrap_group)  # 使用网格布局
        wrap_layout.setSpacing(15)
        wrap_layout.setColumnStretch(1, 1)
        wrap_layout.setColumnStretch(3, 1)
        
        # 第一行
        wrap_layout.addWidget(QLabel("换行模式:"), 0, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.wrap_mode_combo = QComboBox()
        self.wrap_mode_combo.addItems(["不换行", "按单词换行", "按字符换行"])
        self.wrap_mode_combo.setCurrentIndex(self.settings.get("wrap_mode", 1))
        wrap_layout.addWidget(self.wrap_mode_combo, 0, 1)
        
        self.wrap_visual_check = QCheckBox("显示换行标记")
        self.wrap_visual_check.setChecked(self.settings.get("wrap_visual", True))
        wrap_layout.addWidget(self.wrap_visual_check, 0, 2, 1, 2)
        
        # 第二行
        wrap_layout.addWidget(QLabel("换行缩进模式:"), 1, 0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.wrap_indent_mode_combo = QComboBox()
        self.wrap_indent_mode_combo.addItems(["无缩进", "与当前行相同", "增加缩进"])
        self.wrap_indent_mode_combo.setCurrentIndex(self.settings.get("wrap_indent_mode", 1))
        wrap_layout.addWidget(self.wrap_indent_mode_combo, 1, 1)
        editor_layout.addWidget(wrap_group)
        
        # 代码折叠设置
        folding_group = QGroupBox("代码折叠")
        folding_layout = QVBoxLayout(folding_group)
        
        self.folding_enabled_check = QCheckBox("启用代码折叠")
        self.folding_enabled_check.setChecked(self.settings.get("folding_enabled", True))
        folding_layout.addWidget(self.folding_enabled_check)
        
        self.folding_margin_check = QCheckBox("显示折叠边距")
        self.folding_margin_check.setChecked(self.settings.get("folding_margin", True))
        folding_layout.addWidget(self.folding_margin_check)
        
        self.folding_style_combo = QComboBox()
        self.folding_style_combo.addItems(["无", "简单", "树状"])
        self.folding_style_combo.setCurrentIndex(self.settings.get("folding_style", 2))
        folding_layout.addWidget(QLabel("折叠样式:"))
        folding_layout.addWidget(self.folding_style_combo)
        editor_layout.addWidget(folding_group)
        
        # 3. 自动保存设置
        auto_save_tab = QWidget()
        tab_widget.addTab(auto_save_tab, "自动保存")
        
        auto_save_layout = QVBoxLayout(auto_save_tab)
        
        self.auto_save_interval_spin = QSpinBox()
        self.auto_save_interval_spin.setRange(5000, 300000)
        self.auto_save_interval_spin.setValue(self.settings.get("auto_save_interval", 30000))
        self.auto_save_interval_spin.setSuffix(" 毫秒")
        auto_save_layout.addWidget(QLabel("自动保存间隔:"))
        auto_save_layout.addWidget(self.auto_save_interval_spin)
        
        # 4. 语法检查设置
        syntax_tab = QWidget()
        tab_widget.addTab(syntax_tab, "语法检查")
        
        syntax_layout = QVBoxLayout(syntax_tab)
        
        self.syntax_check_enabled_check = QCheckBox("启用语法检查")
        self.syntax_check_enabled_check.setChecked(self.settings.get("syntax_check_enabled", True))
        syntax_layout.addWidget(self.syntax_check_enabled_check)
        
        syntax_layout.addWidget(QLabel("语法检查间隔:"))
        self.syntax_check_interval_spin = QSpinBox()
        self.syntax_check_interval_spin.setRange(500, 5000)
        self.syntax_check_interval_spin.setValue(self.settings.get("syntax_check_interval", 1000))
        self.syntax_check_interval_spin.setSuffix(" 毫秒")
        syntax_layout.addWidget(self.syntax_check_interval_spin)
        
        self.show_warnings_check = QCheckBox("显示警告")
        self.show_warnings_check.setChecked(self.settings.get("show_warnings", True))
        syntax_layout.addWidget(self.show_warnings_check)
        
        self.show_errors_check = QCheckBox("显示错误")
        self.show_errors_check.setChecked(self.settings.get("show_errors", True))
        syntax_layout.addWidget(self.show_errors_check)
        
        # 5. 文件设置
        file_tab = QWidget()
        tab_widget.addTab(file_tab, "文件")
        
        file_layout = QVBoxLayout(file_tab)
        
        self.default_encoding_combo = QComboBox()
        self.default_encoding_combo.addItems(["UTF-8", "GBK", "ASCII", "UTF-16"])
        self.default_encoding_combo.setCurrentIndex(self.settings.get("default_encoding", 0))
        file_layout.addWidget(QLabel("默认文件编码:"))
        file_layout.addWidget(self.default_encoding_combo)
        
        self.auto_detect_encoding_check = QCheckBox("自动检测编码")
        self.auto_detect_encoding_check.setChecked(self.settings.get("auto_detect_encoding", True))
        file_layout.addWidget(self.auto_detect_encoding_check)
        
        self.add_newline_at_end_check = QCheckBox("保存时自动添加换行符")
        self.add_newline_at_end_check.setChecked(self.settings.get("add_newline_at_end", True))
        file_layout.addWidget(self.add_newline_at_end_check)
        
        # 6. 终端设置
        terminal_tab = QWidget()
        tab_widget.addTab(terminal_tab, "终端")
        
        terminal_layout = QVBoxLayout(terminal_tab)
        
        terminal_layout.addWidget(QLabel("终端字体大小:"))
        self.terminal_font_size_spin = QSpinBox()
        self.terminal_font_size_spin.setRange(8, 24)
        self.terminal_font_size_spin.setValue(self.settings.get("terminal_font_size", 12))
        terminal_layout.addWidget(self.terminal_font_size_spin)
        
        terminal_layout.addWidget(QLabel("终端字体:"))
        self.terminal_font_family_edit = QLineEdit(self.settings.get("terminal_font_family", "Consolas"))
        terminal_layout.addWidget(self.terminal_font_family_edit)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("应用")
        apply_button.clicked.connect(self.apply_settings)
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(lambda: self.apply_settings() or dialog.accept())
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        dialog.exec()
    
    def apply_settings(self):
        """应用设置"""
        # 更新设置
        self.settings["theme"] = "light" if self.theme_combo.currentIndex() == 0 else "dark"
        self.settings["font_family"] = self.font_family_edit.text()
        self.settings["font_size"] = self.font_size_spin.value()
        self.settings["show_line_numbers"] = self.show_line_numbers_check.isChecked()
        self.settings["show_indentation_guides"] = self.show_indentation_guides_check.isChecked()
        self.settings["show_caret_line"] = self.show_caret_line_check.isChecked()
        self.settings["show_whitespace"] = self.show_whitespace_check.isChecked()
        self.settings["show_eol_markers"] = self.show_eol_markers_check.isChecked()
        self.settings["show_ruler"] = self.show_ruler_check.isChecked()
        self.settings["ruler_column"] = self.ruler_column_spin.value()
        self.settings["use_tabs"] = self.use_tabs_check.isChecked()
        self.settings["tab_width"] = self.tab_width_spin.value()
        self.settings["indentation_width"] = self.indentation_width_spin.value()
        self.settings["indent_on_tab"] = self.indent_on_tab_check.isChecked()
        self.settings["unindent_on_backspace"] = self.unindent_on_backspace_check.isChecked()
        self.settings["auto_complete_brackets"] = self.auto_complete_brackets_check.isChecked()
        self.settings["auto_complete_quotes"] = self.auto_complete_quotes_check.isChecked()
        self.settings["brace_matching"] = self.brace_matching_check.isChecked()
        self.settings["caret_style"] = self.caret_style_combo.currentIndex()
        self.settings["caret_width"] = self.caret_width_spin.value()
        self.settings["line_height"] = self.line_height_spin.value()
        self.settings["caret_blink"] = self.caret_blink_check.isChecked()
        self.settings["caret_blink_rate"] = self.caret_blink_rate_spin.value()
        self.settings["show_status_bar"] = self.show_status_bar_check.isChecked()
        self.settings["show_toolbar"] = self.show_toolbar_check.isChecked()
        self.settings["show_full_path"] = self.show_full_path_check.isChecked()
        self.settings["wrap_mode"] = self.wrap_mode_combo.currentIndex()
        self.settings["wrap_visual"] = self.wrap_visual_check.isChecked()
        self.settings["wrap_indent_mode"] = self.wrap_indent_mode_combo.currentIndex()
        self.settings["folding_enabled"] = self.folding_enabled_check.isChecked()
        self.settings["folding_margin"] = self.folding_margin_check.isChecked()
        self.settings["folding_style"] = self.folding_style_combo.currentIndex()
        self.settings["auto_save_interval"] = self.auto_save_interval_spin.value()
        self.settings["syntax_check_enabled"] = self.syntax_check_enabled_check.isChecked()
        self.settings["syntax_check_interval"] = self.syntax_check_interval_spin.value()
        self.settings["show_warnings"] = self.show_warnings_check.isChecked()
        self.settings["show_errors"] = self.show_errors_check.isChecked()
        self.settings["default_encoding"] = self.default_encoding_combo.currentIndex()
        self.settings["auto_detect_encoding"] = self.auto_detect_encoding_check.isChecked()
        self.settings["add_newline_at_end"] = self.add_newline_at_end_check.isChecked()
        self.settings["terminal_font_size"] = self.terminal_font_size_spin.value()
        self.settings["terminal_font_family"] = self.terminal_font_family_edit.text()
        
        # 保存设置
        self.save_settings()
        
        # 应用主题
        self.switch_theme(self.settings["theme"])
        
        # 更新编辑器设置
        self.update_editor_settings()
        
        # 更新自动保存定时器
        self.init_auto_save()
        
        # 更新状态栏信息
        self.statusBar().showMessage("设置已应用")
    
    def update_editor_settings(self):
        """更新所有编辑器的设置"""
        if hasattr(self, 'tab_widget') and self.tab_widget is not None:
            for i in range(self.tab_widget.count()):
                editor = self.tab_widget.widget(i)
                if hasattr(editor, "setPaper"):
                    # 更新字体
                    font = editor.font()
                    font.setFamily(self.settings.get("font_family", "Consolas"))
                    font.setPointSize(self.settings.get("font_size", 12))
                    editor.setFont(font)
                    editor.setMarginsFont(font)
                    
                    # 更新行号显示
                    editor.setMarginLineNumbers(0, self.settings.get("show_line_numbers", True))
                    
                    # 更新缩进指南
                    editor.setIndentationGuides(self.settings.get("show_indentation_guides", True))
                    
                    # 更新光标行
                    editor.setCaretLineVisible(self.settings.get("show_caret_line", False))
                    
                    # 更新显示空格和行尾标记
                    whitespace_visibility = QsciScintilla.WhitespaceVisibility.WsInvisible
                    if self.settings.get("show_whitespace", False):
                        if self.settings.get("show_eol_markers", False):
                            whitespace_visibility = QsciScintilla.WhitespaceVisibility.WsVisibleAfterIndent
                        else:
                            whitespace_visibility = QsciScintilla.WhitespaceVisibility.WsVisible
                    editor.setWhitespaceVisibility(whitespace_visibility)
                    editor.setWhitespaceSize(1)
                    
                    # 更新标尺
                    if self.settings.get("show_ruler", False):
                        editor.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
                        editor.setEdgeColumn(self.settings.get("ruler_column", 80))
                        editor.setEdgeColor(Qt.GlobalColor.lightGray)
                    else:
                        editor.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)
                    
                    # 更新制表符和缩进设置
                    editor.setIndentationsUseTabs(self.settings.get("use_tabs", False))
                    editor.setTabWidth(self.settings.get("tab_width", 4))
                    editor.setIndentationWidth(self.settings.get("indentation_width", 4))
                    editor.setTabIndents(self.settings.get("indent_on_tab", True))
                    editor.setBackspaceUnindents(self.settings.get("unindent_on_backspace", True))
                    
                    # 更新括号匹配
                    if self.settings.get("brace_matching", True):
                        editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
                    else:
                        editor.setBraceMatching(QsciScintilla.BraceMatch.NoBraceMatch)
                    
                    # 更新光标设置
                    caret_style = self.settings.get("caret_style", 0)
                    if caret_style == 0:
                        editor.setCaretStyle(QsciScintilla.CaretStyle.CaretStyleLine)
                    elif caret_style == 1:
                        editor.setCaretStyle(QsciScintilla.CaretStyle.CaretStyleBlock)
                    else:
                        editor.setCaretStyle(QsciScintilla.CaretStyle.CaretStyleUnderline)
                    
                    editor.setCaretWidth(self.settings.get("caret_width", 2))
                    editor.setCaretBlinkRate(self.settings.get("caret_blink_rate", 500))
                    if not self.settings.get("caret_blink", True):
                        editor.setCaretBlinkRate(0)  # 禁用闪烁
                    
                    # 更新行高
                    line_height = self.settings.get("line_height", 12)
                    editor.setLineHeight(line_height)
                    
                    # 更新换行设置
                    wrap_mode = self.settings.get("wrap_mode", 1)
                    if wrap_mode == 0:
                        editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)
                    elif wrap_mode == 1:
                        editor.setWrapMode(QsciScintilla.WrapMode.WrapWord)
                    else:
                        editor.setWrapMode(QsciScintilla.WrapMode.WrapChar)
                    
                    # 更新换行视觉标记
                    if self.settings.get("wrap_visual", True):
                        editor.setWrapVisualFlags(QsciScintilla.WrapVisualFlag.WrapFlagByText)
                    else:
                        editor.setWrapVisualFlags(QsciScintilla.WrapVisualFlag.WrapFlagNone)
                    
                    # 更新换行缩进模式
                    wrap_indent_mode = self.settings.get("wrap_indent_mode", 1)
                    if wrap_indent_mode == 0:
                        editor.setWrapIndentMode(QsciScintilla.WrapIndentMode.WrapIndentNone)
                    elif wrap_indent_mode == 1:
                        editor.setWrapIndentMode(QsciScintilla.WrapIndentMode.WrapIndentSame)
                    else:
                        editor.setWrapIndentMode(QsciScintilla.WrapIndentMode.WrapIndentMore)
                    
                    # 更新代码折叠设置
                    folding_enabled = self.settings.get("folding_enabled", True)
                    folding_style = self.settings.get("folding_style", 2)
                    
                    if folding_enabled:
                        if folding_style == 0:
                            editor.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)
                        elif folding_style == 1:
                            editor.setFolding(QsciScintilla.FoldStyle.BoxedFoldStyle)
                        else:
                            editor.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)
                    else:
                        editor.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)
                    
                    # 更新折叠边距
                    if self.settings.get("folding_margin", True):
                        editor.setMarginWidth(1, 20)  # 折叠边距宽度
                    else:
                        editor.setMarginWidth(1, 0)  # 隐藏折叠边距
                    
                    # 更新状态栏显示
                    self.statusBar().setVisible(self.settings.get("show_status_bar", True))
                    
                    # 更新终端设置
                    if hasattr(self, 'terminal_tab') and self.terminal_tab is not None:
                        for i in range(self.terminal_tab.count()):
                            terminal = self.terminal_tab.widget(i)
                            if hasattr(terminal, "output"):
                                # 终端字体设置
                                terminal_font_family = self.settings.get("terminal_font_family", "Consolas")
                                terminal_font_size = self.settings.get("terminal_font_size", 12)
                                terminal.output.setStyleSheet(f"background-color: black; color: white; font-family: {terminal_font_family}; font-size: {terminal_font_size}pt;")
    
    def save_settings(self):
        """保存设置文件"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"保存设置失败: {e}")
    
    def check_auto_open_changes_log(self):
        """检查是否需要自动打开changes.log"""
        if not self.settings.get("changes_log_opened", False):
            # 检查changes.log文件是否存在
            # 处理PyInstaller编译后的情况
            import sys
            if hasattr(sys, '_MEIPASS'):
                # 从编译后的可执行文件运行
                changes_log_path = os.path.join(sys._MEIPASS, "changes.log")
            else:
                # 从源代码运行
                changes_log_path = "changes.log"
            
            if os.path.exists(changes_log_path):
                # 打开changes.log文件
                self.open_specific_file(changes_log_path)
                # 更新设置，标记为已打开
                self.settings["changes_log_opened"] = True
                self.save_settings()
    
    def check_autosave_files(self):
        """检查是否存在自动保存文件"""
        # 遍历当前目录，查找所有.autosave文件
        current_dir = os.getcwd()
        autosave_files = []
        
        try:
            for file in os.listdir(current_dir):
                if file.endswith(".autosave"):
                    autosave_files.append(os.path.join(current_dir, file))
        except Exception as e:
            return
        
        # 处理每个自动保存文件
        for autosave_path in autosave_files:
            original_file = autosave_path[:-9]  # 移除.autosave后缀
            
            # 显示消息框，询问用户如何处理
            msg_box = QMessageBox()
            msg_box.setWindowTitle("发现自动保存文件")
            msg_box.setText(f"发现自动保存文件: {autosave_path}\n\n您想要如何处理？")
            
            # 添加按钮
            open_btn = msg_box.addButton("打开", QMessageBox.ButtonRole.AcceptRole)
            discard_btn = msg_box.addButton("舍弃", QMessageBox.ButtonRole.RejectRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.ActionRole)
            
            msg_box.setDefaultButton(open_btn)
            msg_box.exec()
            
            # 获取用户选择
            clicked_btn = msg_box.clickedButton()
            
            if clicked_btn == open_btn:
                # 打开自动保存文件
                self.open_autosave_file(autosave_path, original_file)
            elif clicked_btn == discard_btn:
                # 舍弃自动保存文件
                try:
                    os.remove(autosave_path)
                    self.statusBar().showMessage(f"已舍弃自动保存文件: {autosave_path}")
                except Exception as e:
                    self.statusBar().showMessage(f"舍弃自动保存文件失败: {str(e)}")
            # 如果用户点击取消，什么都不做
    
    def open_autosave_file(self, autosave_path, original_file):
        """打开自动保存文件"""
        try:
            with open(autosave_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 打开原始文件或创建新标签页
            if os.path.exists(original_file):
                # 打开原始文件
                self.open_specific_file(original_file)
                # 获取最后打开的编辑器
                editor = self.tab_widget.currentWidget()
                # 提示用户是否替换内容
                msg_box = QMessageBox()
                msg_box.setWindowTitle("替换文件内容")
                msg_box.setText(f"是否用自动保存的内容替换 {original_file} 的内容？")
                msg_box.setIcon(QMessageBox.Icon.Question)
                
                yes_btn = msg_box.addButton("是", QMessageBox.ButtonRole.AcceptRole)
                no_btn = msg_box.addButton("否", QMessageBox.ButtonRole.RejectRole)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == yes_btn:
                    editor.setText(content)
                    editor.setModified(True)
                    self.statusBar().showMessage(f"已用自动保存内容替换: {original_file}")
            else:
                # 创建新标签页
                editor = self.setup_editor()
                editor.setText(content)
                editor.current_file = original_file
                editor.setModified(True)
                
                # 获取文件名
                filename = os.path.basename(original_file)
                index = self.tab_widget.addTab(editor, filename)
                self.tab_widget.setCurrentIndex(index)
                self.statusBar().showMessage(f"已打开自动保存文件: {autosave_path}")
            
            # 删除自动保存文件
            try:
                os.remove(autosave_path)
            except Exception as e:
                pass
        except Exception as e:
            self.statusBar().showMessage(f"打开自动保存文件失败: {str(e)}")
    
    def open_specific_file(self, file_path):
        """打开指定文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            editor = self.setup_editor()
            editor.setText(content)
            
            # 自动检测语言
            file_ext = file_path.split('.')[-1].lower() if '.' in file_path else None
            detected_lang = self.detect_language(content, file_ext)
            
            # 设置语言
            self.change_language(detected_lang, editor)
            
            # 获取文件名（处理不同操作系统的路径分隔符）
            if '\\' in file_path:
                filename = file_path.split('\\')[-1]
            else:
                filename = file_path.split('/')[-1]
            
            index = self.tab_widget.addTab(editor, filename)
            self.tab_widget.setCurrentIndex(index)
            editor.current_file = file_path
            # 标记为未修改
            editor.setModified(False)
            self.statusBar().showMessage(f"打开文件: {file_path}")
        except Exception as e:
            self.statusBar().showMessage(f"打开文件失败: {str(e)}")
    
    def init_auto_save(self):
        """初始化自动保存功能"""
        # 创建自动保存定时器
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save_all)
        self.auto_save_timer.start(self.auto_save_interval)
    
    def auto_save_all(self):
        """自动保存所有修改过的文件"""
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if hasattr(editor, 'current_file') and editor.current_file:
                # 检查文件是否被修改
                if editor.isModified():
                    try:
                        # 创建自动保存文件，使用 .autosave 后缀
                        autosave_path = editor.current_file + ".autosave"
                        with open(autosave_path, 'w', encoding='utf-8') as f:
                            f.write(editor.text())
                        self.statusBar().showMessage(f"自动保存: {editor.current_file}")
                    except Exception as e:
                        self.statusBar().showMessage(f"自动保存失败: {str(e)}")
    
    def build_language_menu(self):
        """构建层级语言菜单"""
        for lang_category, sub_langs in self.language_dict.items():
            if sub_langs is None:
                # 无子菜单，直接添加动作
                action = QAction(lang_category, self)
                action.triggered.connect(lambda checked, lang=lang_category: self.change_language(lang))
                self.language_menu.addAction(action)
            else:
                # 创建子菜单
                sub_menu = self.language_menu.addMenu(lang_category)
                for sub_lang in sub_langs:
                    action = QAction(sub_lang, self)
                    action.triggered.connect(lambda checked, lang=sub_lang: self.change_language(lang))
                    sub_menu.addAction(action)
    
    def new_file(self):
        editor = self.setup_editor()
        index = self.tab_widget.addTab(editor, "未命名")
        self.tab_widget.setCurrentIndex(index)
        self.statusBar().showMessage("新建文件")
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "所有文件 (*);;Python 文件 (*.py);;C++ 文件 (*.cpp *.h);;Java 文件 (*.java);;HTML 文件 (*.html);;JavaScript 文件 (*.js)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            editor = self.setup_editor()
            editor.setText(content)
            
            # 自动检测语言
            file_ext = file_path.split('.')[-1].lower() if '.' in file_path else None
            detected_lang = self.detect_language(content, file_ext)
            
            # 设置语言
            self.change_language(detected_lang, editor)
            
            # 获取文件名（处理不同操作系统的路径分隔符）
            if '\\' in file_path:
                filename = file_path.split('\\')[-1]
            else:
                filename = file_path.split('/')[-1]
            
            index = self.tab_widget.addTab(editor, filename)
            self.tab_widget.setCurrentIndex(index)
            editor.current_file = file_path
            # 标记为未修改
            editor.setModified(False)
            self.statusBar().showMessage(f"打开文件: {file_path}")
    
    def save_file(self):
        editor = self.tab_widget.currentWidget()
        if hasattr(editor, 'current_file') and editor.current_file:
            with open(editor.current_file, 'w', encoding='utf-8') as f:
                f.write(editor.text())
            # 标记为未修改
            editor.setModified(False)
            # 删除对应的自动保存文件
            autosave_path = editor.current_file + ".autosave"
            if os.path.exists(autosave_path):
                try:
                    os.remove(autosave_path)
                except Exception as e:
                    pass
            self.statusBar().showMessage(f"保存文件: {editor.current_file}")
        else:
            self.save_as_file()
    
    def save_as_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "另存为", "", "所有文件 (*);;Python 文件 (*.py);;C++ 文件 (*.cpp);;Java 文件 (*.java);;HTML 文件 (*.html);;JavaScript 文件 (*.js)")
        if file_path:
            editor = self.tab_widget.currentWidget()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(editor.text())
            editor.current_file = file_path
            # 标记为未修改
            editor.setModified(False)
            # 删除对应的自动保存文件
            autosave_path = file_path + ".autosave"
            if os.path.exists(autosave_path):
                try:
                    os.remove(autosave_path)
                except Exception as e:
                    pass
            # 获取文件名（处理不同操作系统的路径分隔符）
            if '\\' in file_path:
                filename = file_path.split('\\')[-1]
            else:
                filename = file_path.split('/')[-1]
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), filename)
            self.statusBar().showMessage(f"保存文件: {file_path}")
    
    def close_tab(self, index):
        self.tab_widget.removeTab(index)
    
    def undo(self):
        editor = self.tab_widget.currentWidget()
        editor.undo()
    
    def redo(self):
        editor = self.tab_widget.currentWidget()
        editor.redo()
    
    def on_tab_changed(self, index):
        # 标签页切换时更新状态栏
        editor = self.tab_widget.currentWidget()
        if editor:
            editor.update_status()
    
    def detect_language(self, content, file_ext=None):
        """根据文件内容和扩展名自动检测编程语言"""
        # 优先根据扩展名检测
        if file_ext:
            ext_map = {
                'py': 'Python',
                'cpp': 'C++',
                'h': 'C++',
                'hpp': 'C++',
                'java': 'Java',
                'html': 'HTML',
                'htm': 'HTML',
                'js': 'JavaScript',
                'json': 'JavaScript',
                'xml': 'XML',
                'md': 'Markdown (preinstalled)',
                'markdown': 'Markdown (preinstalled)'
            }
            if file_ext in ext_map:
                return ext_map[file_ext]
        
        # 根据内容检测
        content_lower = content.lower()
        
        # 检测Python
        if 'import ' in content_lower or 'def ' in content_lower or 'class ' in content_lower:
            if 'print(' in content_lower or 'from ' in content_lower:
                return 'Python'
        
        # 检测C++
        if '#include' in content_lower or 'using namespace' in content_lower or 'int main(' in content_lower:
            return 'C++'
        
        # 检测Java
        if 'public class' in content_lower or 'public static void main' in content_lower:
            return 'Java'
        
        # 检测HTML
        if '<html' in content_lower or '<body' in content_lower or '<div' in content_lower:
            return 'HTML'
        
        # 检测XML
        if '<?xml' in content_lower or '<root' in content_lower or '<tag' in content_lower:
            return 'XML'
        
        # 检测Markdown
        if '#' in content_lower or '**' in content_lower or '* ' in content_lower or '> ' in content_lower:
            return 'Markdown (preinstalled)'
        
        # 检测JavaScript
        if 'function ' in content_lower or 'var ' in content_lower or 'let ' in content_lower or 'const ' in content_lower:
            return 'JavaScript'
        
        # 默认返回普通文本
        return 'None (Normal Text)'
    
    def change_language(self, language, editor=None):
        if editor is None:
            editor = self.tab_widget.currentWidget()
        
        font = editor.font()
        
        # 更新当前编辑器的语言属性
        editor.current_language = language
        
        # 根据选择的语言设置对应的lexer
        if language == "None (Normal Text)":
            editor.setLexer(None)  # 普通文本，无语法高亮
        elif language == "Python":
            from PyQt6.Qsci import QsciLexerPython
            lexer = QsciLexerPython()
            lexer.setFont(font)
            editor.setLexer(lexer)
        elif language == "C++" or language == "C":
            from PyQt6.Qsci import QsciLexerCPP
            lexer = QsciLexerCPP()
            lexer.setFont(font)
            editor.setLexer(lexer)
        elif language == "Java":
            from PyQt6.Qsci import QsciLexerJava
            lexer = QsciLexerJava()
            lexer.setFont(font)
            editor.setLexer(lexer)
        elif language == "HTML":
            from PyQt6.Qsci import QsciLexerHTML
            lexer = QsciLexerHTML()
            lexer.setFont(font)
            # 设置HTML lexer支持嵌入CSS和JavaScript
            try:
                # 启用HTML中的CSS和JavaScript支持
                lexer.setDefaultPaper(editor.paper())
                lexer.setDefaultColor(editor.color())
            except AttributeError:
                pass
            editor.setLexer(lexer)
        elif language == "JavaScript" or language == "JSON" or language == "JSON5":
            from PyQt6.Qsci import QsciLexerJavaScript
            lexer = QsciLexerJavaScript()
            lexer.setFont(font)
            editor.setLexer(lexer)
        elif language == "XML":
            from PyQt6.Qsci import QsciLexerXML
            lexer = QsciLexerXML()
            lexer.setFont(font)
            editor.setLexer(lexer)
        elif "Markdown" in language or language == "Markdown":
            try:
                from PyQt6.Qsci import QsciLexerMarkdown
                lexer = QsciLexerMarkdown()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                # 如果没有Markdown lexer，使用HTML或普通文本
                editor.setLexer(None)
        elif language == "CSS":
            from PyQt6.Qsci import QsciLexerCSS
            lexer = QsciLexerCSS()
            lexer.setFont(font)
            # 设置CSS lexer的颜色主题
            try:
                # 确保CSS语法高亮颜色鲜明
                lexer.setColor(QColor(0, 0, 128), QsciLexerCSS.ColorProperty)
                lexer.setColor(QColor(0, 128, 0), QsciLexerCSS.ColorComment)
                lexer.setColor(QColor(128, 0, 0), QsciLexerCSS.ColorKeyword)
                lexer.setColor(QColor(0, 0, 0), QsciLexerCSS.ColorDefault)
            except AttributeError:
                pass
            editor.setLexer(lexer)
        elif language == "PHP":
            try:
                from PyQt6.Qsci import QsciLexerPHP
                lexer = QsciLexerPHP()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Bash" or language == "Shell" or language == "Batch":
            try:
                from PyQt6.Qsci import QsciLexerBash
                lexer = QsciLexerBash()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "SQL":
            try:
                from PyQt6.Qsci import QsciLexerSQL
                lexer = QsciLexerSQL()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Perl":
            try:
                from PyQt6.Qsci import QsciLexerPerl
                lexer = QsciLexerPerl()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Ruby":
            try:
                from PyQt6.Qsci import QsciLexerRuby
                lexer = QsciLexerRuby()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Lua":
            try:
                from PyQt6.Qsci import QsciLexerLua
                lexer = QsciLexerLua()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Rust":
            try:
                from PyQt6.Qsci import QsciLexerRust
                lexer = QsciLexerRust()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Go":
            try:
                from PyQt6.Qsci import QsciLexerGo
                lexer = QsciLexerGo()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Swift":
            try:
                from PyQt6.Qsci import QsciLexerSwift
                lexer = QsciLexerSwift()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Kotlin":
            try:
                from PyQt6.Qsci import QsciLexerKotlin
                lexer = QsciLexerKotlin()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "R":
            try:
                from PyQt6.Qsci import QsciLexerR
                lexer = QsciLexerR()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
        elif language == "Asm" or language == "NASM":
            try:
                # 尝试使用其他合适的lexer来处理汇编语言，因为QsciLexerAsm是抽象类
                from PyQt6.Qsci import QsciLexerCPP
                lexer = QsciLexerCPP()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                # 如果没有合适的lexer，使用默认设置
                editor.setLexer(None)
        else:
            # 对于其他语言选项，尝试使用通用的lexer或默认lexer
            editor.setLexer(None)
        
        # 更新状态栏显示
        if hasattr(self, 'status_info'):
            self.status_info["type"].setText(f"{language} file")
        
        # 更新当前语言标签
        if hasattr(self, 'current_language_label'):
            self.current_language_label.setText(language)
        
        # 更新HTML运行按钮可见性
        if hasattr(self, 'run_html_action'):
            self.run_html_action.setVisible(language == "HTML")
        
        # 更新Python运行按钮可见性
        if hasattr(self, 'run_python_action'):
            self.run_python_action.setVisible(language == "Python")
        
        # 更新运行菜单可见性
        # 运行菜单已被删除，不再需要更新可见性
    
    def run_html_in_browser(self):
        """在浏览器中打开当前HTML文件"""
        editor = self.tab_widget.currentWidget()
        if editor and hasattr(editor, 'current_file') and editor.current_file:
            # 保存文件
            self.save_file()
            
            # 在浏览器中打开
            import webbrowser
            webbrowser.open(editor.current_file)
        else:
            self.statusBar().showMessage("请先保存HTML文件")
    
    def run_python_file(self):
        """运行当前Python文件，允许选择解释器"""
        editor = self.tab_widget.currentWidget()
        if editor and hasattr(editor, 'current_file') and editor.current_file:
            # 保存文件
            self.save_file()
            
            # 检查是否是Python文件
            file_ext = editor.current_file.split('.')[-1].lower() if '.' in editor.current_file else None
            if file_ext != 'py':
                self.statusBar().showMessage("当前文件不是Python文件")
                return
            
            # 获取Python解释器路径
            python_interpreter = self.get_python_interpreter()
            if not python_interpreter:
                return
            
            # 显示终端
            self.terminal_dock.setVisible(True)
            
            # 获取当前终端或创建新终端
            if self.terminal_tab.count() == 0:
                self.add_terminal_tab()
            terminal = self.terminal_tab.currentWidget()
            
            # 运行Python文件
            command = f'{python_interpreter} "{editor.current_file}"\n'
            terminal.process.write(command.encode('utf-8'))
            
            self.statusBar().showMessage(f"正在运行Python文件: {editor.current_file}")
        else:
            self.statusBar().showMessage("请先保存Python文件")
    
    def get_python_interpreter(self):
        """获取Python解释器路径，允许用户选择"""
        import sys
        import os
        
        # 查找系统中的Python解释器
        python_paths = []
        
        # 添加当前Python解释器
        python_paths.append(sys.executable)
        
        # 检查常见的Python安装路径
        common_paths = [
            'python',
            'python3',
            'python3.11',
            'python3.10',
            'python3.9',
            os.path.join('C:\\Python311', 'python.exe'),
            os.path.join('C:\\Python310', 'python.exe'),
            os.path.join('C:\\Python39', 'python.exe'),
            os.path.join('C:\\Program Files', 'Python311', 'python.exe'),
            os.path.join('C:\\Program Files', 'Python310', 'python.exe'),
            os.path.join('C:\\Program Files', 'Python39', 'python.exe'),
        ]
        
        # 检查常见路径是否存在
        for path in common_paths:
            if os.path.exists(path) or (path in ['python', 'python3']):
                python_paths.append(path)
        
        # 去重
        python_paths = list(set(python_paths))
        
        # 显示选择对话框
        from PyQt6.QtWidgets import QInputDialog
        interpreter, ok = QInputDialog.getItem(
            self,
            "选择Python解释器",
            "请选择要使用的Python解释器:",
            python_paths,
            0,
            False
        )
        
        if ok and interpreter:
            return interpreter
        else:
            return None
    
    def add_terminal_tab(self):
        """添加新的终端标签页"""
        terminal = TerminalWidget()
        index = self.terminal_tab.addTab(terminal, f"终端 {self.terminal_tab.count() + 1}")
        self.terminal_tab.setCurrentIndex(index)
    
    def close_terminal_tab(self, index):
        """关闭终端标签页"""
        if self.terminal_tab.count() > 1:  # 至少保留一个终端
            self.terminal_tab.removeTab(index)
    
    def check_syntax(self, editor=None):
        """检查当前文件的语法"""
        # 获取当前编辑器
        if editor is None:
            editor = self.tab_widget.currentWidget()
        if not editor:
            self.statusBar().showMessage("没有打开的文件")
            return
        
        # 获取文件内容
        content = editor.text()
        if not content:
            self.statusBar().showMessage("文件内容为空")
            return
        
        # 获取当前语言
        current_lang = self.current_language_label.text()
        problems = []
        
        # 根据语言选择语法检查器
        if "Python" in current_lang:
            problems = self.check_python_syntax(content)
        elif "C++" in current_lang or "C" in current_lang:
            problems = self.check_cpp_syntax(content)
        elif "Java" in current_lang:
            problems = self.check_java_syntax(content)
        elif "HTML" in current_lang:
            problems = self.check_html_syntax(content)
        elif "JavaScript" in current_lang or "JSON" in current_lang:
            problems = self.check_javascript_syntax(content)
        elif "CSS" in current_lang:
            problems = self.check_css_syntax(content)
        elif "PHP" in current_lang:
            problems = self.check_php_syntax(content)
        elif "Bash" in current_lang or "Shell" in current_lang or "Batch" in current_lang:
            problems = self.check_bash_syntax(content)
        elif "SQL" in current_lang:
            problems = self.check_sql_syntax(content)
        elif "Asm" in current_lang or "NASM" in current_lang:
            problems = self.check_asm_syntax(content)
        elif "QML" in current_lang:
            problems = self.check_qml_syntax(content)
        else:
            # 为其他语言提供基本的语法检查
            problems = self.check_generic_syntax(content, current_lang)
        
        # 显示语法检查结果
        self.show_syntax_errors(problems)
    
    def check_python_syntax(self, content):
        """检查Python语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 1. 先进行简单的静态检查
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 检查未闭合的字符串
            if stripped_line.count('"') % 2 != 0 or stripped_line.count("'") % 2 != 0:
                # 检查是否是注释
                if not stripped_line.startswith('#'):
                    problems.append((line_num, 1, "可能存在未闭合的字符串", "error"))
            
            # 检查缩进问题（简单示例）
            if line and not line.startswith(' ') and not line.startswith('\t') and not stripped_line.startswith('#'):
                # 检查是否是类或函数定义
                if not any(keyword in stripped_line for keyword in ['class ', 'def ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ', 'lambda ']):
                    problems.append((line_num, 1, "可能存在缩进问题", "warning"))
            
            # 检查print语句（Python 3中应该使用print()函数）
            if 'print ' in line and not 'print(' in line:
                problems.append((line_num, line.find('print') + 1, "Python 3中print应该使用括号", "warning"))
            
            # 检查比较运算符
            if '=' in line and not '==' in line and not '!=' in line and not '<=' in line and not '>=' in line and not '+=' in line and not '-=' in line and not '*=' in line and not '/=' in line:
                # 检查是否是赋值语句
                if 'if ' in line or 'elif ' in line or 'while ' in line:
                    problems.append((line_num, line.find('=') + 1, "可能应该使用==而不是=", "warning"))
        
        # 2. 使用compile函数进行更精确的语法检查
        try:
            compile(content, '<string>', 'exec')
        except SyntaxError as e:
            # 解析语法错误，提供更详细的信息
            error_msg = f"语法错误: {e.msg}"
            # 根据错误类型提供更友好的提示
            if "unexpected EOF" in e.msg:
                error_msg = "语法错误: 遇到了意外的文件结束，可能缺少闭合括号、引号或缩进块"
            elif "expected an indented block" in e.msg:
                error_msg = "语法错误: 期望有缩进块，可能缺少冒号或缩进"
            elif "invalid syntax" in e.msg:
                error_msg = f"语法错误: 无效的语法，位置 {e.offset}"
            problems.append((e.lineno, e.offset, error_msg, "error"))
        except Exception as e:
            # 其他错误
            problems.append((1, 1, f"未知错误: {str(e)}", "error"))
        
        return problems
    
    def check_cpp_syntax(self, content):
        """检查C++语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 跟踪括号匹配
        brace_stack = []
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 跳过注释行
            if stripped_line.startswith('//') or stripped_line.startswith('/*') or stripped_line.startswith('*'):
                continue
            
            # 检查括号匹配
            for char_pos, char in enumerate(line):
                if char in '([{':
                    brace_stack.append((char, line_num, char_pos + 1))
                elif char in ')]}':
                    if not brace_stack:
                        problems.append((line_num, char_pos + 1, "多余的右括号", "error"))
                    else:
                        open_brace, open_line, open_pos = brace_stack.pop()
                        if (open_brace == '(' and char != ')') or \
                           (open_brace == '[' and char != ']') or \
                           (open_brace == '{' and char != '}'):
                            problems.append((line_num, char_pos + 1, f"括号不匹配: {open_brace} 和 {char}", "error"))
            
            # 检查分号
            if stripped_line and not stripped_line.endswith(';') and not stripped_line.endswith('{') and not stripped_line.endswith('}') and not stripped_line.startswith('#') and not '(' in stripped_line:
                # 检查是否是控制流语句
                if not any(keyword in stripped_line for keyword in ['if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break', 'continue', 'return', 'goto', 'try', 'catch', 'throw', 'new', 'delete', 'class', 'struct', 'enum', 'union', 'typedef', 'namespace', 'using', 'template', 'extern', 'inline', 'static', 'const', 'volatile', 'mutable', 'friend', 'virtual', 'override', 'final', 'explicit', 'constexpr', 'consteval', 'constinit', 'noexcept', 'decltype', 'auto', 'declspec', '__declspec', '__attribute__']):
                    problems.append((line_num, len(line), "可能缺少分号", "warning"))
            
            # 检查常见的C++语法问题
            
            # 检查cout/cin流操作符
            if 'cout' in line or 'cin' in line:
                if '<<' not in line and '>>' not in line:
                    problems.append((line_num, line.find('cout') + 1 if 'cout' in line else line.find('cin') + 1, "可能缺少流操作符 << 或 >>", "warning"))
            
            # 检查比较运算符
            if '=' in line and not '==' in line and not '!=' in line and not '<=' in line and not '>=' in line and not '+=' in line and not '-=' in line and not '*=' in line and not '/=' in line:
                # 检查是否是条件语句
                if any(keyword in stripped_line for keyword in ['if', 'else if', 'while', 'for', 'switch', 'case']):
                    problems.append((line_num, line.find('=') + 1, "条件语句中可能应该使用==而不是=", "warning"))
            
            # 检查未初始化的变量
            if any(type_keyword in line for type_keyword in ['int ', 'float ', 'double ', 'char ', 'bool ', 'short ', 'long ', 'unsigned ', 'signed ', 'void ', 'auto ', 'const ', 'volatile ', 'mutable ', 'static ', 'extern ']) and '=' not in line and '(' not in line:
                # 检查是否是变量声明
                if not any(keyword in stripped_line for keyword in ['class', 'struct', 'enum', 'union', 'typedef', 'namespace', 'using', 'template', 'friend', 'virtual', 'override', 'final', 'explicit', 'constexpr', 'consteval', 'constinit', 'noexcept', 'decltype', 'declspec', '__declspec', '__attribute__']):
                    problems.append((line_num, 1, "可能存在未初始化的变量", "warning"))
        
        # 检查未闭合的括号
        for open_brace, open_line, open_pos in brace_stack:
            problems.append((open_line, open_pos, f"未闭合的括号: {open_brace}", "error"))
        
        return problems
    
    def check_java_syntax(self, content):
        """检查Java语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 跟踪括号匹配
        brace_stack = []
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 跳过注释行
            if stripped_line.startswith('//') or stripped_line.startswith('/*') or stripped_line.startswith('*'):
                continue
            
            # 检查括号匹配
            for char_pos, char in enumerate(line):
                if char in '([{':
                    brace_stack.append((char, line_num, char_pos + 1))
                elif char in ')]}':
                    if not brace_stack:
                        problems.append((line_num, char_pos + 1, "多余的右括号", "error"))
                    else:
                        open_brace, open_line, open_pos = brace_stack.pop()
                        if (open_brace == '(' and char != ')') or \
                           (open_brace == '[' and char != ']') or \
                           (open_brace == '{' and char != '}'):
                            problems.append((line_num, char_pos + 1, f"括号不匹配: {open_brace} 和 {char}", "error"))
            
            # 检查分号
            if stripped_line and not stripped_line.endswith(';') and not stripped_line.endswith('{') and not stripped_line.endswith('}') and not stripped_line.startswith('package') and not stripped_line.startswith('import'):
                # 检查是否是控制流语句
                if not any(keyword in stripped_line for keyword in ['if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break', 'continue', 'return', 'throw', 'try', 'catch', 'finally', 'synchronized', 'class', 'interface', 'enum', 'record', 'annotation', 'extends', 'implements', 'throws', 'native', 'abstract', 'final', 'static', 'private', 'protected', 'public', 'default', 'strictfp', 'transient', 'volatile', 'synchronized', 'instanceof', 'new', 'super', 'this', 'assert', 'var', 'const', 'goto']):
                    problems.append((line_num, len(line), "可能缺少分号", "warning"))
            
            # 检查常见的Java语法问题
            
            # 检查比较运算符
            if '=' in line and not '==' in line and not '!=' in line and not '<=' in line and not '>=' in line and not '+=' in line and not '-=' in line and not '*=' in line and not '/=' in line:
                # 检查是否是条件语句
                if any(keyword in stripped_line for keyword in ['if', 'else if', 'while', 'for', 'switch', 'case']):
                    problems.append((line_num, line.find('=') + 1, "条件语句中可能应该使用==而不是=", "warning"))
            
            # 检查未初始化的变量
            if any(type_keyword in line for type_keyword in ['int ', 'float ', 'double ', 'char ', 'boolean ', 'short ', 'long ', 'byte ', 'void ', 'var ', 'private ', 'protected ', 'public ', 'static ', 'final ', 'abstract ', 'synchronized ', 'transient ', 'volatile ', 'native ', 'strictfp ', 'default ', 'record ', 'enum ', 'interface ', 'class ']) and '=' not in line and '(' not in line:
                # 检查是否是变量声明
                if not any(keyword in stripped_line for keyword in ['class', 'interface', 'enum', 'record', 'annotation', 'extends', 'implements', 'throws', 'native', 'abstract', 'final', 'static', 'private', 'protected', 'public', 'default', 'strictfp', 'transient', 'volatile', 'synchronized', 'instanceof', 'new', 'super', 'this', 'assert', 'var', 'const', 'goto']):
                    problems.append((line_num, 1, "可能存在未初始化的变量", "warning"))
            
            # 检查Java关键字使用
            if 'public' in line or 'protected' in line or 'private' in line:
                # 检查访问修饰符位置
                if not any(keyword in line for keyword in ['class ', 'interface ', 'enum ', 'record ', 'annotation ', 'void ', 'int ', 'float ', 'double ', 'char ', 'boolean ', 'short ', 'long ', 'byte ', 'var ']):
                    problems.append((line_num, line.find('public') + 1 if 'public' in line else line.find('protected') + 1 if 'protected' in line else line.find('private') + 1, "访问修饰符应该用于类、接口或方法", "warning"))
        
        # 检查未闭合的括号
        for open_brace, open_line, open_pos in brace_stack:
            problems.append((open_line, open_pos, f"未闭合的括号: {open_brace}", "error"))
        
        return problems
    
    def check_html_syntax(self, content):
        """检查HTML语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 跟踪HTML标签嵌套
        tag_stack = []
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 跳过注释行
            if stripped_line.startswith('<!--'):
                continue
            
            # 简单的HTML标签检查
            if '<' in line and '>' in line:
                # 解析当前行的标签
                parts = line.split('<')
                for part in parts[1:]:
                    if '>' in part:
                        tag_part = part.split('>')[0]
                        
                        # 跳过自闭合标签和特殊标签
                        if tag_part.startswith('/'):
                            # 闭合标签
                            close_tag = tag_part[1:].split(' ')[0]
                            if not tag_stack:
                                problems.append((line_num, line.find(f'</{close_tag}') + 1, f"多余的闭合标签 </{close_tag}>", "error"))
                            else:
                                open_tag = tag_stack.pop()
                                if open_tag != close_tag:
                                    problems.append((line_num, line.find(f'</{close_tag}') + 1, f"标签不匹配: <{open_tag}> 和 </{close_tag}>", "error"))
                        elif not any(keyword in tag_part for keyword in ['!DOCTYPE', '!doctype', '!--', 'meta', 'link', 'br', 'hr', 'img', 'input', 'area', 'base', 'col', 'command', 'embed', 'keygen', 'param', 'source', 'track', 'wbr']):
                            # 开始标签（非自闭合）
                            open_tag = tag_part.split(' ')[0].split('/')[0]
                            if open_tag:
                                tag_stack.append(open_tag)
        
        # 检查未闭合的标签
        for tag in tag_stack:
            problems.append((len(lines), 1, f"未闭合的标签: <{tag}>", "error"))
        
        # 检查常见的HTML语法问题
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 检查DOCTYPE声明
            if line_num == 1 and not any(keyword in stripped_line.lower() for keyword in ['<!doctype', '<!DOCTYPE']):
                problems.append((line_num, 1, "建议添加DOCTYPE声明", "warning"))
            
            # 检查标签嵌套
            if '<html' in stripped_line.lower() and '</html>' in stripped_line.lower():
                problems.append((line_num, line.find('<html') + 1, "HTML标签不应该在同一行闭合", "warning"))
            
            # 检查属性引号
            if '<' in line and '=' in line:
                # 简单检查属性引号
                parts = line.split('<')
                for part in parts[1:]:
                    if '=' in part and '>' in part:
                        tag_part = part.split('>')[0]
                        attrs = tag_part.split(' ')
                        for attr in attrs[1:]:  # 跳过标签名
                            if '=' in attr:
                                attr_name, attr_value = attr.split('=', 1)
                                # 检查属性值是否有引号
                                if attr_value and not (attr_value.startswith('"') or attr_value.startswith("'")):
                                    problems.append((line_num, line.find(attr) + 1, f"属性值 '{attr_name}' 建议使用引号", "warning"))
        
        return problems
    
    def check_javascript_syntax(self, content):
        """检查JavaScript语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 跟踪括号匹配
        brace_stack = []
        
        # 1. 先进行静态检查
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 跳过注释行
            if stripped_line.startswith('//') or stripped_line.startswith('/*') or stripped_line.startswith('*'):
                continue
            
            # 检查括号匹配
            for char_pos, char in enumerate(line):
                if char in '([{':
                    brace_stack.append((char, line_num, char_pos + 1))
                elif char in ')]}':
                    if not brace_stack:
                        problems.append((line_num, char_pos + 1, "多余的右括号", "error"))
                    else:
                        open_brace, open_line, open_pos = brace_stack.pop()
                        if (open_brace == '(' and char != ')') or \
                           (open_brace == '[' and char != ']') or \
                           (open_brace == '{' and char != '}'):
                            problems.append((line_num, char_pos + 1, f"括号不匹配: {open_brace} 和 {char}", "error"))
            
            # 检查常见的JavaScript语法问题
            
            # 检查比较运算符
            if '=' in line and not '==' in line and not '!=' in line and not '<=' in line and not '>=' in line and not '+=' in line and not '-=' in line and not '*=' in line and not '/=' in line:
                # 检查是否是条件语句
                if any(keyword in stripped_line for keyword in ['if', 'else if', 'while', 'for', 'switch', 'case']):
                    problems.append((line_num, line.find('=') + 1, "条件语句中可能应该使用==而不是=", "warning"))
            
            # 检查var关键字（建议使用let或const）
            if 'var ' in line:
                problems.append((line_num, line.find('var') + 1, "建议使用let或const代替var", "warning"))
            
            # JavaScript不需要强制分号，移除分号警告
            # 只检查其他语法问题
        
        # 检查未闭合的括号
        for open_brace, open_line, open_pos in brace_stack:
            problems.append((open_line, open_pos, f"未闭合的括号: {open_brace}", "error"))
        
        # 2. 使用eval进行更精确的语法检查
        try:
            # 简单的JavaScript语法检查，使用eval尝试执行（仅用于语法检查）
            eval(content)
        except SyntaxError as e:
            # 解析语法错误，提供更详细的信息
            error_msg = f"语法错误: {e.msg}"
            # 根据错误类型提供更友好的提示
            if "unexpected end of input" in e.msg:
                error_msg = "语法错误: 遇到了意外的输入结束，可能缺少闭合括号、引号或代码块"
            elif "expected expression" in e.msg:
                error_msg = "语法错误: 期望有表达式，可能缺少运算符或括号"
            elif "invalid left-hand side in assignment" in e.msg:
                error_msg = "语法错误: 赋值语句左侧无效，可能是语法错误或使用了保留字"
            problems.append((1, 1, error_msg, "error"))
        except Exception:
            # 忽略运行时错误，只关注语法错误
            pass
        
        return problems
    
    def check_css_syntax(self, content):
        """检查CSS语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 跟踪CSS括号匹配
        brace_stack = []
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # 跳过注释行
            if stripped_line.startswith('/*') or stripped_line.startswith('//'):
                continue
            
            # 检查括号匹配
            for char_pos, char in enumerate(line):
                if char == '{':
                    brace_stack.append((char, line_num, char_pos + 1))
                elif char == '}':
                    if not brace_stack:
                        problems.append((line_num, char_pos + 1, "多余的右括号", "error"))
                    else:
                        open_brace, open_line, open_pos = brace_stack.pop()
            
            # 检查常见的CSS语法问题
            
            # 检查CSS属性格式
            if ':' in line and not line.strip().startswith('/*') and not line.strip().startswith('//'):
                # 检查是否有多个冒号
                if line.count(':') > 1:
                    problems.append((line_num, line.find(':') + 1, "CSS属性中不应有多个冒号", "warning"))
                
                # CSS不需要强制分号，移除分号警告
            
            # 检查CSS选择器
            if '{' in line and not line.strip().startswith('/*') and not line.strip().startswith('//'):
                selector = line.split('{')[0].strip()
                if selector:
                    # 检查选择器是否包含非法字符
                    if any(char in selector for char in ['(', ')', '^', '$', '*', '+', '?', '.', '|', '\\', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '=', '[', ']', '{', '}', '|', '\\', ';', ':', '"', "'", '<', '>', ',', '.', '/', '?', '~', '`', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '+', '=', '[', ']', '{', '}', '|', '\\', ';', ':', '"', "'", '<', '>', ',', '.', '/', '?', '~', '`']):
                        # 跳过合法的CSS选择器符号
                        if not any(keyword in selector for keyword in ['#', '.', '>', '+', '~', ' ', '*', '[', ']', ':', '::', '^=', '$=', '*=', '~=', '|=', '=']):
                            problems.append((line_num, 1, "可能存在无效的CSS选择器", "warning"))
        
        # 检查未闭合的括号
        for open_brace, open_line, open_pos in brace_stack:
            problems.append((open_line, open_pos, "未闭合的左括号", "error"))
        
        return problems
    
    def check_php_syntax(self, content):
        """检查PHP语法（简单实现）"""
        problems = []
        # 简单的PHP语法检查示例
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # 检查缺少分号（简单示例）
            if line.strip() and not line.strip().endswith(';') and not line.strip().endswith('{') and not line.strip().endswith('}') and not line.strip().startswith('//') and not line.strip().startswith('/*') and not line.strip().startswith('<?php') and not line.strip().startswith('?>'):
                problems.append((line_num, len(line), "可能缺少分号", "warning"))
        return problems
    
    def check_bash_syntax(self, content):
        """检查Bash/Shell语法（简单实现）"""
        problems = []
        # 简单的Bash语法检查示例
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # 检查缺少空格（简单示例）
            if '=' in line and not any(operator in line for operator in ['==', '!=', '<', '>', '<=', '>=']):
                # 检查变量赋值是否缺少空格
                parts = line.split('=')
                if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                    if parts[0][-1] != ' ' and parts[1][0] != ' ':
                        problems.append((line_num, line.find('=') + 1, "变量赋值建议使用空格分隔", "warning"))
        return problems
    
    def check_sql_syntax(self, content):
        """检查SQL语法（简单实现）"""
        problems = []
        # 简单的SQL语法检查示例
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # 检查缺少分号（简单示例）
            if line.strip() and not line.strip().endswith(';') and not line.strip().startswith('--'):
                problems.append((line_num, len(line), "可能缺少分号", "warning"))
        return problems
    
    def check_asm_syntax(self, content):
        """检查汇编语言语法（简单实现）"""
        problems = []
        # 简单的汇编语言语法检查示例
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # 检查常见的汇编语言语法问题
            line_stripped = line.strip()
            
            # 检查注释格式
            if line_stripped.startswith(';'):
                # 注释行，跳过检查
                continue
            
            # 检查指令格式（简单示例）
            if line_stripped and not any(prefix in line_stripped for prefix in ['mov', 'add', 'sub', 'mul', 'div', 'push', 'pop', 'ret', 'jmp', 'je', 'jne', 'jl', 'jg', 'call', 'int', 'db', 'dw', 'dd', 'dq', 'section', 'global', 'extern']):
                # 检查是否是标签
                if ':' in line_stripped:
                    # 可能是标签，跳过检查
                    continue
                else:
                    problems.append((line_num, 1, "可能是无效的汇编指令", "warning"))
        return problems
    
    def check_generic_syntax(self, content, language):
        """通用语法检查，适用于所有语言"""
        problems = []
        lines = content.split('\n')
        
        # 检查常见的语法问题
        for line_num, line in enumerate(lines, 1):
            # 检查行尾空格
            if line.endswith(' '):
                problems.append((line_num, len(line), "行尾存在空格", "warning"))
            # 检查制表符使用
            if '\t' in line:
                problems.append((line_num, line.find('\t') + 1, "建议使用空格代替制表符", "warning"))
        
        # 在状态栏显示信息
        self.statusBar().showMessage(f"{language}语法检查完成，发现 {len(problems)} 个问题")
        return problems
    
    def apply_initial_theme(self):
        """应用初始主题"""
        # 根据当前设置设置主题
        if self.settings.get("theme", "light") == "light":
            self.light_theme_action.setChecked(True)
            self.switch_theme("light")
        else:
            self.dark_theme_action.setChecked(True)
            self.switch_theme("dark")
    
    def switch_theme(self, theme):
        """切换IDE主题"""
        from PyQt6.QtGui import QPalette, QColor
        
        # 更新设置
        self.settings["theme"] = theme
        self.save_settings()
        
        # 更新主题菜单项的选中状态
        self.light_theme_action.setChecked(theme == "light")
        self.dark_theme_action.setChecked(theme == "dark")
        
        # 定义主题颜色
        if theme == "light":
            # 亮色主题
            editor_bg = QColor(255, 255, 255)  # 白色背景
            editor_fg = QColor(0, 0, 0)  # 黑色前景
            terminal_bg = QColor(0, 0, 0)  # 终端保持黑色
            terminal_fg = QColor(255, 255, 255)  # 终端保持白色文字
            margin_bg = QColor(240, 240, 240)  # 浅灰色边距
            caret_line_bg = QColor(250, 250, 200)  # 浅黄色光标行
            indent_guide = QColor(200, 200, 200)  # 浅灰色缩进指南
            list_bg = QColor(255, 255, 255)  # 白色列表背景
            list_fg = QColor(0, 0, 0)  # 黑色列表文字
        else:
            # 暗色主题
            editor_bg = QColor(30, 30, 30)  # 深灰色背景
            editor_fg = QColor(200, 200, 200)  # 浅灰色前景
            terminal_bg = QColor(0, 0, 0)  # 终端保持黑色
            terminal_fg = QColor(255, 255, 255)  # 终端保持白色文字
            margin_bg = QColor(50, 50, 50)  # 深灰色边距
            caret_line_bg = QColor(50, 50, 70)  # 深蓝色光标行
            indent_guide = QColor(70, 70, 70)  # 深灰色缩进指南
            list_bg = QColor(30, 30, 30)  # 深灰色列表背景
            list_fg = QColor(200, 200, 200)  # 浅灰色列表文字
        
        # 更新所有编辑器的主题
        if hasattr(self, 'tab_widget') and self.tab_widget is not None:
            for i in range(self.tab_widget.count()):
                editor = self.tab_widget.widget(i)
                if hasattr(editor, "setPaper"):
                    # 更新编辑器背景色
                    editor.setPaper(editor_bg)
                    editor.setColor(editor_fg)
                    
                    # 更新边距颜色
                    editor.setMarginsBackgroundColor(margin_bg)
                    
                    # 更新光标行颜色
                    editor.setCaretLineBackgroundColor(caret_line_bg)
                    
                    # 更新缩进指南颜色
                    editor.setIndentationGuidesBackgroundColor(indent_guide)
                    
                    # 更新语法高亮颜色
                    lexer = editor.lexer()
                    if lexer:
                        # 设置lexer的基本颜色
                        lexer.setDefaultPaper(editor_bg)
                        lexer.setDefaultColor(editor_fg)
                        
                        # 针对不同类型的lexer设置特定颜色
                        try:
                            from PyQt6.Qsci import QsciLexerHTML, QsciLexerCSS, QsciLexerJavaScript
                            
                            if isinstance(lexer, QsciLexerHTML):
                                # HTML lexer特定颜色设置 - 更亮的颜色
                                lexer.setColor(QColor(255, 0, 0), QsciLexerHTML.ColorTag)  # 亮红色标签
                                lexer.setColor(QColor(0, 128, 255), QsciLexerHTML.ColorAttribute)  # 亮蓝色属性
                                lexer.setColor(QColor(0, 200, 0), QsciLexerHTML.ColorComment)  # 亮绿色注释
                                lexer.setColor(QColor(255, 255, 0), QsciLexerHTML.ColorEntity)  # 亮黄色实体
                                lexer.setColor(QColor(0, 255, 255), QsciLexerHTML.ColorNumber)  # 亮青色数字
                                lexer.setColor(QColor(255, 0, 255), QsciLexerHTML.ColorString)  # 亮紫色字符串
                            elif isinstance(lexer, QsciLexerCSS):
                                # CSS lexer特定颜色设置 - 更亮的颜色
                                lexer.setColor(QColor(0, 128, 255), QsciLexerCSS.ColorProperty)  # 亮蓝色属性
                                lexer.setColor(QColor(0, 200, 0), QsciLexerCSS.ColorComment)  # 亮绿色注释
                                lexer.setColor(QColor(255, 0, 0), QsciLexerCSS.ColorKeyword)  # 亮红色关键字
                                lexer.setColor(QColor(255, 0, 255), QsciLexerCSS.ColorString)  # 亮紫色字符串
                                lexer.setColor(QColor(0, 255, 255), QsciLexerCSS.ColorNumber)  # 亮青色数字
                                lexer.setColor(QColor(255, 255, 0), QsciLexerCSS.ColorSelector)  # 亮黄色选择器
                            elif isinstance(lexer, QsciLexerJavaScript):
                                # JavaScript lexer特定颜色设置 - 更亮的颜色
                                lexer.setColor(QColor(255, 0, 0), QsciLexerJavaScript.ColorKeyword)  # 亮红色关键字
                                lexer.setColor(QColor(0, 200, 0), QsciLexerJavaScript.ColorComment)  # 亮绿色注释
                                lexer.setColor(QColor(255, 0, 255), QsciLexerJavaScript.ColorString)  # 亮紫色字符串
                                lexer.setColor(QColor(0, 255, 255), QsciLexerJavaScript.ColorNumber)  # 亮青色数字
                            
                            # 设置括号颜色
                            try:
                                # 为所有lexer设置括号颜色
                                lexer.setColor(QColor(255, 255, 0), QsciLexerHTML.ColorOperator)  # 亮黄色括号
                                lexer.setColor(QColor(255, 255, 0), QsciLexerCSS.ColorOperator)  # 亮黄色括号
                                lexer.setColor(QColor(255, 255, 0), QsciLexerJavaScript.ColorOperator)  # 亮黄色括号
                            except AttributeError:
                                # 忽略不支持的颜色类型
                                pass
                        except (ImportError, AttributeError):
                            # 忽略不支持的lexer或颜色类型
                            pass
                        
                        # 重新应用lexer
                        editor.setLexer(lexer)
        
        # 更新所有终端的主题
        if hasattr(self, 'terminal_tab') and self.terminal_tab is not None:
            for i in range(self.terminal_tab.count()):
                terminal = self.terminal_tab.widget(i)
                if hasattr(terminal, "output"):
                    # 终端背景色和前景色
                    terminal.output.setStyleSheet(f"background-color: {terminal_bg.name()}; color: {terminal_fg.name()}; font-family: Consolas, monospace;")
        
        # 更新资源管理器的主题
        if hasattr(self, 'resource_explorer') and self.resource_explorer is not None:
            palette = self.resource_explorer.tree.palette()
            palette.setColor(QPalette.ColorRole.Window, editor_bg)
            palette.setColor(QPalette.ColorRole.WindowText, editor_fg)
            palette.setColor(QPalette.ColorRole.Base, editor_bg)
            palette.setColor(QPalette.ColorRole.Text, editor_fg)
            self.resource_explorer.tree.setPalette(palette)
        
        # 更新问题选项卡的主题
        if hasattr(self, 'problems_list') and self.problems_list is not None:
            palette = self.problems_list.palette()
            palette.setColor(QPalette.ColorRole.Window, list_bg)
            palette.setColor(QPalette.ColorRole.WindowText, list_fg)
            palette.setColor(QPalette.ColorRole.Base, list_bg)
            palette.setColor(QPalette.ColorRole.Text, list_fg)
            self.problems_list.setPalette(palette)
        
        # 更新状态栏信息
        self.statusBar().showMessage(f"已切换到{theme}主题")
    
    def show_syntax_errors(self, problems):
        """显示语法错误和警告，提供详细的错误信息和修复建议"""
        # 清空问题列表
        self.problems_list.clear()
        
        if not problems:
            # 没有问题，恢复原始标题
            self.problems_dock.setWindowTitle("问题")
            self.statusBar().showMessage("语法检查通过，未发现问题")
            return
        
        # 统计错误和警告数量
        error_count = 0
        warning_count = 0
        
        # 在问题选项卡中显示问题信息
        for line, col, msg, severity in problems:
            # 生成更详细的错误信息，包括可能的修复建议
            detailed_msg = msg
            
            # 添加错误代码和修复建议
            if "未闭合" in msg:
                detailed_msg += " (修复建议: 检查并添加缺失的闭合符号)"
            elif "括号不匹配" in msg:
                detailed_msg += " (修复建议: 检查括号配对)"
            elif "缺少分号" in msg:
                detailed_msg += " (修复建议: 在行尾添加分号)"
            elif "可能应该使用==" in msg:
                detailed_msg += " (修复建议: 将 = 替换为 ==)"
            elif "未初始化" in msg:
                detailed_msg += " (修复建议: 初始化变量或分配默认值)"
            elif "无效的" in msg:
                detailed_msg += " (修复建议: 检查语法或拼写)"
            elif "缩进问题" in msg:
                detailed_msg += " (修复建议: 检查缩进是否一致)"
            elif "未闭合的字符串" in msg:
                detailed_msg += " (修复建议: 检查字符串引号是否匹配)"
            elif "print " in msg:
                detailed_msg += " (修复建议: 使用 print() 函数)"
            
            # 添加错误代码
            error_code = f"ERR_{severity.upper()}_{line}_{col}"
            
            # 创建列表项
            if severity == "error":
                error_item = QListWidgetItem(f"错误 [{error_code}]: 行 {line}, 列 {col}: {detailed_msg}")
                error_item.setForeground(Qt.GlobalColor.red)
                error_count += 1
            else:  # warning
                warning_item = QListWidgetItem(f"警告 [{error_code}]: 行 {line}, 列 {col}: {detailed_msg}")
                warning_item.setForeground(Qt.GlobalColor.darkYellow)
                warning_count += 1
            
            self.problems_list.addItem(error_item if severity == "error" else warning_item)
        
        # 在状态栏显示简要信息
        total_count = error_count + warning_count
        if error_count > 0:
            self.statusBar().showMessage(f"发现 {error_count} 个错误和 {warning_count} 个警告")
        else:
            self.statusBar().showMessage(f"发现 {warning_count} 个警告")
        
        # 有问题，在标题中添加红点
        self.problems_dock.setWindowTitle("问题 ●")
    
    def check_qml_syntax(self, content):
        """检查QML语法，提供更精准的错误信息"""
        problems = []
        lines = content.split('\n')
        
        # 1. 检查括号和引号匹配
        brace_stack = []
        quote_stack = []
        
        for line_num, line in enumerate(lines, 1):
            for char_pos, char in enumerate(line):
                # 检查引号
                if char in ['"', "'"]:
                    if not quote_stack or quote_stack[-1] != char:
                        quote_stack.append(char)
                    else:
                        quote_stack.pop()
                
                # 检查括号
                if char in '([{':
                    brace_stack.append((char, line_num, char_pos + 1))
                elif char in ')]}':
                    if not brace_stack:
                        problems.append((line_num, char_pos + 1, "多余的右括号", "error"))
                    else:
                        open_brace, open_line, open_pos = brace_stack.pop()
                        if (open_brace == '(' and char != ')') or \
                           (open_brace == '[' and char != ']') or \
                           (open_brace == '{' and char != '}'):
                            problems.append((line_num, char_pos + 1, f"括号不匹配: {open_brace} 和 {char}", "error"))
        
        # 检查未闭合的括号
        for open_brace, open_line, open_pos in brace_stack:
            problems.append((open_line, open_pos, f"未闭合的括号: {open_brace}", "error"))
        
        # 检查未闭合的引号
        if quote_stack:
            problems.append((1, 1, f"未闭合的引号: {quote_stack[-1]}", "error"))
        
        # 2. 检查QML特定的语法问题
        
        # 检查是否有根元素
        has_root = False
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('//') and not stripped_line.startswith('/*') and not stripped_line.startswith('*'):
                # 简单检查是否有根元素
                if stripped_line.endswith('{') and not stripped_line.startswith('import'):
                    has_root = True
                    break
        
        if not has_root and content.strip():
            problems.append((1, 1, "QML文件缺少根元素", "error"))
        
        # 检查导入语句
        has_import = False
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('import'):
                has_import = True
                # 检查导入语句格式
                if ' ' not in stripped_line:
                    problems.append((line_num, 1, "导入语句格式不正确", "warning"))
                else:
                    # 检查是否有版本号
                    import_parts = stripped_line.split()
                    if len(import_parts) < 2:
                        problems.append((line_num, 1, "导入语句缺少模块名", "error"))
                    elif len(import_parts) == 2 and import_parts[1] in ['QtQuick', 'QtWidgets', 'QtCore', 'QtGui', 'QtQml']:
                        problems.append((line_num, len(stripped_line), "建议为Qt模块添加版本号", "warning"))
        
        if not has_import and content.strip():
            problems.append((1, 1, "建议添加导入语句", "warning"))
        
        # 检查常见的QML语法问题
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('//') or stripped_line.startswith('/*') or stripped_line.startswith('*'):
                continue
            
            # 检查属性赋值
            if ':' in stripped_line and not stripped_line.startswith('import'):
                # 检查是否缺少分号
                if not stripped_line.endswith(';'):
                    problems.append((line_num, len(stripped_line), "建议添加分号", "warning"))
                
                # 检查属性名是否有效
                prop_name = stripped_line.split(':')[0].strip()
                if not prop_name.isidentifier():
                    problems.append((line_num, 1, f"无效的属性名: {prop_name}", "warning"))
            
            # 检查函数调用
            if '(' in stripped_line and ')' in stripped_line:
                # 检查是否缺少分号
                if not stripped_line.endswith(';') and not stripped_line.endswith('{'):
                    problems.append((line_num, len(stripped_line), "建议添加分号", "warning"))
            
            # 检查比较运算符
            if '=' in line and not '==' in line and not '!=' in line and not '<=' in line and not '>=' in line and not '+=' in line and not '-=' in line and not '*=' in line and not '/=' in line:
                # 检查是否是条件语句
                if 'if ' in line or 'else if ' in line or 'while ' in line:
                    problems.append((line_num, line.find('=') + 1, "条件语句中可能应该使用==而不是=", "warning"))
        
        return problems

# 程序入口点
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyIDE()
    window.show()
    sys.exit(app.exec())
