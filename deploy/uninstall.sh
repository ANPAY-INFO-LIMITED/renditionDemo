#!/bin/bash
# ===========================================
# RenditionDemo 卸载脚本
# ===========================================

set -e

APP_DIR="/var/www/renditiondemo"
SERVICE_NAME="renditiondemo"

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

main() {
    echo "=========================================="
    echo "  RenditionDemo 卸载脚本"
    echo "=========================================="

    check_root

    # 停止并禁用服务
    log_info "停止服务..."
    systemctl stop ${SERVICE_NAME} 2>/dev/null || true
    systemctl disable ${SERVICE_NAME} 2>/dev/null || true

    # 删除 Systemd 服务文件
    log_info "删除服务文件..."
    rm -f /etc/systemd/system/${SERVICE_NAME}.service
    systemctl daemon-reload

    # 删除 Nginx 配置
    log_info "删除 Nginx 配置..."
    rm -f /etc/nginx/sites-enabled/renditiondemo
    rm -f /etc/nginx/sites-available/renditiondemo
    nginx -t && systemctl reload nginx

    # 询问是否删除应用数据
    read -p "是否删除应用数据和目录？[y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_warn "删除应用目录..."
        rm -rf ${APP_DIR}
    else
        log_info "保留应用目录"
    fi

    log_info "卸载完成！"
}

main "$@"
