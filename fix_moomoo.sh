#!/bin/bash
echo "Downloading FutuOpenD-rs (High-Performance Rust Edition)..."
mkdir -p /opt/futuopend
cd /opt/futuopend
curl -sL https://futuapi.com/releases/rs-v1.4.122/futu-opend-rs-1.4.122-linux-x86_64.tar.gz | tar -xz

# バイナリを探して現在のディレクトリにコピー
BINARY_PATH=$(find . -name "futu-opend" -type f | head -n 1)
if [ -n "$BINARY_PATH" ]; then
    cp "$BINARY_PATH" ./futu-opend_bin
    chmod +x ./futu-opend_bin
fi

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
pkill -f futu-opend || true
nohup ./futu-opend_bin > futu.log 2>&1 &
sleep 2

echo "Checking if it started..."
cat futu.log
echo "Done! Moomoo Gateway is now running on port 11111."
