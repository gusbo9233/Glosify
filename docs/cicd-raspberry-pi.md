# CI/CD to Raspberry Pi (GitHub → Pi) for continuous running

This guide sets up a simple pipeline:

- You **push** code from your laptop to **GitHub**
- **GitHub Actions** SSHes into your Raspberry Pi
- The Pi does `git pull` + installs deps + restarts services
- Your app runs continuously on the Pi via **systemd**

This matches the current repo structure:

- Backend: Flask (`app.py`) on port **5001**
- Frontend: Expo web dev server (`Glosify/`) on port **8081**

> Note: Running Expo web as a long-running service works for a home setup, but it’s still a “dev server”.
> If you later want a more production-like setup, build the web frontend and serve it with Nginx.

## One-time: Raspberry Pi setup

### 1) Install OS packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
```

Install Node.js 18+ (Expo works best with modern Node). Verify:

```bash
node -v
npm -v
```

### 2) Clone the repo on the Pi

Choose a stable location (example: `/opt/glosify`):

```bash
sudo mkdir -p /opt/glosify
sudo chown -R $USER:$USER /opt/glosify

git clone <YOUR_GITHUB_REPO_URL> /opt/glosify
cd /opt/glosify
```

### 3) Backend deps (venv)

```bash
cd /opt/glosify
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install flask flask-sqlalchemy flask-login flask-bcrypt flask-cors flask-wtf openai
```

### 4) Frontend deps

```bash
cd /opt/glosify/Glosify
npm ci
```

### 5) Secrets (do this on the Pi, not in git)

Backend reads:

- `SECRET_KEY` (optional, has a fallback)
- `apikey.txt` (OpenAI key file)

Create `/opt/glosify/apikey.txt` on the Pi (single line, not committed).

## Make it run continuously (systemd)

This repo includes template service files in `deploy/systemd/`.

### 1) Install the services

On the Pi:

```bash
sudo cp /opt/glosify/deploy/systemd/glosify-backend.service /etc/systemd/system/
sudo cp /opt/glosify/deploy/systemd/glosify-frontend.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable glosify-backend glosify-frontend
sudo systemctl start glosify-backend glosify-frontend
```

Check status/logs:

```bash
sudo systemctl status glosify-backend --no-pager
sudo journalctl -u glosify-backend -n 200 --no-pager

sudo systemctl status glosify-frontend --no-pager
sudo journalctl -u glosify-frontend -n 200 --no-pager
```

### 2) Access from your laptop

- Frontend: `http://<PI_IP>:8081`
- Backend: `http://<PI_IP>:5001`

## Deployment script on the Pi

This repo includes `deploy/pi_deploy.sh`. It:

- pulls latest code (`git pull --ff-only`)
- updates Python deps (best-effort)
- updates Node deps (`npm ci`)
- restarts systemd services

You can run it manually on the Pi:

```bash
cd /opt/glosify
./deploy/pi_deploy.sh
```

## CI/CD: GitHub Actions → SSH into Pi → run deploy script

This repo includes a workflow at `.github/workflows/deploy-pi.yml`.

### 1) Set GitHub Secrets

In your GitHub repo: **Settings → Secrets and variables → Actions**

Add these secrets:

- `PI_HOST`: the Pi’s LAN IP or hostname (e.g. `192.168.1.50`)
- `PI_USER`: SSH username on the Pi (e.g. `pi`)
- `PI_SSH_PRIVATE_KEY`: private key that can SSH into the Pi

### 2) Set up SSH key access on the Pi

On your laptop, generate a deploy key (example):

```bash
ssh-keygen -t ed25519 -C \"glosify-deploy\" -f ~/.ssh/glosify_pi
```

Copy the public key to the Pi:

```bash
ssh-copy-id -i ~/.ssh/glosify_pi.pub <pi-user>@<pi-ip>
```

Put the *private* key content into the GitHub secret `PI_SSH_PRIVATE_KEY`.

### 3) Allow restarting services without password (recommended)

Your deploy script restarts services via `sudo systemctl restart ...`.
To make that work non-interactively, allow passwordless restarts for that user:

```bash
sudo visudo
```

Add a line like:

```
<pi-user> ALL=NOPASSWD: /bin/systemctl restart glosify-backend, /bin/systemctl restart glosify-frontend, /bin/systemctl daemon-reload
```

### 4) How to deploy

Push to `main` from your laptop:

```bash
git push origin main
```

GitHub Actions will run the workflow and deploy to your Pi automatically.

## Important note about the database

This repo currently tracks `instance/database.db`.

- A deploy that runs `git pull` may update the DB file.
- If the Pi has local DB changes and the repo has a different DB version, `git pull` can fail with conflicts.

If you want “Pi owns the DB” (common for servers), the better pattern is:

- Keep the DB **outside** the repo on the Pi (e.g. `/var/lib/glosify/database.db`)
- Configure the backend to read the DB path from an env var
- Never overwrite it on deploy

If you want, tell me “Pi should own the DB” and I’ll adjust the app + deploy script accordingly.

