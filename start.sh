#!/bin/bash

# Parse args
BIND="127.0.0.1"
IP="localhost"
VAULT_PATH="/mnt/vault"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --expose)
      BIND="0.0.0.0"
      IP=$(hostname -I | awk '{print $1}')
      shift
      ;;
    --path)
      if [ -n "$2" ]; then
        VAULT_PATH="$2"
        shift 2
      else
        echo "Error: --path requires a value"
        exit 1
      fi
      ;;
    *)
      shift
      ;;
  esac
done

# Function to cleanup all started background processes
cleanup() {
  echo
  echo "Stopping all services..."
  [ -n "$KIWIX_PID" ] && kill "$KIWIX_PID"
  [ -n "$CALIBRE_PID" ] && kill "$CALIBRE_PID"
  [ -n "$MEILI_PID" ] && kill "$MEILI_PID"
  [ -n "$HTTP_PID" ] && kill "$HTTP_PID"
  [ -n "$JELLYFIN_PID" ] && kill "$JELLYFIN_PID"
  sudo systemctl stop jellyfin
  wait
  echo "All services stopped."
  exit 0
}

trap cleanup INT
sleep 3

sudo mount /dev/sda $VAULT_PATH

# Start Kiwix
kiwix-serve --port 8888 --address $BIND $VAULT_PATH/zim/*.zim &
KIWIX_PID=$!

# Start Calibre-Web
./venv/bin/cps -i $BIND &
CALIBRE_PID=$!

# Start MeiliSearch
./meilisearch --db-path $VAULT_PATH/meili-data --http-addr $BIND:7700 --no-analytics &
MEILI_PID=$!

# Start Jellyfin
sudo systemctl start jellyfin

# Start landing page server
python3 -m http.server 5500 --bind $BIND --directory ./ &
HTTP_PID=$!

echo "All services started:"
echo "  Landing page: http://$IP:5500"
echo "  Kiwix:        http://$IP:8888"
echo "  Calibre-Web:  http://$IP:8083"
echo "  MeiliSearch:  http://$IP:7700"
echo "  Jellyfin:     http://$IP:8096"

# Wait forever until trapped (so ctrl+c works)
wait