#!/bin/bash
# ===========================================
# RenditionDemo 部署脚本
# ===========================================

set -e

# 配置变量（根据实际情况修改）
DOMAIN="your-domain.com"                    # 你的域名
APP_DIR="/var/www/renditiondemo"           # 应用安装目录
GIT_REPO=""                                # Git 仓库地址（留空则使用本地代码）
TASKS_DIR="${APP_DIR}/tasks"               # 任务数据目录
VENV_DIR="${APP_DIR}/venv"                 # Python 虚拟环境

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 检查 root 权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行，请使用 sudo"
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    apt update
    apt install -y \
        python3.11 \
        python3.11-venv \
        python3-pip \
        git \
        nginx \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        ffmpeg
    log_info "系统依赖安装完成"
}

# 创建应用目录
setup_directories() {
    log_info "创建应用目录..."
    mkdir -p ${APP_DIR}
    mkdir -p ${TASKS_DIR}
    mkdir -p /var/log/renditiondemo

    # 创建 www-data 用户组
    chown -R www-data:www-data ${APP_DIR}
    chmod -R 755 ${APP_DIR}
    log_info "目录创建完成"
}

# 部署应用代码
deploy_code() {
    log_info "部署应用代码..."

    if [ -n "$GIT_REPO" ]; then
        # 从 Git 克隆
        cd ${APP_DIR}
        git clone ${GIT_REPO} .
    else
        # 使用当前目录的代码（假设部署脚本在项目根目录运行）
        log_warn "未指定 Git 仓库，将使用当前目录代码"
    fi

    # 确保任务目录存在
    mkdir -p tasks
    chown -R www-data:www-data ${APP_DIR}
    log_info "代码部署完成"
}

# 创建 Python 虚拟环境
setup_venv() {
    log_info "创建 Python 虚拟环境..."

    if [ -d "${VENV_DIR}" ]; then
        log_warn "虚拟环境已存在，将重新创建"
        rm -rf ${VENV_DIR}
    fi

    python3.11 -m venv ${VENV_DIR}
    source ${VENV_DIR}/bin/activate

    # 升级 pip
    pip install --upgrade pip

    # 安装依赖
    pip install -r ${APP_DIR}/requirements.txt

    # 安装额外的系统依赖（OpenCV 需要）
    pip install opencv-python-headless

    log_info "虚拟环境创建完成"
}

# 配置 Nginx
setup_nginx() {
    log_info "配置 Nginx..."

    # 复制 Nginx 配置
    cp ${APP_DIR}/deploy/nginx.conf /etc/nginx/sites-available/renditiondemo

    # 替换域名
    sed -i "s/your-domain.com/${DOMAIN}/g" /etc/nginx/sites-available/renditiondemo

    # 启用站点
    ln -sf /etc/nginx/sites-available/renditiondemo /etc/nginx/sites-enabled/

    # 测试配置
    nginx -t || log_error "Nginx 配置测试失败"

    # 重载 Nginx
    systemctl reload nginx
    log_info "Nginx 配置完成"
}

# 配置 Systemd 服务
setup_systemd() {
    log_info "配置 Systemd 服务..."

    cp ${APP_DIR}/deploy/renditiondemo.service /etc/systemd/system/

    systemctl daemon-reload
    systemctl enable renditiondemo
    systemctl start renditiondemo

    # 检查服务状态
    sleep 3
    systemctl status renditiondemo --no-pager

    log_info "Systemd 服务配置完成"
}

# 主函数
main() {
    echo "=========================================="
    echo "  RenditionDemo 部署脚本"
    echo "=========================================="

    check_root
    install_system_deps
    setup_directories
    deploy_code
    setup_venv
    setup_nginx
    setup_systemd

    # 提示 SSL 配置
    echo ""
    log_info "=========================================="
    log_info "部署完成！"
    log_info "=========================================="
    echo ""
    echo "1. 编辑 Nginx 配置，填入你的 SSL 证书路径："
    echo "   sudo nano /etc/nginx/sites-available/renditiondemo"
    echo "   修改 ssl_certificate 和 ssl_certificate_key"
    echo ""
    echo "2. 重载 Nginx："
    echo "   sudo nginx -t && sudo systemctl reload nginx"
    echo ""
    echo "3. 查看服务状态："
    echo "   systemctl status renditiondemo"
    echo ""
    echo "4. 查看日志："
    echo "   journalctl -u renditiondemo -f"
    echo ""
    echo "5. 重启服务："
    echo "   systemctl restart renditiondemo"
    echo ""
}

main "$@"
