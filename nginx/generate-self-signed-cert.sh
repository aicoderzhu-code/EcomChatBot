#!/bin/bash
#
# 生成自签名SSL证书（用于开发环境）
# 生产环境请使用 Let's Encrypt 或购买的证书
#

# 创建SSL目录
mkdir -p ./ssl

# 生成私钥和自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ./ssl/key.pem \
    -out ./ssl/cert.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=EcomChatBot/OU=Dev/CN=localhost"

echo "✅ 自签名证书生成成功！"
echo "   证书位置: ./ssl/cert.pem"
echo "   私钥位置: ./ssl/key.pem"
echo ""
echo "⚠️  注意: 自签名证书仅用于开发环境"
echo "   浏览器会显示安全警告，这是正常现象"
echo "   生产环境请使用 Let's Encrypt 或购买的证书"