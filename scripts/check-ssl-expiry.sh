#!/bin/bash
# SSL 证书过期检查脚本
# 检查证书剩余有效期，低于阈值时输出警告

CERT_FILE="/root/ecom-chat-bot/ssl/cert.pem"
WARN_DAYS=30

if [ ! -f "$CERT_FILE" ]; then
    echo "[ERROR] 证书文件不存在: $CERT_FILE"
    exit 1
fi

EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

if [ "$DAYS_LEFT" -lt "$WARN_DAYS" ]; then
    echo "[WARNING] SSL 证书将在 ${DAYS_LEFT} 天后过期 (${EXPIRY})"
    echo "请尽快更新 DigiCert 证书并替换以下文件："
    echo "  - /root/ecom-chat-bot/ssl/cert.pem"
    echo "  - /root/ecom-chat-bot/ssl/key.pem"
    echo "替换后运行: cd /root/ecom-chat-bot && docker compose restart nginx"
    exit 2
fi

echo "[OK] SSL 证书有效，剩余 ${DAYS_LEFT} 天 (过期时间: ${EXPIRY})"
