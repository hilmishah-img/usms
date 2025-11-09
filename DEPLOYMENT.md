# USMS API - Production Deployment Guide

This guide provides step-by-step instructions for deploying the USMS REST API in production using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Deployment](#detailed-deployment)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+) or Docker-compatible OS
- **Docker**: 20.10+ with Docker Compose v2
- **CPU**: Minimum 2 cores (recommended: 4+ cores)
- **RAM**: Minimum 2GB (recommended: 4GB+)
- **Disk**: 10GB+ for application and logs
- **Network**: Open port 8000 (or custom port) for API access

### Required Tools

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

## Quick Start

### 1. Pull Pre-built Image

The USMS API is automatically published to GitHub Container Registry (GHCR):

```bash
# Pull latest version
docker pull ghcr.io/azsaurr/usms:latest

# Or pull specific version
docker pull ghcr.io/azsaurr/usms:v0.9.2
```

### 2. Create Environment Configuration

```bash
# Copy production template
cp .env.production .env

# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env file and set USMS_JWT_SECRET
nano .env
```

**Minimum required configuration** in `.env`:

```bash
USMS_JWT_SECRET=your-generated-secret-here
USMS_API_HOST=0.0.0.0
USMS_API_PORT=8000
USMS_API_WORKERS=4
```

### 3. Run API Service

```bash
# Start API service using docker-compose
docker-compose -f docker-compose.prod.yml --profile api up -d

# Verify service is running
docker ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f usms-api
```

### 4. Test API

```bash
# Health check
curl http://localhost:8000/health

# Access API documentation
# Open in browser: http://localhost:8000/docs
```

## Detailed Deployment

### Step 1: Server Preparation

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Create deployment directory
sudo mkdir -p /opt/usms-api
cd /opt/usms-api

# Create data directory for persistence
sudo mkdir -p /opt/usms-api/data

# Set proper permissions
sudo chown -R $USER:$USER /opt/usms-api
```

### Step 2: Clone Repository (Optional)

If you want to use the included docker-compose files:

```bash
git clone https://github.com/hilmishah-img/usms.git /opt/usms-api
cd /opt/usms-api
```

Or create minimal setup:

```bash
# Download only docker-compose.prod.yml
wget https://raw.githubusercontent.com/hilmishah-img/usms/main/docker-compose.prod.yml

# Download .env.production template
wget https://raw.githubusercontent.com/hilmishah-img/usms/main/.env.production
```

### Step 3: Configure Environment

```bash
# Copy template
cp .env.production .env

# Generate strong JWT secret
python3 scripts/generate_jwt_secret.py > .jwt_secret
export USMS_JWT_SECRET=$(cat .jwt_secret)

# Edit configuration
nano .env
```

**Production configuration checklist**:

- [ ] Set strong `USMS_JWT_SECRET`
- [ ] Configure `USMS_API_WORKERS` (formula: 2×CPU cores + 1)
- [ ] Adjust cache TTLs based on usage patterns
- [ ] Set appropriate `USMS_API_RATE_LIMIT`
- [ ] Ensure `USMS_API_RELOAD=false`
- [ ] Review all timeout values

### Step 4: Deploy with Docker Compose

```bash
# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Start API service
docker compose -f docker-compose.prod.yml --profile api up -d

# Verify deployment
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs usms-api
```

### Step 5: Verify Deployment

```bash
# Check container health
docker inspect usms-api | grep Health -A 10

# Test health endpoint
curl http://localhost:8000/health

# Test authentication endpoint
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your-ic-number","password":"your-password"}'

# Access interactive API docs
# Browser: http://localhost:8000/docs
```

## Reverse Proxy Setup

For production deployments, use a reverse proxy (nginx, Traefik, Caddy) to handle:
- HTTPS/TLS termination
- SSL certificate management
- Load balancing (if running multiple instances)
- Request logging
- Rate limiting (additional layer)

### Option 1: Nginx

**Install Nginx**:

```bash
sudo apt-get install nginx
```

**Create configuration** (`/etc/nginx/sites-available/usms-api`):

```nginx
upstream usms_api {
    # Single instance
    server localhost:8000;

    # Multiple instances (load balancing)
    # server localhost:8001;
    # server localhost:8002;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/usms-api-access.log;
    error_log /var/log/nginx/usms-api-error.log;

    # Proxy settings
    location / {
        proxy_pass http://usms_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (bypass logging)
    location /health {
        proxy_pass http://usms_api;
        access_log off;
    }
}
```

**Enable and restart**:

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/usms-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

**SSL Certificate with Let's Encrypt**:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Option 2: Traefik

**Create `docker-compose.traefik.yml`**:

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=your-email@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
    restart: unless-stopped

  usms-api:
    image: ghcr.io/azsaurr/usms:latest
    command: serve --host 0.0.0.0 --port 8000 --workers 4
    env_file: .env
    volumes:
      - usms-api-data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.usms-api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.usms-api.entrypoints=websecure"
      - "traefik.http.routers.usms-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.usms-api.loadbalancer.server.port=8000"
    restart: unless-stopped

volumes:
  usms-api-data:
```

**Deploy**:

```bash
docker compose -f docker-compose.traefik.yml up -d
```

### Option 3: Caddy

**Create `Caddyfile`**:

```
api.yourdomain.com {
    reverse_proxy localhost:8000

    # Automatic HTTPS with Let's Encrypt
    tls your-email@example.com

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }

    # Logging
    log {
        output file /var/log/caddy/usms-api.log
        format json
    }
}
```

**Run Caddy**:

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Copy Caddyfile
sudo cp Caddyfile /etc/caddy/Caddyfile

# Restart Caddy
sudo systemctl restart caddy
```

## Monitoring and Maintenance

### Health Monitoring

**Health check endpoint**:

```bash
# Simple health check
curl http://localhost:8000/health

# Detailed check with auth test
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

**Set up monitoring with cron**:

```bash
# Create health check script
cat > /opt/usms-api/health_check.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $RESPONSE -ne 200 ]; then
    echo "USMS API health check failed! HTTP $RESPONSE"
    # Send alert (email, Slack, etc.)
    # Optionally restart service
    # docker compose -f /opt/usms-api/docker-compose.prod.yml restart usms-api
fi
EOF

chmod +x /opt/usms-api/health_check.sh

# Add to crontab (every 5 minutes)
echo "*/5 * * * * /opt/usms-api/health_check.sh" | crontab -
```

### Log Management

**View logs**:

```bash
# Real-time logs
docker compose -f docker-compose.prod.yml logs -f usms-api

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 usms-api

# Filter by error level
docker compose -f docker-compose.prod.yml logs usms-api | grep ERROR
```

**Log rotation**:

Docker handles log rotation automatically, but you can configure it:

```yaml
# In docker-compose.prod.yml
services:
  usms-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Centralized logging** (optional):

```bash
# Send logs to external service (e.g., Grafana Loki, ELK stack)
# Example with Loki
docker compose -f docker-compose.prod.yml logs -f usms-api | promtail --config.file=promtail-config.yml
```

### Performance Monitoring

**Monitor container stats**:

```bash
# Real-time stats
docker stats usms-api

# Resource usage
docker inspect usms-api | grep -A 20 "Memory"
```

**Cache statistics**:

The API logs cache statistics every 15 minutes. Check logs for:

```
Cache stats - L1: 750/1000 items, L2: 2500 items, Hits: 15234, Misses: 892
```

### Updating the Application

```bash
# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Recreate containers with zero downtime
docker compose -f docker-compose.prod.yml up -d --no-deps --build usms-api

# Verify new version
docker compose -f docker-compose.prod.yml logs usms-api | grep "version"
```

## Backup and Recovery

### What to Backup

1. **Data volume** (`/data` in container):
   - SQLite cache database
   - Webhook database (when implemented)
   - CSV files (if using CSV storage)

2. **Environment configuration**:
   - `.env` file
   - JWT secret

3. **Reverse proxy configuration**:
   - Nginx/Traefik/Caddy configs
   - SSL certificates

### Backup Script

See `scripts/backup.sh` for automated backup solution.

**Manual backup**:

```bash
# Create backup directory
mkdir -p /opt/usms-api/backups

# Backup data volume
docker run --rm \
  -v usms-api-data:/data \
  -v /opt/usms-api/backups:/backup \
  alpine tar czf /backup/usms-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# Backup environment
cp .env /opt/usms-api/backups/.env.$(date +%Y%m%d-%H%M%S)

# List backups
ls -lh /opt/usms-api/backups/
```

**Automated backup with cron**:

```bash
# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/usms-api/scripts/backup.sh" | crontab -
```

### Recovery

**Restore from backup**:

```bash
# Stop API service
docker compose -f docker-compose.prod.yml down

# Restore data volume
docker run --rm \
  -v usms-api-data:/data \
  -v /opt/usms-api/backups:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/usms-data-20250109-020000.tar.gz -C /data"

# Restore environment
cp /opt/usms-api/backups/.env.20250109-020000 .env

# Start service
docker compose -f docker-compose.prod.yml --profile api up -d
```

## Troubleshooting

### Common Issues

#### 1. API Not Starting

**Symptoms**: Container exits immediately

**Check logs**:
```bash
docker compose -f docker-compose.prod.yml logs usms-api
```

**Common causes**:
- Missing or invalid `USMS_JWT_SECRET`
- Port 8000 already in use
- Insufficient memory

**Solutions**:
```bash
# Check environment variables
docker compose -f docker-compose.prod.yml config

# Check port availability
sudo netstat -tlnp | grep 8000

# Increase memory limit (docker-compose.prod.yml)
services:
  usms-api:
    mem_limit: 2g
```

#### 2. Authentication Failures

**Symptoms**: `401 Unauthorized` errors

**Causes**:
- Invalid JWT secret (changed after tokens issued)
- Expired tokens
- Password encryption issues

**Solutions**:
```bash
# Verify JWT secret hasn't changed
grep USMS_JWT_SECRET .env

# Test login endpoint
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your-ic","password":"your-pass"}' -v
```

#### 3. Performance Issues

**Symptoms**: Slow response times, high CPU/memory

**Diagnostics**:
```bash
# Check container resources
docker stats usms-api

# Check cache hit rate (in logs)
docker compose -f docker-compose.prod.yml logs usms-api | grep "Cache stats"

# Check number of requests
docker compose -f docker-compose.prod.yml logs usms-api | grep "GET\|POST" | wc -l
```

**Solutions**:
- Increase worker count
- Increase cache size
- Adjust cache TTLs
- Add more RAM

#### 4. Rate Limiting Issues

**Symptoms**: `429 Too Many Requests`

**Solutions**:
```bash
# Increase rate limits in .env
USMS_API_RATE_LIMIT=200
USMS_API_RATE_WINDOW=3600

# Restart service
docker compose -f docker-compose.prod.yml restart usms-api
```

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or use debug profile
docker compose -f docker-compose.prod.yml --profile debug up
```

## Security Considerations

### Essential Security Measures

1. **JWT Secret Management**
   - Use strong, randomly generated secrets (32+ characters)
   - Never commit secrets to git
   - Rotate secrets periodically
   - Store in secure vault (e.g., HashiCorp Vault, AWS Secrets Manager)

2. **HTTPS/TLS**
   - Always use HTTPS in production
   - Use Let's Encrypt for free SSL certificates
   - Enable HSTS headers
   - Disable SSLv3, TLS 1.0, TLS 1.1

3. **CORS Configuration**
   - Update `api/main.py` to restrict allowed origins
   - Never use `allow_origins=["*"]` in production

4. **Rate Limiting**
   - Configure appropriate limits based on expected usage
   - Monitor for abuse patterns
   - Consider adding IP-based rate limiting at reverse proxy level

5. **Network Security**
   - Use firewall rules (ufw, iptables)
   - Only expose necessary ports
   - Consider using VPN for admin access
   - Implement DDoS protection (Cloudflare, AWS Shield)

6. **Container Security**
   - Run as non-root user (already configured)
   - Keep Docker and base images updated
   - Scan images for vulnerabilities (docker scan, Snyk, Trivy)
   - Use minimal base images

7. **Access Control**
   - Implement IP whitelisting for sensitive endpoints
   - Use strong authentication for any admin features
   - Regularly audit access logs

8. **Data Protection**
   - Encrypt data at rest (volume encryption)
   - Encrypt data in transit (HTTPS)
   - Regular backups with encryption
   - Secure backup storage

### Security Checklist

- [ ] Strong JWT secret configured
- [ ] HTTPS enabled with valid SSL certificate
- [ ] CORS properly configured
- [ ] Rate limiting enabled and tuned
- [ ] Firewall rules configured
- [ ] Regular security updates scheduled
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan documented
- [ ] Security audit completed

## Additional Resources

- **USMS Library Documentation**: https://github.com/hilmishah-img/usms
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Docker Documentation**: https://docs.docker.com
- **Nginx Documentation**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org

## Support

For issues and questions:
- GitHub Issues: https://github.com/hilmishah-img/usms/issues
- Documentation: See CLAUDE.md and README.md
