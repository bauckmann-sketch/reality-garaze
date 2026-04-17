#!/bin/bash
# Deploy script for Reality-garaze to Hetzner VPS
set -e

SERVER="root@49.13.75.133"
PASS="rgeTAqH4kCRb"
PROJECT_DIR="/root/reality-garaze"

echo "=== Step 1: Install Docker on server ==="
expect -c "
spawn ssh -o StrictHostKeyChecking=no $SERVER {
  # Check if docker exists
  if command -v docker &> /dev/null; then
    echo 'Docker already installed'
  else
    echo 'Installing Docker...'
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo 'Docker installed!'
  fi
  
  # Install docker compose plugin if missing
  docker compose version 2>/dev/null || {
    apt-get update && apt-get install -y docker-compose-plugin
  }
  
  docker --version
  docker compose version
}
expect \"password:\"
send \"$PASS\r\"
expect eof
"

echo ""
echo "=== Step 2: Upload project files ==="
# Create tarball of project (exclude unnecessary files)
cd "$(dirname "$0")/.."
tar czf /tmp/reality-garaze.tar.gz \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='sreality_tracker.db' \
  --exclude='node_modules' \
  .

echo "Tarball created: $(du -h /tmp/reality-garaze.tar.gz | cut -f1)"

# Upload
expect -c "
spawn scp -o StrictHostKeyChecking=no /tmp/reality-garaze.tar.gz $SERVER:/tmp/
expect \"password:\"
send \"$PASS\r\"
expect eof
"

echo ""
echo "=== Step 3: Extract and deploy ==="
expect -c "
spawn ssh -o StrictHostKeyChecking=no $SERVER {
  mkdir -p $PROJECT_DIR
  cd $PROJECT_DIR
  tar xzf /tmp/reality-garaze.tar.gz
  rm /tmp/reality-garaze.tar.gz
  
  # Create .env for production
  cat > .env << 'ENVEOF'
DB_USER=sreality
DB_PASSWORD=sreality_secure_2026
DATABASE_URL=postgresql://sreality:sreality_secure_2026@db:5432/sreality_tracker
OPENAI_API_KEY=
APP_PASSWORD=
SCRAPE_INTERVAL_HOURS=12
REQUEST_DELAY_MIN=2.0
REQUEST_DELAY_MAX=4.0
ENVEOF
  
  echo 'Building and starting containers...'
  docker compose down 2>/dev/null || true
  docker compose build --no-cache
  docker compose up -d
  
  sleep 5
  echo ''
  echo '=== Container status ==='
  docker compose ps
  echo ''
  echo '=== Logs ==='
  docker compose logs --tail 20
}
expect \"password:\"
send \"$PASS\r\"
expect eof
"

echo ""
echo "========================================="
echo "  Deploy complete!"
echo "  Dashboard: http://49.13.75.133:8501"
echo "========================================="
