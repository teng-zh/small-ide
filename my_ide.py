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
        
        # 语法检查菜单
        self.check_menu = menubar.addMenu("检查")
        
        self.check_syntax_action = QAction("检查语法", self)
        self.check_syntax_action.setShortcut("F7")
        self.check_syntax_action.triggered.connect(self.check_syntax)
        self.check_menu.addAction(self.check_syntax_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
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
        
        # 添加文本改变事件监听，用于实时语法检查
        editor.textChanged.connect(lambda: self.check_syntax(editor=editor))
        
        return editor
    
    def load_settings(self):
        """加载设置文件"""
        default_settings = {
            "changes_log_opened": False
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
            try:
                from PyQt6.Qsci import QsciLexerCSS
                lexer = QsciLexerCSS()
                lexer.setFont(font)
                editor.setLexer(lexer)
            except ImportError:
                editor.setLexer(None)
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
        
        # 更新运行菜单可见性
        # 运行菜单已被删除，不再需要更新可见性
    
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
            
            # 检查分号
            if stripped_line and not stripped_line.endswith(';') and not stripped_line.endswith('{') and not stripped_line.endswith('}'):
                # 检查是否是控制流语句
                if not any(keyword in stripped_line for keyword in ['if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break', 'continue', 'return', 'throw', 'try', 'catch', 'finally', 'function', 'class', 'interface', 'enum', 'record', 'extends', 'implements', 'export', 'import', 'from', 'as', 'async', 'await', 'new', 'super', 'this', 'typeof', 'instanceof', 'delete', 'void', 'in', 'of', 'with', 'debugger', 'yield', 'return', 'throw', 'try', 'catch', 'finally', 'switch', 'case', 'default', 'break', 'continue', 'if', 'else', 'for', 'while', 'do', 'label:', 'goto', 'const', 'let', 'var', 'function', 'class', 'interface', 'enum', 'record', 'extends', 'implements', 'export', 'import', 'from', 'as', 'async', 'await', 'new', 'super', 'this', 'typeof', 'instanceof', 'delete', 'void', 'in', 'of', 'with', 'debugger', 'yield']):
                    problems.append((line_num, len(line), "建议添加分号", "warning"))
        
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
                
                # 检查属性值是否有分号
                if ';' not in line and not line.strip().endswith('{') and not line.strip().endswith('}'):
                    problems.append((line_num, len(line), "CSS属性值建议添加分号", "warning"))
            
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
    
    def show_syntax_errors(self, problems):
        """显示语法错误和警告"""
        # 清空问题列表
        self.problems_list.clear()
        
        if not problems:
            # 没有问题，恢复原始标题
            self.problems_dock.setWindowTitle("问题")
            self.statusBar().showMessage("语法检查通过，未发现问题")
            # 保持问题选项卡隐藏
            return
        
        # 统计错误和警告数量
        error_count = 0
        warning_count = 0
        
        # 在问题选项卡中显示问题信息
        for line, col, msg, severity in problems:
            if severity == "error":
                error_item = QListWidgetItem(f"错误: 行 {line}, 列 {col}: {msg}")
                error_item.setForeground(Qt.GlobalColor.red)
                error_count += 1
            else:  # warning
                warning_item = QListWidgetItem(f"警告: 行 {line}, 列 {col}: {msg}")
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
        # 保持问题选项卡隐藏，只显示红点提示
        # self.problems_dock.show()  # 注释掉这行

# 程序入口点
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyIDE()
    window.show()
    sys.exit(app.exec())