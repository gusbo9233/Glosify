# Raspberry Pi 4: pull from GitHub and run (Option A)

This guide runs:

- **Backend**: Flask on the Raspberry Pi (listens on port **5001**)
- **Frontend**: Expo **Web** dev server on the Raspberry Pi (port is printed by Expo, often **19006**)

Then you access the frontend from your laptop on the **same Wi‑Fi**.

## Prerequisites (on the Pi)

- Raspberry Pi OS **64-bit** recommended
- Python 3
- Node.js **18+** recommended (Expo works best with a modern Node)

Install base packages:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
```

Verify Node is installed:

```bash
node -v
npm -v
```

If you don’t have Node 18+, install/upgrade it (e.g. via NodeSource or `nvm`) and re-check the versions.

## 1) Clone the project from GitHub

```bash
cd ~
git clone <YOUR_GITHUB_REPO_URL> glosor-webserver
cd glosor-webserver
```

If you already cloned it earlier, update it later with:

```bash
cd ~/glosor-webserver
git pull
```

## 2) Backend: set up and run Flask on the Pi

Create a virtualenv and install Python dependencies:

```bash
cd ~/glosor-webserver
python3 -m venv venv
source venv/bin/activate

pip install flask flask-sqlalchemy flask-login flask-bcrypt flask-cors flask-wtf openai
```

Initialize the database (first run only):

```bash
python init_db.py
```

Add your OpenAI API key:

- Create a file named `apikey.txt` in the repo root containing your key (single line).

Run the server:

```bash
python app.py
```

Backend URL (from your laptop):

- `http://<PI_IP>:5001`

## 3) Frontend: run Expo Web on the Pi

Open a second terminal on the Pi (leave the backend running), then:

```bash
cd ~/glosor-webserver/Glosify
npm install
npx expo start --web --host lan
```

Expo will print a LAN URL. From your laptop, open that URL (often something like `http://<PI_IP>:19006`).

## 4) Find the Pi IP and open the app from your laptop

On the Pi:

```bash
hostname -I
```

Pick the first IP (commonly `192.168.x.y`).

On your laptop:

- Open the URL printed by Expo, e.g. `http://192.168.1.50:19006`

## How it works with the database (SQLite)

The backend uses SQLite:

- In `app.py`, the DB URI is `sqlite:///instance/database.db`
- That means the database is a **file** named `database.db` in the `instance/` folder
- When you run `python app.py` from the repo root, the DB file will be located at:
  - `~/glosor-webserver/instance/database.db`

### Does the DB persist across restarts?

Yes. As long as you don’t delete `database.db`, your data persists across restarts/reboots.

### What happens when you `git pull`?

- `git pull` updates tracked source files.
- Your `database.db` file should **not** be overwritten (it’s not expected to be committed).
- So your data stays, and you can just restart the backend + frontend.

### Should you run `init_db.py` again after pulling?

Usually:

- **No** (once the DB exists and has been pulled).
- Only run it on first setup, or if you intentionally want to reset/create a fresh database.
- If the database file doesn't exist after pulling, run `python init_db.py` to create it.

If new code requires schema changes, this repo uses separate migration scripts (see `README.md` “Run migrations” section).

### Backing up the DB

The simplest backup is to copy the file while the server is stopped:

```bash
cp ~/glosor-webserver/instance/database.db ~/database.db.backup
```

### Recommended improvement (optional)

For a “home server” setup, it’s often nicer to store the DB outside the git checkout (so you can freely delete/re-clone the repo). That requires either:

- changing `app.py` to read the DB path from an environment variable, or
- moving the repo and keeping the DB file in place.

If you want, I can update the backend to support something like `DATABASE_URL=sqlite:////home/pi/glosify-data/database.db` and document it.

## Troubleshooting

- **Firewall**: the Pi must allow inbound connections on ports **5001** and the Expo web port (often **19006**).
- **Same Wi‑Fi**: laptop + Pi must be on the same LAN.
- **Login/session issues**: frontend uses cookie-based sessions (`withCredentials: true`). If login doesn’t stick, check the browser console + Network tab and share the error.

