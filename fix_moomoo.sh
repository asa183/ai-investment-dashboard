#!/bin/bash
echo "Downloading FutuOpenD-rs (High-Performance Rust Edition)..."
mkdir -p /opt/futuopend
cd /opt/futuopend
curl -sL https://futuapi.com/releases/rs-v1.4.122/futu-opend-rs-1.4.122-linux-x86_64.tar.gz | tar -xz

echo "Generating Configuration..."
cat <<EOF > FutuOpenD.xml
<?xml version="1.0" encoding="utf-8"?>
<xml>
  <login_account>asahi@syncra.co.jp</login_account>
  <login_pwd_md5>b051329aab4910e811257f520553bb08</login_pwd_md5>
  <ip>0.0.0.0</ip>
</xml>
EOF

echo "Starting FutuOpenD-rs in background..."
pkill -f futu-opend-rs || true
nohup ./futu-opend-rs > futu.log 2>&1 &

echo "Done! Moomoo Gateway is now running on port 11111."
