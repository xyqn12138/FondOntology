#!/usr/bin/env bash
# FondOntology 一键部署脚本（Ubuntu/Debian）
# 用法: 在项目目录下执行  sudo bash deploy/setup.sh
# 自动检测项目路径与运行用户，无需传参；随机生成访问密码并打印。
set -euo pipefail

# ---- 自动检测项目目录与运行用户 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
RUN_USER="${SUDO_USER:-$USER}"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
[ -z "$RUN_HOME" ] && RUN_HOME="/root"
UV_BIN="$RUN_HOME/.local/bin/uv"
PORT="${PORT:-8000}"

echo "==> 项目目录: $APP_DIR"
echo "==> 运行用户: $RUN_USER (home: $RUN_HOME)"
echo "==> 服务端口: $PORT"

if [ ! -f "$APP_DIR/pyproject.toml" ]; then
  echo "错误: 在 $APP_DIR 下没找到 pyproject.toml，请把本脚本放在项目内的 deploy/ 目录再运行"
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "错误: 请用 root 执行：sudo bash deploy/setup.sh"
  exit 1
fi

# ---- 1. 安装系统依赖 ----
echo "==> [1/7] 安装基础依赖"
apt-get update -qq
apt-get install -y -qq nginx git curl apache2-utils ufw

# ---- 2. 安装 uv ----
echo "==> [2/7] 安装 uv"
if [ -x "$UV_BIN" ]; then
  echo "    uv 已存在，跳过"
else
  sudo -u "$RUN_USER" curl -LsSf https://astral.sh/uv/install.sh | sudo -u "$RUN_USER" sh
fi

# ---- 3. 同步 Python 依赖 ----
echo "==> [3/7] 同步依赖 (uv sync)"
cd "$APP_DIR"
sudo -u "$RUN_USER" "$UV_BIN" sync

# ---- 4. 生成本体文件（若缺失）----
echo "==> [4/7] 检查本体产物"
TTL="$APP_DIR/artifacts/cnfo/cnfo-fund-tbox.ttl"
if [ ! -f "$TTL" ]; then
  echo "    未发现 $TTL ，执行 build 生成"
  sudo -u "$RUN_USER" "$UV_BIN" run python -m fondontology.cli build
fi

# ---- 5. systemd 常驻服务 ----
echo "==> [5/7] 注册 systemd 服务"
cat > /etc/systemd/system/fondontology.service <<EOF
[Unit]
Description=FondOntology Explorer
After=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$APP_DIR
ExecStart=$UV_BIN run python -m fondontology.explorer --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=5
MemoryMax=1400M

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now fondontology
sleep 2
systemctl is-active --quiet fondontology && echo "    fondontology 服务已启动" || echo "    ⚠ 服务未正常运行，请查 journalctl -u fondontology"

# ---- 6. nginx 反向代理 + 随机密码 ----
echo "==> [6/7] 配置 nginx（含随机访问密码）"
ADMIN_USER="admin"
ADMIN_PASS="$(head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 12)"
htpasswd -bc /etc/nginx/.htpasswd_fondontology "$ADMIN_USER" "$ADMIN_PASS" >/dev/null 2>&1

cat > /etc/nginx/sites-available/fondontology <<EOF
server {
    listen 80;
    server_name _;

    auth_basic "FondOntology";
    auth_basic_user_file /etc/nginx/.htpasswd_fondontology;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/fondontology /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 放行系统防火墙（云安全组需另行放行）
ufw allow 80/tcp >/dev/null 2>&1 || true

# ---- 7. 完成 ----
PUB_IP="$(curl -s --max-time 5 https://ifconfig.me || echo '服务器公网IP')"
echo ""
echo "========================================================"
echo "  部署完成！"
echo "  访问地址: http://$PUB_IP/"
echo "  登录账号: $ADMIN_USER"
echo "  登录密码: $ADMIN_PASS   （请妥善保存，仅显示一次）"
echo "========================================================"
echo "  查看服务状态: systemctl status fondontology"
echo "  查看运行日志: journalctl -u fondontology -f"
echo "  重启服务:     systemctl restart fondontology"
echo "  修改密码:     htpasswd /etc/nginx/.htpasswd_fondontology admin"
echo ""
echo "  ⚠ 若仍打不开页面，请到云服务器控制台「安全组」放行 80/TCP 入站"
echo "========================================================"
