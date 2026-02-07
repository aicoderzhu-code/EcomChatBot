# Nginx HTTPS 配置说明

本目录包含 Nginx 的 HTTPS 配置文件和 SSL 证书生成脚本。

## 目录结构

```
nginx/
├── conf.d/
│   └── default.conf          # Nginx 配置文件
├── ssl/                       # SSL 证书目录（需要创建）
│   ├── cert.pem               # SSL 证书
│   └── key.pem                # SSL 私钥
├── generate-self-signed-cert.sh  # 自签名证书生成脚本（开发环境）
└── README.md                  # 本文件
```

## 开发环境配置

### 1. 生成自签名证书

```bash
cd nginx
chmod +x generate-self-signed-cert.sh
./generate-self-signed-cert.sh
```

这将在 `ssl/` 目录下生成：
- `cert.pem` - SSL 证书
- `key.pem` - SSL 私钥

⚠️ **注意**：自签名证书会在浏览器中显示安全警告，这是正常现象。仅用于开发环境。

### 2. 更新 Docker Compose

在 `docker-compose.yml` 中添加 Nginx 服务：

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - backend
    networks:
      - app-network
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 测试 HTTPS

- HTTP: http://localhost
  - 应该自动重定向到 HTTPS
- HTTPS: https://localhost
  - 正常访问（忽略浏览器证书警告）

## 生产环境配置

### 方案 1: 使用 Let's Encrypt（推荐）

Let's Encrypt 提供免费的 SSL 证书，且受到主流浏览器信任。

#### 使用 Certbot

```bash
# 1. 安装 Certbot
apt-get update
apt-get install certbot python3-certbot-nginx

# 2. 获取证书
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 3. 自动续期
certbot renew --dry-run
```

#### 使用 Docker + Certbot

```yaml
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./nginx/ssl:/etc/letsencrypt
      - ./nginx/certbot-webroot:/var/www/certbot
    command: certonly --webroot -w /var/www/certbot --email admin@yourdomain.com -d yourdomain.com --agree-tos --no-eff-email
```

然后更新 `nginx/conf.d/default.conf`：

```nginx
ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
```

### 方案 2: 使用商业证书

1. 从证书颁发机构（CA）购买 SSL 证书
2. 下载证书文件（通常包括 `.crt` 和 `.key` 文件）
3. 将证书放置到 `nginx/ssl/` 目录
4. 更新 `default.conf` 中的证书路径

```nginx
ssl_certificate /etc/nginx/ssl/yourdomain.com.crt;
ssl_certificate_key /etc/nginx/ssl/yourdomain.com.key;
```

### 方案 3: 使用云服务商的负载均衡器

如果使用 AWS、阿里云等云服务，推荐在负载均衡器层面配置 SSL：

- AWS: Application Load Balancer (ALB) + ACM 证书
- 阿里云: SLB + 免费证书
- 腾讯云: CLB + SSL 证书

此方案下，后端服务只需处理 HTTP 流量，SSL 终止在负载均衡器层。

## 配置文件说明

### default.conf

#### HTTP → HTTPS 重定向

```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;  # 强制重定向
}
```

#### SSL 配置

```nginx
ssl_protocols TLSv1.2 TLSv1.3;  # 仅允许 TLS 1.2 和 1.3
ssl_ciphers '...';               # 安全的加密套件
```

#### 安全头部

```nginx
add_header Strict-Transport-Security "max-age=31536000";  # HSTS
add_header X-Frame-Options "SAMEORIGIN";                   # 防止点击劫持
add_header X-Content-Type-Options "nosniff";               # 防止 MIME 嗅探
add_header X-XSS-Protection "1; mode=block";               # XSS 保护
```

## 安全最佳实践

### 1. 证书管理

- ✅ 使用强加密算法（RSA 2048位或更高）
- ✅ 定期更新证书（Let's Encrypt 每90天自动续期）
- ✅ 妥善保管私钥文件（设置只读权限）
- ❌ 不要将私钥提交到 Git 仓库

### 2. SSL/TLS 配置

- ✅ 禁用 SSLv3、TLSv1.0、TLSv1.1（已过时且不安全）
- ✅ 仅使用强加密套件
- ✅ 启用 HSTS（防止中间人攻击）
- ✅ 启用 OCSP Stapling（改善性能）

### 3. 防火墙规则

```bash
# 仅开放 80 和 443 端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 4. 证书透明度

将证书提交到 Certificate Transparency logs，提高可信度：

```nginx
ssl_ct on;
ssl_ct_static_scts /path/to/scts;
```

## 测试工具

### 1. SSL Labs SSL Test

https://www.ssllabs.com/ssltest/

评估 SSL 配置质量，目标：A+ 评分

### 2. testssl.sh

```bash
git clone https://github.com/drwetter/testssl.sh.git
cd testssl.sh
./testssl.sh https://yourdomain.com
```

### 3. 本地测试

```bash
# 检查证书有效期
openssl x509 -in nginx/ssl/cert.pem -noout -dates

# 测试 HTTPS 连接
curl -v https://localhost -k

# 测试 HTTP → HTTPS 重定向
curl -I http://localhost
```

## 监控和维护

### 证书过期监控

添加定时任务检查证书有效期：

```bash
# 添加到 crontab
0 0 * * * certbot renew --quiet --deploy-hook "nginx -s reload"
```

### 日志位置

- 访问日志: `nginx/logs/access.log`
- 错误日志: `nginx/logs/error.log`

### 性能优化

```nginx
# 启用 HTTP/2
listen 443 ssl http2;

# 启用 gzip 压缩
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# SSL 会话缓存
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

## 故障排查

### 问题 1: "502 Bad Gateway"

**原因**: Nginx 无法连接到后端服务

**解决**:
```bash
# 检查后端服务是否运行
docker-compose ps backend

# 检查网络连接
docker-compose exec nginx ping backend
```

### 问题 2: "SSL certificate problem"

**原因**: 证书配置错误或证书文件不存在

**解决**:
```bash
# 检查证书文件
ls -la nginx/ssl/

# 验证证书
openssl x509 -in nginx/ssl/cert.pem -text -noout
```

### 问题 3: "NET::ERR_CERT_AUTHORITY_INVALID"

**原因**: 使用自签名证书（开发环境正常）

**解决**:
- 开发环境：在浏览器中点击"继续访问"
- 生产环境：使用 Let's Encrypt 或购买的证书

## 参考资料

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Nginx SSL Module Documentation](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [OWASP TLS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
