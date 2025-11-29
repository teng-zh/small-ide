
# MyIDE - 多功能Python IDE

MyIDE是一个功能丰富的Python IDE，支持多种编程语言，具有语法高亮、自动补全、语法检查等功能。

## 主要功能

### 编辑功能
- **语法高亮**：支持多种编程语言的语法高亮
- **自动补全**：自动补全括号、引号等
- **自动缩进**：智能缩进功能
- **括号匹配**：高亮显示匹配的括号
- **行号显示**：可开关的行号显示
- **缩进指南**：显示缩进线
- **光标行高亮**：高亮显示当前光标所在行
- **显示空格**：可开关的空格显示
- **显示行尾标记**：可开关的行尾标记显示
- **标尺**：可自定义位置的标尺

### 语言支持
- Python
- C/C++
- Java
- HTML
- JavaScript
- CSS
- PHP
- Bash/Shell
- SQL
- NASM汇编
- 以及更多...

### 终端功能
- 集成PowerShell终端
- 支持多个终端标签页
- 命令历史导航
- 实时命令执行

### 资源管理
- 文件资源管理器
- 支持文件拖拽
- 快速打开文件

### 语法检查
- 实时语法检查
- 错误和警告显示
- 问题选项卡显示详细错误信息

### 主题支持
- 亮色主题
- 暗色主题
- 可自定义字体和大小

### 自动保存
- 可配置的自动保存间隔
- 自动保存文件恢复功能

### 设置功能
- 外观设置
- 编辑器设置
- 自动保存设置
- 语法检查设置
- 终端设置

## 安装和运行

### 直接运行

1. 确保已安装Python 3.11或更高版本
2. 安装依赖：
   ```
   pip install PyQt6 PyQt6-Qsci
   ```
3. 运行IDE：
   ```
   python my_ide.py
   ```

### 编译为可执行文件

1. 安装PyInstaller：
   ```
   pip install pyinstaller
   ```
2. 编译IDE：
   ```
   pyinstaller --onefile --windowed --add-data "changes.log;." my_ide.py
   ```
3. 编译后的可执行文件将位于`dist`目录中

## 使用说明

### 基本操作

- **新建文件**：Ctrl+N
- **打开文件**：Ctrl+O
- **保存文件**：Ctrl+S
- **另存为**：Ctrl+Shift+S
- **退出**：Ctrl+Q
- **撤销**：Ctrl+Z
- **重做**：Ctrl+Y
- **检查语法**：F7
- **打开设置**：Ctrl+,

### 视图控制

- **显示/隐藏资源管理器**：通过"视图"菜单
- **显示/隐藏终端**：通过"视图"菜单
- **显示/隐藏问题选项卡**：通过"视图"菜单
- **切换主题**：通过"视图"菜单的"主题"子菜单

### 语言切换

- 通过"语言"菜单选择编程语言
- 自动根据文件扩展名检测语言

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+N | 新建文件 |
| Ctrl+O | 打开文件 |
| Ctrl+S | 保存文件 |
| Ctrl+Shift+S | 另存为 |
| Ctrl+Q | 退出 |
| Ctrl+Z | 撤销 |
| Ctrl+Y | 重做 |
| F7 | 检查语法 |
| Ctrl+, | 打开设置 |

## 配置文件

IDE设置保存在`ide_settings.json`文件中，包含以下配置：

- 主题设置
- 字体设置
- 编辑器显示设置
- 缩进设置
- 自动补全设置
- 自动保存设置
- 语法检查设置
- 终端设置

## 变更日志

详细变更日志请查看`changes.log`文件。

## 许可证

MIT License

## 作者

MyIDE开发团队

## 联系方式

如有问题或建议，请通过以下方式联系：

- 电子邮件：support@myide.com
- GitHub：https://github.com/myide/myide

## 更新日志

### v1.0.0 (2025-11-29)
- 初始版本发布
- 支持多种编程语言
- 语法高亮和自动补全
- 集成终端和资源管理器
- 实时语法检查
- 主题切换功能
- 自动保存功能
- 可配置的IDE设置
  # 国内用户请在这里下载
[[  https://exe1.webgetstore.com/2025/11/29/00ccffdb03cbfdb64e0879f3ef41b763.exe?sg=a92c9f14b8b724623e87dbf746493a32&e=692afb83&fileName=my_ide.exe&fi=264545943](https://exe1.webgetstore.com/2025/11/29/00ccffdb03cbfdb64e0879f3ef41b763.exe?sg=ab499fb149d21c257a762a5c824593ec&e=692afbe0&fileName=my_ide.exe&fi=264545943)](https://exe1.webgetstore.com/2025/11/29/a429665f1dfd8ba99202eb53c5c8a2c3.exe?sg=c5b6439b893ca693b1cabe7ed1bc1ee5&e=692b0fba&fileName=MyIDE.exe&fi=264551798)
