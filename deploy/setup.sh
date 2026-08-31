#!/usr/bin/env bash
# FondOntology 一键部署脚本（Ubuntu/Debian，root 执行）
# 用法: sudo bash setup.sh /opt/fondontology ubuntu
set -euo pipefail

APP_DIR="${1:-/opt/fondontology}"
APP_USER="${2:-ubuntu}"

echo "==> 安装基础依赖"
apt-get update -qq
apt-get install -y -qq nginx git curl

echo "==> 安装 uv（用户: ${APP_USER}）"
sudo -u "$APP_USER" curl -LsSf https://astral.sh/uv/install.sh | sudo -u "$APP_USER" sh
UV_BIN="/home/${APP_USER}/.local/bin/uv"

if [ ! -d "$APP_DIR" ]; then
  echo "错误: 项目目录 ${APP_DIR} 不存在，请先上传代码（git clone 或 rsync）"
  exit 1
fi

echo "==> 同步依赖"
cd "$APP_DIR"
sudo -u "$APP_USER" "$UV_BIN" sync

echo "==> 安装 systemd 服务"
sed -e "s|/opt/fondontology|${APP_DIR}|g" \
    -e "s|User=ubuntu|User=${APP_USER}|g" \
    -e "s|/home/ubuntu|/home/${APP_USER}|g" \
    "$APP_DIR/deploy/fondontology.service" > /etc/systemd/system/fondontology.service
systemctl daemon-reload
systemctl enable --now fondontology

echo "==> 配置 nginx 反向代理（含基础密码保护）"
# 生成访问密码，交互输入两次（也可用 htpasswd 工具管理）
apt-get install -y -qq apache2-utils
htpasswd -c /etc/nginx/.htpasswd_fondontology "$APP_USER"

cat > /etc/nginx/sites-available/fondontology <<'EOF'
server {
    listen 80;
    server_name _;

    # 基础认证：浏览器会弹登录框
    auth_basic "FondOntology";
    auth_basic_user_file /etc/nginx/.htpasswd_fondontology;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # 本体图较大时放宽超时
        proxy_read_timeout 120s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/fondontology /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> 完成！访问 http://服务器公网IP/ 试试"
systemctl status fondontology --no-pager -l | head -15
