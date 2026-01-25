#!/bin/bash
set -e

# Configuration
WEB_PORT=5000
DASH_PORT=8587
CONTAINER_WEB="ptof-web-runner"
CONTAINER_DASH="orienta-dashboard"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Restarting Docker Environment (Safe Mode)...${NC}"

# 1. Stop Containers
echo -e "${YELLOW}1. Stopping containers...${NC}"
docker-compose down --remove-orphans || true

# 2. Kill anything on ports (Host side)
echo -e "${YELLOW}2. Cleaning host ports $WEB_PORT and $DASH_PORT...${NC}"

kill_port() {
    local PORT=$1
    local PID=$(lsof -t -i:$PORT 2>/dev/null || true)
    if [ ! -z "$PID" ]; then
        echo -e "${RED}   ⚠️ Port $PORT occupied by PID $PID. Killing...${NC}"
        kill -9 $PID 2>/dev/null || true
    else
        echo -e "${GREEN}   ✅ Port $PORT is free.${NC}"
    fi
}

kill_port $WEB_PORT
kill_port $DASH_PORT

# 3. Prune networks to avoid conflicts (optional but safe)
docker network prune -f >/dev/null 2>&1 || true

# 4. Start Docker Compose
echo -e "${YELLOW}3. Building and Starting containers...${NC}"
docker-compose up --build -d

echo -e "${GREEN}✅ Environment Restarted Successfully!${NC}"
echo -e "   🔗 Web Runner: http://localhost:$WEB_PORT"
echo -e "   🔗 Dashboard:  http://localhost:$DASH_PORT"
