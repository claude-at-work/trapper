#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if ! python3 -c "import flask" 2>/dev/null; then
  echo "Installing dependencies..."
  pip3 install -r requirements.txt -q
fi

echo "Trapper running at http://0.0.0.0:5000"
echo "Open http://<your-machine-ip>:5000 on your phone"
exec python3 app.py
