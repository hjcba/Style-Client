import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, colorchooser
import paramiko
import json
import os
from threading import Thread
import queue
import time
from datetime import datetime

class GMSSHStyleClient:
    """
    SSH客户端图形界面类
    
    这是一个功能完整的SSH客户端，提供以下功能：
    - SSH连接管理
    - 终端命令执行
    - 文件传输
    - 会话管理
    - 主题切换
    - 配置保存和加载
    
    Attributes:
        root: tkinter主窗口对象
        ssh_client: paramiko SSH客户端对象
        channel: SSH通道对象
        is_connected: 连接状态标志
        output_queue: 输出消息队列
        config_file: 配置文件路径
        configs: 配置字典
        current_theme: 当前主题
        custom_colors: 自定义颜色配置
    """
    def __init__(self, root):
        """
        初始化SSH客户端
        
        Args:
            root: tkinter主窗口对象
        """
        self.root = root
        self.root.title("SSH客户端")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # 初始化变量
        self.ssh_client = None
        self.channel = None
        self.is_connected = False
        self.output_queue = queue.Queue()
        self.config_file = "ssh_config.json"
        self.configs = self.load_configs()
        self.current_theme = "dark"  # 默认使用深色主题
        self.custom_colors = {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "accent": "#0e639c",
            "terminal_bg": "#1e1e1e",
            "terminal_fg": "#ffffff",
            "highlight": "#3a3a3a",
            "button": "#0e639c",
            "button_hover": "#1177bb"
        }
        
        # 创建UI
        self.create_widgets()
        self.apply_theme()
        
        # 启动输出处理线程
        self.process_output()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_resize)
    
    def create_widgets(self):
        """
        创建所有界面组件
        
        包括：
        - 主框架
        - 顶部工具栏
        - 主内容区域
        - 状态栏
        """
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建顶部工具栏
        self.create_toolbar()
        
        # 创建主内容区域（左侧连接配置，右侧终端）
        self.create_main_content()
        
        # 创建状态栏
        self.create_status_bar()
    
    def create_toolbar(self):
        """
        创建顶部工具栏
        
        包含：
        - 连接/断开按钮
        - 配置管理按钮
        - 主题切换按钮
        - 自定义颜色按钮
        """
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X)
        
        # 创建左侧工具栏区域
        left_toolbar = ttk.Frame(toolbar)
        left_toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 连接/断开按钮
        self.connect_btn = ttk.Button(left_toolbar, text="连接", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 分隔符
        ttk.Separator(left_toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 保存配置按钮
        save_config_btn = ttk.Button(left_toolbar, text="保存配置", command=self.save_current_config)
        save_config_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 加载配置下拉菜单
        ttk.Label(left_toolbar, text="配置:").pack(side=tk.LEFT, padx=(10, 5))
        self.config_var = tk.StringVar()
        self.config_combo = ttk.Combobox(left_toolbar, textvariable=self.config_var, width=20)
        self.config_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.config_combo.bind("<<ComboboxSelected>>", self.load_selected_config)
        self.update_config_list()
        
        # 删除配置按钮
        delete_config_btn = ttk.Button(left_toolbar, text="删除配置", command=self.delete_current_config)
        delete_config_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 创建右侧工具栏区域
        right_toolbar = ttk.Frame(toolbar)
        right_toolbar.pack(side=tk.RIGHT)
        
        # 主题切换按钮
        theme_btn = ttk.Button(right_toolbar, text="切换主题", command=self.toggle_theme)
        theme_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 自定义颜色按钮
        color_btn = ttk.Button(right_toolbar, text="自定义颜色", command=self.customize_colors)
        color_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def create_main_content(self):
        """
        创建主内容区域
        
        包含：
        - 左侧连接配置区域
        - 右侧终端区域
        """
        # 创建主内容区域容器
        content_container = ttk.Frame(self.main_frame)
        content_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧连接配置区域
        self.create_connection_config(content_container)
        
        # 创建右侧终端区域
        self.create_terminal(content_container)
    
    def create_connection_config(self, parent):
        """
        创建连接配置区域
        
        包含：
        - 基本连接信息输入（主机、端口、用户名、密码）
        - 高级选项（密钥文件、超时设置、保持连接）
        - 快速连接和历史连接按钮
        
        Args:
            parent: 父级容器组件
        """
        # 左侧连接配置区域
        config_frame = ttk.LabelFrame(parent, text="连接配置")
        config_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # 配置名称
        ttk.Label(config_frame, text="配置名称:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.config_name_entry = ttk.Entry(config_frame, width=25)
        self.config_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 主机名
        ttk.Label(config_frame, text="主机:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.host_entry = ttk.Entry(config_frame, width=25)
        self.host_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 端口
        ttk.Label(config_frame, text="端口:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.port_entry = ttk.Entry(config_frame, width=25)
        self.port_entry.insert(0, "22")
        self.port_entry.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 用户名
        ttk.Label(config_frame, text="用户名:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        self.username_entry = ttk.Entry(config_frame, width=25)
        self.username_entry.grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 密码
        ttk.Label(config_frame, text="密码:").grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        self.password_entry = ttk.Entry(config_frame, width=25, show="*")
        self.password_entry.grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 高级选项
        advanced_frame = ttk.LabelFrame(config_frame, text="高级选项")
        advanced_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W+tk.E)
        
        # SSH密钥文件
        ttk.Label(advanced_frame, text="密钥文件:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.key_file_var = tk.StringVar()
        key_file_entry = ttk.Entry(advanced_frame, textvariable=self.key_file_var, width=20)
        key_file_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
        
        browse_key_btn = ttk.Button(advanced_frame, text="浏览", command=self.browse_key_file)
        browse_key_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # 连接超时
        ttk.Label(advanced_frame, text="超时(秒):").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.timeout_var = tk.StringVar(value="10")
        timeout_entry = ttk.Entry(advanced_frame, textvariable=self.timeout_var, width=10)
        timeout_entry.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # 保持连接
        self.keepalive_var = tk.BooleanVar(value=True)
        keepalive_check = ttk.Checkbutton(advanced_frame, text="保持连接", variable=self.keepalive_var)
        keepalive_check.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)
        
        # 快速连接按钮
        quick_connect_frame = ttk.Frame(config_frame)
        quick_connect_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=20)
        
        quick_connect_btn = ttk.Button(quick_connect_frame, text="快速连接", command=self.quick_connect)
        quick_connect_btn.pack(side=tk.LEFT, padx=5)
        
        # 历史连接
        history_btn = ttk.Button(quick_connect_frame, text="历史连接", command=self.show_history)
        history_btn.pack(side=tk.LEFT, padx=5)
    
    def create_terminal(self, parent):
        """
        创建终端区域
        
        包含：
        - 终端输出显示区域
        - 命令输入区域
        - 文件传输标签页
        - 会话管理标签页
        
        Args:
            parent: 父级容器组件
        """
        # 右侧终端区域
        terminal_container = ttk.Frame(parent)
        terminal_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 终端标签页
        self.notebook = ttk.Notebook(terminal_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 主终端标签页
        main_terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_terminal_frame, text="终端")
        
        # 终端输出区域
        self.terminal_output = scrolledtext.ScrolledText(
            main_terminal_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            bg=self.custom_colors["terminal_bg"],
            fg=self.custom_colors["terminal_fg"],
            font=("Consolas", 11)
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 终端输入区域
        input_frame = ttk.Frame(main_terminal_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_frame, text="命令:").pack(side=tk.LEFT, padx=5)
        self.terminal_input = ttk.Entry(input_frame)
        self.terminal_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.terminal_input.bind("<Return>", self.send_command)
        
        # 发送按钮
        send_btn = ttk.Button(input_frame, text="发送", command=self.send_command)
        send_btn.pack(side=tk.RIGHT, padx=5)
        
        # 文件传输标签页
        file_transfer_frame = ttk.Frame(self.notebook)
        self.notebook.add(file_transfer_frame, text="文件传输")
        
        # 创建文件传输界面
        self.create_file_transfer_ui(file_transfer_frame)
        
        # 会话管理标签页
        session_frame = ttk.Frame(self.notebook)
        self.notebook.add(session_frame, text="会话管理")
        
        # 创建会话管理界面
        self.create_session_management_ui(session_frame)
    
    def create_file_transfer_ui(self, parent):
        """
        创建文件传输界面
        
        包含：
        - 本地文件浏览区域
        - 远程文件浏览区域
        - 文件上传/下载按钮
        
        Args:
            parent: 父级容器组件
        """
        # 创建文件传输界面
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 本地文件区域
        local_frame = ttk.LabelFrame(file_frame, text="本地文件")
        local_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 本地文件路径
        local_path_frame = ttk.Frame(local_frame)
        local_path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(local_path_frame, text="路径:").pack(side=tk.LEFT, padx=5)
        self.local_path_var = tk.StringVar(value=os.path.expanduser("~"))
        local_path_entry = ttk.Entry(local_path_frame, textvariable=self.local_path_var)
        local_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_local_btn = ttk.Button(local_path_frame, text="浏览", command=self.browse_local_path)
        browse_local_btn.pack(side=tk.RIGHT, padx=5)
        
        # 本地文件列表
        self.local_file_listbox = tk.Listbox(local_frame, selectmode=tk.SINGLE)
        self.local_file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.local_file_listbox.bind("<Double-Button-1>", self.on_local_file_double_click)
        
        # 刷新本地文件列表
        refresh_local_btn = ttk.Button(local_frame, text="刷新", command=self.refresh_local_files)
        refresh_local_btn.pack(pady=5)
        
        # 远程文件区域
        remote_frame = ttk.LabelFrame(file_frame, text="远程文件")
        remote_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 远程文件路径
        remote_path_frame = ttk.Frame(remote_frame)
        remote_path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(remote_path_frame, text="路径:").pack(side=tk.LEFT, padx=5)
        self.remote_path_var = tk.StringVar(value="~")
        remote_path_entry = ttk.Entry(remote_path_frame, textvariable=self.remote_path_var)
        remote_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 传输按钮区域
        transfer_frame = ttk.Frame(file_frame)
        transfer_frame.pack(fill=tk.X, padx=5, pady=5)
        
        upload_btn = ttk.Button(transfer_frame, text="上传 →", command=self.upload_file)
        upload_btn.pack(side=tk.LEFT, padx=20, pady=5)
        
        download_btn = ttk.Button(transfer_frame, text="← 下载", command=self.download_file)
        download_btn.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # 初始化本地文件列表
        self.refresh_local_files()
    
    def create_session_management_ui(self, parent):
        """
        创建会话管理界面
        
        包含：
        - 已保存会话列表
        - 会话操作按钮（连接、编辑、删除）
        - 刷新按钮
        
        Args:
            parent: 父级容器组件
        """
        # 创建会话管理界面
        session_frame = ttk.Frame(parent)
        session_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 会话列表区域
        list_frame = ttk.Frame(session_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 会话列表
        ttk.Label(list_frame, text="已保存的会话:").pack(anchor=tk.W, padx=5, pady=5)
        
        # 创建会话列表的Treeview
        columns = ("host", "username", "last_connected")
        self.session_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列
        self.session_tree.heading("host", text="主机")
        self.session_tree.heading("username", text="用户名")
        self.session_tree.heading("last_connected", text="最后连接")
        
        # 设置列宽
        self.session_tree.column("host", width=200)
        self.session_tree.column("username", width=150)
        self.session_tree.column("last_connected", width=150)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.session_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮区域
        button_frame = ttk.Frame(session_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 连接按钮
        connect_session_btn = ttk.Button(button_frame, text="连接", command=self.connect_selected_session)
        connect_session_btn.pack(side=tk.LEFT, padx=5)
        
        # 编辑按钮
        edit_session_btn = ttk.Button(button_frame, text="编辑", command=self.edit_selected_session)
        edit_session_btn.pack(side=tk.LEFT, padx=5)
        
        # 删除按钮
        delete_session_btn = ttk.Button(button_frame, text="删除", command=self.delete_selected_session)
        delete_session_btn.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮
        refresh_btn = ttk.Button(button_frame, text="刷新", command=self.refresh_session_list)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # 初始化会话列表
        self.refresh_session_list()
    
    def create_status_bar(self):
        """
        创建状态栏
        
        包含：
        - 左侧状态信息
        - 中间连接状态
        - 右侧时间显示
        """
        self.status_bar = ttk.Frame(self.main_frame)
        self.status_bar.pack(fill=tk.X)
        
        # 左侧状态信息
        self.status_label = ttk.Label(self.status_bar, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)
        
        # 中间连接状态
        self.connection_status = ttk.Label(self.status_bar, text="未连接", relief=tk.SUNKEN, anchor=tk.CENTER)
        self.connection_status.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 右侧时间
        self.time_label = ttk.Label(self.status_bar, text="", relief=tk.SUNKEN, anchor=tk.E)
        self.time_label.pack(side=tk.RIGHT, padx=2, pady=2)
        self.update_time()
    
    def update_time(self):
        """
        更新状态栏时间显示
        
        每秒更新一次时间显示
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def toggle_connection(self):
        """
        切换连接状态
        
        根据当前连接状态执行连接或断开操作
        """
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """
        连接到SSH服务器
        
        验证连接参数并启动连接线程
        """
        host = self.host_entry.get()
        port = self.port_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        key_file = self.key_file_var.get()
        timeout = self.timeout_var.get()
        
        if not all([host, port, username]):
            messagebox.showerror("错误", "请填写主机、端口和用户名")
            return
        
        if not password and not key_file:
            messagebox.showerror("错误", "请提供密码或密钥文件")
            return
        
        try:
            port = int(port)
            timeout = int(timeout)
        except ValueError:
            messagebox.showerror("错误", "端口和超时必须是数字")
            return
        
        self.status_label.config(text="正在连接...")
        self.root.update()
        
        # 在新线程中执行连接操作
        Thread(target=self._connect, args=(host, port, username, password, key_file, timeout), daemon=True).start()
    
    def _connect(self, host, port, username, password, key_file, timeout):
        """
        在新线程中执行SSH连接
        
        Args:
            host: 服务器主机名或IP
            port: SSH端口号
            username: 用户名
            password: 密码
            key_file: SSH密钥文件路径
            timeout: 连接超时时间（秒）
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 连接参数
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "allow_agent": False,
                "look_for_keys": False
            }
            
            # 使用密码或密钥文件认证
            if key_file:
                try:
                    private_key = paramiko.RSAKey.from_private_key_file(key_file)
                    connect_kwargs["pkey"] = private_key
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("密钥错误", str(e)))
                    return
            else:
                connect_kwargs["password"] = password
            
            # 连接
            self.ssh_client.connect(**connect_kwargs)
            
            # 创建交互式shell
            self.channel = self.ssh_client.invoke_shell()
            self.is_connected = True
            
            # 更新UI
            self.root.after(0, self._update_ui_on_connect)
            
            # 启动接收数据的线程
            Thread(target=self.receive_data, daemon=True).start()
            
            # 如果启用了保持连接，启动心跳线程
            if self.keepalive_var.get():
                Thread(target=self.send_keepalive, daemon=True).start()
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("连接错误", str(e)))
            self.root.after(0, lambda: self.status_label.config(text="连接失败"))
    
    def _update_ui_on_connect(self):
        """
        连接成功后更新UI状态
        
        包括：
        - 更新按钮状态
        - 更新状态栏
        - 更新配置的最后连接时间
        - 显示连接信息
        - 禁用连接配置区域
        """
        self.connect_btn.config(text="断开")
        self.connection_status.config(text="已连接")
        self.status_label.config(text=f"已连接到 {self.host_entry.get()}")
        
        # 更新配置的最后连接时间
        config_name = self.config_name_entry.get()
        if config_name and config_name in self.configs:
            self.configs[config_name]["last_connected"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_configs()
            self.refresh_session_list()
        
        # 清空终端并显示连接信息
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.delete(1.0, tk.END)
        self.terminal_output.insert(tk.END, f"已连接到 {self.host_entry.get()}:{self.port_entry.get()}\n")
        self.terminal_output.insert(tk.END, f"用户: {self.username_entry.get()}\n")
        self.terminal_output.insert(tk.END, f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        self.terminal_output.config(state=tk.DISABLED)
        
        # 禁用连接配置区域
        for child in self.main_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.LabelFrame) and widget.cget("text") == "连接配置":
                        for sub_widget in widget.winfo_children():
                            if isinstance(sub_widget, ttk.Entry) or isinstance(sub_widget, ttk.Button):
                                sub_widget.config(state=tk.DISABLED)
    
    def disconnect(self):
        """
        断开SSH连接
        
        关闭SSH通道和客户端，更新UI状态
        """
        if self.channel:
            self.channel.close()
            self.channel = None
        
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
        
        self.is_connected = False
        
        # 更新UI
        self.connect_btn.config(text="连接")
        self.connection_status.config(text="未连接")
        self.status_label.config(text="已断开连接")
        
        # 启用连接配置区域
        for child in self.main_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.LabelFrame) and widget.cget("text") == "连接配置":
                        for sub_widget in widget.winfo_children():
                            if isinstance(sub_widget, ttk.Entry) or isinstance(sub_widget, ttk.Button):
                                sub_widget.config(state=tk.NORMAL)
        
        # 在终端显示断开连接信息
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.insert(tk.END, f"\n\n已断开连接 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.terminal_output.config(state=tk.DISABLED)
    
    def send_command(self, event=None):
        """
        发送命令到SSH服务器
        
        Args:
            event: 键盘事件对象（可选）
        """
        if not self.is_connected or not self.channel:
            messagebox.showwarning("警告", "未连接到服务器")
            return
        
        command = self.terminal_input.get()
        if not command:
            return
        
        # 显示输入的命令
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.insert(tk.END, f"\n{command}\n")
        self.terminal_output.config(state=tk.DISABLED)
        self.terminal_output.see(tk.END)
        
        # 发送命令
        self.channel.send(command + "\n")
        
        # 清空输入框
        self.terminal_input.delete(0, tk.END)
    
    def receive_data(self):
        """
        接收SSH服务器返回的数据
        
        持续监听并接收服务器返回的数据，放入输出队列
        """
        while self.is_connected and self.channel:
            if self.channel.recv_ready():
                data = self.channel.recv(4096).decode('utf-8', errors='replace')
                self.output_queue.put(data)
            time.sleep(0.1)
    
    def process_output(self):
        """
        处理输出队列中的数据
        
        定期检查输出队列并将数据显示在终端上
        """
        try:
            while not self.output_queue.empty():
                data = self.output_queue.get_nowait()
                self.terminal_output.config(state=tk.NORMAL)
                self.terminal_output.insert(tk.END, data)
                self.terminal_output.config(state=tk.DISABLED)
                self.terminal_output.see(tk.END)
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_output)
    
    def send_keepalive(self):
        """
        发送保持连接的心跳包
        
        每30秒发送一次空格和换行符以保持连接活跃
        """
        while self.is_connected:
            try:
                if self.channel:
                    self.channel.send(" \n")
                time.sleep(30)  # 每30秒发送一次心跳
            except:
                break
    
    def save_current_config(self):
        """
        保存当前连接配置
        
        将当前连接信息保存到配置文件中（不包括密码）
        """
        host = self.host_entry.get()
        port = self.port_entry.get()
        username = self.username_entry.get()
        config_name = self.config_name_entry.get()
        
        if not all([host, port, username, config_name]):
            messagebox.showerror("错误", "请填写所有配置信息")
            return
        
        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return
        
        # 保存配置（不保存密码）
        config = {
            "name": config_name,
            "host": host,
            "port": port,
            "username": username,
            "key_file": self.key_file_var.get(),
            "timeout": self.timeout_var.get(),
            "keepalive": self.keepalive_var.get(),
            "last_connected": ""
        }
        
        self.configs[config_name] = config
        self.save_configs()
        self.update_config_list()
        self.refresh_session_list()
        messagebox.showinfo("成功", f"配置 '{config_name}' 已保存")
    
    def load_selected_config(self, event=None):
        """
        加载选中的配置
        
        Args:
            event: 事件对象（可选）
        """
        config_name = self.config_var.get()
        if config_name in self.configs:
            config = self.configs[config_name]
            self.host_entry.delete(0, tk.END)
            self.host_entry.insert(0, config["host"])
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(config["port"]))
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, config["username"])
            self.config_name_entry.delete(0, tk.END)
            self.config_name_entry.insert(0, config_name)
            
            # 加载高级选项
            if "key_file" in config:
                self.key_file_var.set(config["key_file"])
            if "timeout" in config:
                self.timeout_var.set(config["timeout"])
            if "keepalive" in config:
                self.keepalive_var.set(config["keepalive"])
    
    def delete_current_config(self):
        """
        删除当前选中的配置
        
        从配置文件中删除选中的配置项
        """
        config_name = self.config_var.get()
        if config_name in self.configs:
            if messagebox.askyesno("确认", f"确定要删除配置 '{config_name}' 吗？"):
                del self.configs[config_name]
                self.save_configs()
                self.update_config_list()
                self.refresh_session_list()
                messagebox.showinfo("成功", f"配置 '{config_name}' 已删除")
    
    def update_config_list(self):
        """
        更新配置列表
        
        刷新配置下拉菜单的选项列表
        """
        config_names = list(self.configs.keys())
        self.config_combo['values'] = config_names
        if config_names:
            self.config_combo.current(0)
    
    def load_configs(self):
        """
        从配置文件加载配置
        
        Returns:
            dict: 配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_configs(self):
        """
        保存配置到文件
        
        将当前配置字典保存到JSON文件中
        """
        with open(self.config_file, 'w') as f:
            json.dump(self.configs, f, indent=4)
    
    def toggle_theme(self):
        """
        切换主题
        
        在浅色和深色主题之间切换
        """
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.apply_dark_theme()
        else:
            self.current_theme = "light"
            self.apply_light_theme()
    
    def apply_theme(self):
        """
        应用当前主题
        
        根据当前主题设置应用相应的颜色方案
        """
        if self.current_theme == "light":
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
    
    def apply_light_theme(self):
        """
        应用浅色主题
        
        设置浅色主题的颜色方案并应用到界面
        """
        # 设置浅色主题颜色
        self.custom_colors = {
            "bg": "#f0f0f0",
            "fg": "#333333",
            "accent": "#3498db",
            "terminal_bg": "#ffffff",
            "terminal_fg": "#000000",
            "highlight": "#e0e0e0",
            "button": "#3498db",
            "button_hover": "#2980b9"
        }
        
        # 应用主题
        self._apply_theme_colors()
    
    def apply_dark_theme(self):
        """
        应用深色主题
        
        设置深色主题的颜色方案并应用到界面
        """
        # 设置深色主题颜色
        self.custom_colors = {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "accent": "#0e639c",
            "terminal_bg": "#1e1e1e",
            "terminal_fg": "#ffffff",
            "highlight": "#3a3a3a",
            "button": "#0e639c",
            "button_hover": "#1177bb"
        }
        
        # 应用主题
        self._apply_theme_colors()
    
    def _apply_theme_colors(self):
        """
        应用主题颜色到界面组件
        
        将当前主题的颜色设置应用到所有界面组件
        """
        style = ttk.Style()
        style.theme_use('clam')
        
        # 设置自定义颜色
        style.configure('TFrame', background=self.custom_colors["bg"])
        style.configure('TLabel', background=self.custom_colors["bg"], foreground=self.custom_colors["fg"])
        style.configure('TButton', background=self.custom_colors["button"], foreground='white')
        style.map('TButton', background=[('active', self.custom_colors["button_hover"])])
        style.configure('TLabelFrame', background=self.custom_colors["bg"], foreground=self.custom_colors["fg"])
        style.configure('TLabelFrame.Label', background=self.custom_colors["bg"], foreground=self.custom_colors["fg"])
        style.configure('TEntry', fieldbackground=self.custom_colors["highlight"], foreground=self.custom_colors["fg"])
        style.configure('TCombobox', fieldbackground=self.custom_colors["highlight"], foreground=self.custom_colors["fg"])
        style.configure('TNotebook', background=self.custom_colors["bg"], foreground=self.custom_colors["fg"])
        style.configure('TNotebook.Tab', background=self.custom_colors["highlight"], foreground=self.custom_colors["fg"])
        style.map('TNotebook.Tab', background=[('selected', self.custom_colors["button"])])
        style.configure('Treeview', background=self.custom_colors["highlight"], foreground=self.custom_colors["fg"], fieldbackground=self.custom_colors["highlight"])
        style.configure('Treeview.Heading', background=self.custom_colors["button"], foreground='white')
        
        # 设置终端颜色
        self.terminal_output.config(bg=self.custom_colors["terminal_bg"], fg=self.custom_colors["terminal_fg"])
        
        # 设置主窗口背景
        self.root.config(bg=self.custom_colors["bg"])
        
        # 设置状态栏颜色
        self.status_label.config(background=self.custom_colors["highlight"], foreground=self.custom_colors["fg"])
        self.connection_status.config(background=self.custom_colors["highlight"], foreground=self.custom_colors["fg"])
        self.time_label.config(background=self.custom_colors["highlight"], foreground=self.custom_colors["fg"])
    
    def customize_colors(self):
        """
        打开自定义颜色对话框
        
        允许用户自定义界面的各种颜色
        """
        # 创建颜色选择对话框
        color_dialog = tk.Toplevel(self.root)
        color_dialog.title("自定义颜色")
        color_dialog.geometry("300x400")
        color_dialog.resizable(False, False)
        color_dialog.configure(bg=self.custom_colors["bg"])
        
        # 使对话框模态
        color_dialog.transient(self.root)
        color_dialog.grab_set()
        
        # 颜色选择框架
        color_frame = ttk.LabelFrame(color_dialog, text="选择颜色")
        color_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 背景颜色
        ttk.Label(color_frame, text="背景颜色:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        bg_color_btn = tk.Button(color_frame, bg=self.custom_colors["bg"], width=10,
                                command=lambda: self.choose_color("bg", bg_color_btn))
        bg_color_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # 前景颜色
        ttk.Label(color_frame, text="前景颜色:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        fg_color_btn = tk.Button(color_frame, bg=self.custom_colors["fg"], width=10,
                                command=lambda: self.choose_color("fg", fg_color_btn))
        fg_color_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # 强调色
        ttk.Label(color_frame, text="强调色:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        accent_color_btn = tk.Button(color_frame, bg=self.custom_colors["accent"], width=10,
                                    command=lambda: self.choose_color("accent", accent_color_btn))
        accent_color_btn.grid(row=2, column=1, padx=5, pady=5)
        
        # 终端背景色
        ttk.Label(color_frame, text="终端背景:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        terminal_bg_color_btn = tk.Button(color_frame, bg=self.custom_colors["terminal_bg"], width=10,
                                         command=lambda: self.choose_color("terminal_bg", terminal_bg_color_btn))
        terminal_bg_color_btn.grid(row=3, column=1, padx=5, pady=5)
        
        # 终端前景色
        ttk.Label(color_frame, text="终端前景:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        terminal_fg_color_btn = tk.Button(color_frame, bg=self.custom_colors["terminal_fg"], width=10,
                                         command=lambda: self.choose_color("terminal_fg", terminal_fg_color_btn))
        terminal_fg_color_btn.grid(row=4, column=1, padx=5, pady=5)
        
        # 高亮颜色
        ttk.Label(color_frame, text="高亮颜色:").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        highlight_color_btn = tk.Button(color_frame, bg=self.custom_colors["highlight"], width=10,
                                       command=lambda: self.choose_color("highlight", highlight_color_btn))
        highlight_color_btn.grid(row=5, column=1, padx=5, pady=5)
        
        # 按钮颜色
        ttk.Label(color_frame, text="按钮颜色:").grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        button_color_btn = tk.Button(color_frame, bg=self.custom_colors["button"], width=10,
                                    command=lambda: self.choose_color("button", button_color_btn))
        button_color_btn.grid(row=6, column=1, padx=5, pady=5)
        
        # 按钮悬停颜色
        ttk.Label(color_frame, text="按钮悬停:").grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)
        button_hover_color_btn = tk.Button(color_frame, bg=self.custom_colors["button_hover"], width=10,
                                          command=lambda: self.choose_color("button_hover", button_hover_color_btn))
        button_hover_color_btn.grid(row=7, column=1, padx=5, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(color_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 应用按钮
        apply_btn = ttk.Button(button_frame, text="应用", command=lambda: self.apply_custom_colors(color_dialog))
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
        # 重置按钮
        reset_btn = ttk.Button(button_frame, text="重置", command=self.reset_colors)
        reset_btn.pack(side=tk.RIGHT, padx=5)
    
    def choose_color(self, color_type, button):
        """
        选择颜色
        
        Args:
            color_type: 颜色类型（如'bg', 'fg'等）
            button: 要更新颜色的按钮对象
        """
        color = colorchooser.askcolor(initialcolor=self.custom_colors[color_type])
        if color[1]:
            self.custom_colors[color_type] = color[1]
            button.config(bg=color[1])
    
    def apply_custom_colors(self, dialog):
        """
        应用自定义颜色
        
        Args:
            dialog: 颜色选择对话框对象
        """
        self._apply_theme_colors()
        dialog.destroy()
    
    def reset_colors(self):
        """
        重置颜色为主题默认值
        
        根据当前主题重置所有颜色为默认值
        """
        if self.current_theme == "light":
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
    
    def browse_key_file(self):
        """
        浏览并选择SSH密钥文件
        
        打开文件选择对话框，让用户选择SSH密钥文件
        """
        file_path = filedialog.askopenfilename(
            title="选择SSH密钥文件",
            filetypes=[("密钥文件", "*.pem;*.ppk;*.key"), ("所有文件", "*.*")]
        )
        if file_path:
            self.key_file_var.set(file_path)
    
    def quick_connect(self):
        """
        快速连接功能
        
        验证必要字段后直接发起连接
        """
        # 快速连接功能
        if self.is_connected:
            messagebox.showinfo("提示", "已经连接到服务器")
            return
        
        # 检查必要字段
        host = self.host_entry.get()
        port = self.port_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not all([host, port, username]):
            messagebox.showerror("错误", "请填写主机、端口和用户名")
            return
        
        if not password and not self.key_file_var.get():
            messagebox.showerror("错误", "请提供密码或密钥文件")
            return
        
        # 连接
        self.connect()
    
    def show_history(self):
        """
        显示历史连接对话框
        
        显示所有保存的连接配置及其最后连接时间
        """
        # 显示历史连接
        history_dialog = tk.Toplevel(self.root)
        history_dialog.title("历史连接")
        history_dialog.geometry("600x400")
        history_dialog.configure(bg=self.custom_colors["bg"])
        
        # 使对话框模态
        history_dialog.transient(self.root)
        history_dialog.grab_set()
        
        # 创建历史记录框架
        history_frame = ttk.Frame(history_dialog)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建历史记录列表
        columns = ("name", "host", "username", "last_connected")
        history_tree = ttk.Treeview(history_frame, columns=columns, show="headings")
        
        # 设置列
        history_tree.heading("name", text="名称")
        history_tree.heading("host", text="主机")
        history_tree.heading("username", text="用户名")
        history_tree.heading("last_connected", text="最后连接")
        
        # 设置列宽
        history_tree.column("name", width=150)
        history_tree.column("host", width=200)
        history_tree.column("username", width=100)
        history_tree.column("last_connected", width=150)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=history_tree.yview)
        history_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充历史记录
        for name, config in self.configs.items():
            if "last_connected" in config and config["last_connected"]:
                history_tree.insert("", tk.END, values=(
                    name,
                    config["host"],
                    config["username"],
                    config["last_connected"]
                ))
        
        # 按钮框架
        button_frame = ttk.Frame(history_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 连接按钮
        connect_btn = ttk.Button(button_frame, text="连接", 
                                command=lambda: self.connect_from_history(history_tree, history_dialog))
        connect_btn.pack(side=tk.RIGHT, padx=5)
        
        # 关闭按钮
        close_btn = ttk.Button(button_frame, text="关闭", command=history_dialog.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def connect_from_history(self, tree, dialog):
        """
        从历史记录中连接
        
        Args:
            tree: 历史记录树形视图
            dialog: 历史记录对话框
        """
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("警告", "请选择一个连接")
            return
        
        values = tree.item(selected_item, "values")
        config_name = values[0]
        
        if config_name in self.configs:
            # 加载配置
            self.config_var.set(config_name)
            self.load_selected_config()
            
            # 关闭对话框
            dialog.destroy()
            
            # 连接
            self.connect()
    
    def browse_local_path(self):
        """
        浏览本地目录
        
        打开目录选择对话框，让用户选择本地目录
        """
        path = filedialog.askdirectory(title="选择本地目录")
        if path:
            self.local_path_var.set(path)
            self.refresh_local_files()
    
    def refresh_local_files(self):
        """
        刷新本地文件列表
        
        读取当前目录下的文件和文件夹，更新文件列表显示
        """
        # 刷新本地文件列表
        self.local_file_listbox.delete(0, tk.END)
        path = self.local_path_var.get()
        
        if not os.path.exists(path):
            return
        
        try:
            # 添加上级目录
            if path != os.path.dirname(path):
                self.local_file_listbox.insert(tk.END, "..")
            
            # 添加目录和文件
            for item in sorted(os.listdir(path)):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    self.local_file_listbox.insert(tk.END, f"[DIR] {item}")
                else:
                    self.local_file_listbox.insert(tk.END, f"[FILE] {item}")
        except Exception as e:
            messagebox.showerror("错误", f"无法读取目录: {str(e)}")
    
    def on_local_file_double_click(self, event):
        """
        处理本地文件双击事件
        
        双击文件夹时进入该文件夹，双击..时返回上级目录
        
        Args:
            event: 鼠标事件对象
        """
        # 处理本地文件双击事件
        selection = self.local_file_listbox.curselection()
        if not selection:
            return
        
        item = self.local_file_listbox.get(selection[0])
        path = self.local_path_var.get()
        
        if item == "..":
            # 上级目录
            new_path = os.path.dirname(path)
            if new_path != path:
                self.local_path_var.set(new_path)
                self.refresh_local_files()
        elif item.startswith("[DIR]"):
            # 进入目录
            dir_name = item[6:]  # 去掉 "[DIR] " 前缀
            new_path = os.path.join(path, dir_name)
            if os.path.isdir(new_path):
                self.local_path_var.set(new_path)
                self.refresh_local_files()
    
    def upload_file(self):
        """
        上传文件到远程服务器
        
        选择本地文件并上传到远程服务器的指定位置
        """
        # 上传文件功能
        if not self.is_connected:
            messagebox.showwarning("警告", "未连接到服务器")
            return
        
        selection = self.local_file_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择要上传的文件")
            return
        
        item = self.local_file_listbox.get(selection[0])
        if not item.startswith("[FILE]"):
            messagebox.showwarning("警告", "请选择文件，而不是目录")
            return
        
        local_path = self.local_path_var.get()
        file_name = item[7:]  # 去掉 "[FILE] " 前缀
        local_file = os.path.join(local_path, file_name)
        
        # 选择远程路径
        remote_path = filedialog.asksaveasfilename(
            title="选择远程保存位置",
            initialfile=file_name,
            parent=self.root
        )
        
        if not remote_path:
            return
        
        # 在新线程中执行上传
        Thread(target=self._upload_file, args=(local_file, remote_path), daemon=True).start()
    
    def _upload_file(self, local_file, remote_path):
        """
        在新线程中执行文件上传
        
        Args:
            local_file: 本地文件路径
            remote_path: 远程保存路径
        """
        try:
            self.status_label.config(text=f"正在上传 {os.path.basename(local_file)}...")
            self.root.update()
            
            # 创建SFTP客户端
            sftp = self.ssh_client.open_sftp()
            
            # 上传文件
            sftp.put(local_file, remote_path)
            
            # 关闭SFTP客户端
            sftp.close()
            
            self.root.after(0, lambda: messagebox.showinfo("成功", f"文件 {os.path.basename(local_file)} 上传成功"))
            self.root.after(0, lambda: self.status_label.config(text="文件上传完成"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("上传错误", str(e)))
            self.root.after(0, lambda: self.status_label.config(text="文件上传失败"))
    
    def download_file(self):
        """
        从远程服务器下载文件
        
        选择远程文件并下载到本地指定位置
        """
        # 下载文件功能
        if not self.is_connected:
            messagebox.showwarning("警告", "未连接到服务器")
            return
        
        # 这里简化处理，实际应用中应该先获取远程文件列表
        remote_file = filedialog.askopenfilename(
            title="选择要下载的远程文件",
            parent=self.root
        )
        
        if not remote_file:
            return
        
        # 选择本地保存路径
        local_path = filedialog.asksaveasfilename(
            title="选择本地保存位置",
            initialfile=os.path.basename(remote_file),
            parent=self.root
        )
        
        if not local_path:
            return
        
        # 在新线程中执行下载
        Thread(target=self._download_file, args=(remote_file, local_path), daemon=True).start()
    
    def _download_file(self, remote_file, local_path):
        """
        在新线程中执行文件下载
        
        Args:
            remote_file: 远程文件路径
            local_path: 本地保存路径
        """
        try:
            self.status_label.config(text=f"正在下载 {os.path.basename(remote_file)}...")
            self.root.update()
            
            # 创建SFTP客户端
            sftp = self.ssh_client.open_sftp()
            
            # 下载文件
            sftp.get(remote_file, local_path)
            
            # 关闭SFTP客户端
            sftp.close()
            
            self.root.after(0, lambda: messagebox.showinfo("成功", f"文件 {os.path.basename(remote_file)} 下载成功"))
            self.root.after(0, lambda: self.status_label.config(text="文件下载完成"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("下载错误", str(e)))
            self.root.after(0, lambda: self.status_label.config(text="文件下载失败"))
    
    def refresh_session_list(self):
        """
        刷新会话列表
        
        更新会话管理界面中的会话列表显示
        """
        # 刷新会话列表
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        for name, config in self.configs.items():
            last_connected = config.get("last_connected", "从未连接")
            self.session_tree.insert("", tk.END, values=(
                config["host"],
                config["username"],
                last_connected
            ), tags=(name,))
    
    def connect_selected_session(self):
        """
        连接选中的会话
        
        从会话列表中选择一个会话并进行连接
        """
        # 连接选中的会话
        selected_item = self.session_tree.focus()
        if not selected_item:
            messagebox.showwarning("警告", "请选择一个会话")
            return
        
        # 获取配置名称
        tags = self.session_tree.item(selected_item, "tags")
        if not tags:
            return
        
        config_name = tags[0]
        if config_name in self.configs:
            # 加载配置
            self.config_var.set(config_name)
            self.load_selected_config()
            
            # 连接
            self.connect()
    
    def edit_selected_session(self):
        """
        编辑选中的会话
        
        从会话列表中选择一个会话并加载其配置进行编辑
        """
        # 编辑选中的会话
        selected_item = self.session_tree.focus()
        if not selected_item:
            messagebox.showwarning("警告", "请选择一个会话")
            return
        
        # 获取配置名称
        tags = self.session_tree.item(selected_item, "tags")
        if not tags:
            return
        
        config_name = tags[0]
        if config_name in self.configs:
            # 加载配置
            self.config_var.set(config_name)
            self.load_selected_config()
            
            # 切换到连接配置标签页
            self.notebook.select(0)
    
    def delete_selected_session(self):
        """
        删除选中的会话
        
        从会话列表和配置文件中删除选中的会话配置
        """
        # 删除选中的会话
        selected_item = self.session_tree.focus()
        if not selected_item:
            messagebox.showwarning("警告", "请选择一个会话")
            return
        
        # 获取配置名称
        tags = self.session_tree.item(selected_item, "tags")
        if not tags:
            return
        
        config_name = tags[0]
        if config_name in self.configs:
            if messagebox.askyesno("确认", f"确定要删除配置 '{config_name}' 吗？"):
                del self.configs[config_name]
                self.save_configs()
                self.update_config_list()
                self.refresh_session_list()
                messagebox.showinfo("成功", f"配置 '{config_name}' 已删除")
    
    def on_window_resize(self, event):
        """
        处理窗口大小改变事件
        
        Args:
            event: 窗口事件对象
        """
        # 响应式布局调整
        if event.widget == self.root:
            # 可以在这里添加响应式布局的逻辑
            pass
    
    def on_closing(self):
        """
        处理窗口关闭事件
        
        如果已连接，询问用户是否断开连接并退出
        """
        if self.is_connected:
            if messagebox.askyesno("确认", "确定要断开连接并退出吗？"):
                self.disconnect()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GMSSHStyleClient(root)
    root.mainloop()