#!/bin/bash

# Parse args
if [ "$1" = "--expose" ]; then
  BIND="0.0.0.0"
  IP=$(hostname -I | awk '{print $1}')
else
  BIND="127.0.0.1"
  IP="localhost"
fi

# Function to cleanup all started background processes
cleanup() {
  echo
  echo "Stopping all services..."
  [ -n "$KIWIX_PID" ] && kill "$KIWIX_PID"
  [ -n "$CALIBRE_PID" ] && kill "$CALIBRE_PID"
  [ -n "$MEILI_PID" ] && kill "$MEILI_PID"
  [ -n "$HTTP_PID" ] && kill "$HTTP_PID"
  wait
  echo "All services stopped."
  exit 0
}

trap cleanup INT
sleep 3

# Start Kiwix
kiwix-serve --port 8888 --address $BIND /mnt/vault/zim/*.zim &
KIWIX_PID=$!

# Start Calibre-Web
/mnt/vault/pdf/calibre-web-env/bin/cps -i $BIND &
CALIBRE_PID=$!

# Start MeiliSearch
~/Documents/prep/meilisearch --db-path /mnt/vault/meili-data --http-addr $BIND:7700 --no-analytics &


# Start landing page server
python3 -m http.server 5500 --bind $BIND --directory $HOME/Documents/prep &
HTTP_PID=$!

echo "All services started:"
echo "  Landing page: http://$IP:5500"
echo "  Kiwix:        http://$IP:8888"
echo "  Calibre-Web:  http://$IP:8083"
echo "  MeiliSearch:  http://$IP:7700"

# Wait forever until trapped (so ctrl+c works)
wait