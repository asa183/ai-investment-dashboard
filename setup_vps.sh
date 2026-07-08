#!/bin/bash
set -e

echo "=== 🚀 AI Trading Bot VPS Auto Setup ==="

# 1. System Update
echo "1. Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install Docker & Docker Compose
echo "2. Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    # Install Docker Compose V2
    apt-get install docker-compose-plugin -y
else
    echo "Docker already installed."
fi

# 3. Setup FutuOpenD
echo "3. Setting up FutuOpenD (Moomoo API Gateway)..."
mkdir -p /opt/futuopend
cd /opt/futuopend
# Download the latest Linux CLI version (Simulated download for now)
wget -qO futuopend.tar.gz https://softwarefile.moomoo.com/FutuOpenD_8.3.4328_Ubuntu16.04.tar.gz || true
if [ -f futuopend.tar.gz ]; then
    tar -xzf futuopend.tar.gz
    rm futuopend.tar.gz
fi

# Generate FutuOpenD.xml (assuming MOOMOO_ID and MOOMOO_PASSWORD_MD5 are exported)
MOOMOO_ID="${MOOMOO_ID:-}"
MOOMOO_PASSWORD_MD5="${MOOMOO_PASSWORD_MD5:-}"

if [ -n "$MOOMOO_ID" ] && [ -n "$MOOMOO_PASSWORD_MD5" ]; then
cat <<EOF > FutuOpenD.xml
<?xml version="1.0" encoding="utf-8"?>
<FutuOpenD>
  <login_account>$MOOMOO_ID</login_account>
  <trade_pwd_md5>$MOOMOO_PASSWORD_MD5</trade_pwd_md5>
  <is_enable_sync_tck>1</is_enable_sync_tck>
  <futu_api_ip>0.0.0.0</futu_api_ip>
  <futu_api_port>11111</futu_api_port>
</FutuOpenD>
EOF
    echo "FutuOpenD.xml configured successfully."
else
    echo "Warning: MOOMOO_ID or MOOMOO_PASSWORD_MD5 not set. Please configure FutuOpenD.xml manually."
fi

# 4. Clone / Prepare Workspace
echo "4. Setting up Workspace..."
mkdir -p /app/ai-investment-dashboard
cd /app/ai-investment-dashboard
# Assuming source code will be rsynced here...

echo "=== ✅ Setup completed. Ready to run docker-compose up -d ==="
