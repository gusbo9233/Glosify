#!/usr/bin/env bash
set -euo pipefail

# Run both backend + frontend on a Raspberry Pi (or any Linux box).
# - Backend: Flask (app.py) on :5001
# - Frontend: Expo web dev server on :8081
#
# Usage (on the Pi):
#   cd /opt/glosify
#   chmod +x ./deploy/run_pi.sh
#   ./deploy/run_pi.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-5001}"
FRONTEND_PORT="${FRONTEND_PORT:-8081}"

export CI="${CI:-false}"
export FORCE_COLOR="${FORCE_COLOR:-0}"

backend_pid=""
frontend_pid=""

cleanup() {
  echo
  echo "Stopping services..."
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
  wait || true
  echo "Stopped."
}
trap cleanup EXIT INT TERM

echo "Repo root: ${ROOT_DIR}"

echo
echo "== Backend =="
cd "${ROOT_DIR}"
if [[ ! -x "${ROOT_DIR}/venv/bin/python" ]]; then
  echo "ERROR: venv not found at ${ROOT_DIR}/venv"
  echo "Create it with:"
  echo "  python3 -m venv venv && source venv/bin/activate && pip install flask flask-sqlalchemy flask-login flask-bcrypt flask-cors flask-wtf openai"
  exit 1
fi

# Activate venv for flask dependencies
# shellcheck disable=SC1091
source "${ROOT_DIR}/venv/bin/activate"

echo "Starting Flask on 0.0.0.0:${BACKEND_PORT} ..."
python3 "${ROOT_DIR}/app.py" > "${ROOT_DIR}/backend.log" 2>&1 &
backend_pid="$!"
echo "Backend PID: ${backend_pid}"
echo "Backend log: ${ROOT_DIR}/backend.log"

echo
echo "== Frontend =="
cd "${ROOT_DIR}/Glosify"
if [[ ! -d node_modules ]]; then
  echo "node_modules/ not found, installing..."
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

echo "Starting Expo web on 0.0.0.0:${FRONTEND_PORT} ..."
if [[ -x "${ROOT_DIR}/Glosify/node_modules/.bin/expo" ]]; then
  "${ROOT_DIR}/Glosify/node_modules/.bin/expo" start --web --host lan --port "${FRONTEND_PORT}" > "${ROOT_DIR}/frontend.log" 2>&1 &
else
  npx expo start --web --host lan --port "${FRONTEND_PORT}" > "${ROOT_DIR}/frontend.log" 2>&1 &
fi
frontend_pid="$!"
echo "Frontend PID: ${frontend_pid}"
echo "Frontend log: ${ROOT_DIR}/frontend.log"

echo
echo "== Ready =="
echo "Backend : http://<PI_IP>:${BACKEND_PORT}"
echo "Frontend: http://<PI_IP>:${FRONTEND_PORT}"
echo
echo "Press Ctrl+C to stop both."

# Wait until one exits (then cleanup trap will run)
wait -n "${backend_pid}" "${frontend_pid}"

