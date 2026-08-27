# RenditionDemo 部署文档

## 环境要求

- Ubuntu 20.04+ (本文档基于 Ubuntu 22.04)
- Nginx
- Python 3.8+ (推荐 3.10+)
- Git
- FFmpeg

---

## 快速部署

### 方式一：使用一键部署脚本

```bash
# 1. 上传代码到服务器（使用 scp/rsync/git 等方式）
scp -r ./renditionDemo user@your-server:/tmp/

# 2. SSH 登录服务器
ssh user@your-server

# 3. 执行部署脚本
cd /tmp/renditionDemo/deploy
chmod +x deploy.sh
sudo ./deploy.sh
```

### 方式二：手动部署

#### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    fonts-noto-cjk \
    fonts-wqy-zenhei
```

#### 2. 创建应用目录

```bash
sudo mkdir -p /var/www/renditiondemo
sudo chown -R www-data:www-data /var/www/renditiondemo
```

#### 3. 部署代码

```bash
# 方式 A: 使用 Git
cd /var/www/renditiondemo
sudo -u www-data git clone YOUR_GIT_REPO .

# 方式 B: 直接复制
sudo cp -r /path/to/renditionDemo/* /var/www/renditiondemo/
sudo chown -R www-data:www-data /var/www/renditiondemo
```

#### 4. 创建虚拟环境并安装依赖

```bash
cd /var/www/renditiondemo
sudo python3.11 -m venv venv
sudo chown -R www-data:www-data venv

# 激活虚拟环境并安装
sudo -u www-data /var/www/renditiondemo/venv/bin/pip install --upgrade pip
sudo -u www-data /var/www/renditiondemo/venv/bin/pip install -r requirements.txt
sudo -u www-data /var/www/renditiondemo/venv/bin/pip install opencv-python-headless
```

#### 5. 配置环境变量

```bash
sudo cp /var/www/renditiondemo/deploy/.env.example /var/www/renditiondemo/.env
sudo nano /var/www/renditiondemo/.env  # 编辑填入实际值
sudo chown www-data:www-data /var/www/renditiondemo/.env
sudo chmod 600 /var/www/renditiondemo/.env
```

#### 6. 配置 Nginx

```bash
# 复制并编辑配置
sudo cp /var/www/renditiondemo/deploy/nginx.conf /etc/nginx/sites-available/renditiondemo
sudo nano /etc/nginx/sites-available/renditiondemo
# 将 your-domain.com 替换为你的实际域名
# 将 SSL 证书路径替换为你的实际路径

# 启用站点
sudo ln -sf /etc/nginx/sites-available/renditiondemo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 7. 配置 SSL（使用已有证书）

将你的证书文件上传到服务器，并确保 `nginx.conf` 中的证书路径正确：

```bash
# 示例：上传证书
scp /path/to/your-cert.pem user@your-server:/etc/nginx/ssl/
scp /path/to/your-key.pem user@your-server:/etc/nginx/ssl/

# 然后编辑 nginx.conf 中的证书路径
sudo nano /etc/nginx/sites-available/renditiondemo
```

#### 8. 配置 Systemd 服务

```bash
sudo cp /var/www/renditiondemo/deploy/renditiondemo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable renditiondemo
sudo systemctl start renditiondemo
```

---

## 服务管理

### 查看服务状态
```bash
sudo systemctl status renditiondemo
```

### 查看应用日志
```bash
# Systemd 日志
sudo journalctl -u renditiondemo -f

# Nginx 日志
sudo tail -f /var/log/nginx/renditiondemo_access.log
sudo tail -f /var/log/nginx/renditiondemo_error.log
```

### 重启服务
```bash
sudo systemctl restart renditiondemo
sudo systemctl reload nginx
```

### 停止服务
```bash
sudo systemctl stop renditiondemo
```

---

## 目录结构

部署后的目录结构：

```
/var/www/renditiondemo/
├── main.py                 # Streamlit 入口
├── requirements.txt        # Python 依赖
├── modules/                # 业务模块
├── pages/                  # Streamlit 页面
├── tasks/                  # 任务数据（重要！）
├── deploy/                 # 部署配置文件
│   ├── nginx.conf
│   ├── renditiondemo.service
│   └── .env.example
└── venv/                   # Python 虚拟环境
```

---

## 数据备份

任务数据存储在 `/var/www/renditiondemo/tasks/` 目录，**非常重要**，建议定期备份：

```bash
# 备份任务数据
sudo tar -czf renditiondemo_tasks_backup_$(date +%Y%m%d).tar.gz \
    /var/www/renditiondemo/tasks/

# 恢复到新服务器
sudo tar -xzf renditiondemo_tasks_backup_xxxx.tar.gz -C /
```

---

## 故障排查

### 1. 服务启动失败

```bash
# 查看详细错误
sudo journalctl -u renditiondemo -n 50

# 常见问题：
# - 端口被占用：lsof -i :8501
# - 权限问题：检查目录权限 chown -R www-data:www-data /var/www/renditiondemo
```

### 2. Nginx 502 错误

```bash
# 检查 Streamlit 是否正常运行
sudo systemctl status renditiondemo

# 检查 Nginx 错误日志
sudo tail -f /var/log/nginx/renditiondemo_error.log
```

### 3. 上传文件失败

```bash
# 检查 Nginx 上传大小限制
# 确保 nginx.conf 中 client_max_body_size 足够大

# 检查磁盘空间
df -h
```

---

## 注意事项

1. **防火墙设置**：确保 80 和 443 端口开放
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

2. **SSL 证书**：使用你已有的证书，无需自动续期配置

3. **定期维护**：
   - 清理旧任务数据
   - 更新依赖包
   - 监控磁盘空间

---

## 卸载

```bash
cd /var/www/renditiondemo/deploy
chmod +x uninstall.sh
sudo ./uninstall.sh
```
