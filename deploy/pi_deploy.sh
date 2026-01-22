#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/glosify"

echo "Deploying in: ${REPO_DIR}"
cd "${REPO_DIR}"

echo
echo "== Git update =="
git fetch origin
git checkout main
git pull --ff-only

echo
echo "== Backend deps (best-effort) =="
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
  python -m pip install --upgrade pip
  # If you add a requirements.txt later, prefer it:
  if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    pip install flask flask-sqlalchemy flask-login flask-bcrypt flask-cors flask-wtf openai
  fi
else
  echo "WARNING: venv/ not found. Skipping pip install."
fi

echo
echo "== Frontend deps =="
if [ -d "Glosify" ]; then
  cd "Glosify"
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
else
  echo "WARNING: Glosify/ not found. Skipping npm."
fi

echo
echo "== Restart services =="
sudo systemctl daemon-reload
sudo systemctl restart glosify-backend
sudo systemctl restart glosify-frontend

echo
echo "== Status =="
sudo systemctl --no-pager --full status glosify-backend || true
sudo systemctl --no-pager --full status glosify-frontend || true

echo
echo "Deploy complete."

