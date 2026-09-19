# Bugless Fit: Safe Local Handoff and Setup

This guide explains how to transfer and run Bugless Fit safely on a Windows
development computer. It creates a fresh local SQLite database and does not
reuse the sender's accounts, orders, contact messages, secrets, or runtime
files.

The project is a local learning application. Django's development server is
not a production server and must not be exposed to the internet.

## Part A: Sender handoff checklist

### 1. Confirm that the intended source is committed

From the repository root, run:

```powershell
git status --porcelain
```

Check:

- [ ] The command prints nothing.
- [ ] If it prints file names, review and commit only the intended source
  changes before continuing.

### 2. Confirm that private local files are not tracked

Run:

```powershell
git ls-files -- .env db.sqlite3 db.pre-custom-user.20260913.sqlite3
```

Check:

- [ ] The command prints nothing.
- [ ] Do not send `.env`, any `*.sqlite3` file, `media/`, `.venv/`,
  `node_modules/`, `staticfiles/`, `.phase6/`, test results, logs, or the
  `.git/` directory.

Database files must be treated as private even when they are believed to
contain only demonstration data.

### 3. Create a source-only ZIP archive

`git archive` includes files from the committed revision and leaves ignored
local data out of the archive:

```powershell
$handoffArchive = Join-Path ([System.IO.Path]::GetTempPath()) "bugless-fit-source.zip"
git archive --format=zip --output $handoffArchive HEAD
Get-Item -LiteralPath $handoffArchive
```

Check:

- [ ] `bugless-fit-source.zip` exists at the printed location.
- [ ] The archive was made only after the intended source was committed.

### 4. Create an integrity hash

Run:

```powershell
Get-FileHash -LiteralPath $handoffArchive -Algorithm SHA256
```

Check:

- [ ] Save the complete SHA-256 value.
- [ ] Send the ZIP privately.
- [ ] Send the expected SHA-256 value through a separate trusted message when
  practical.

## Part B: Recipient setup checklist

All commands below must be run from Windows PowerShell. Python 3.13 is
recommended because it matches the currently verified development
environment. On macOS or Linux, use `python3`, `.venv/bin/python`, and the
equivalent shell environment syntax.

### 1. Verify the received archive before extracting it

Run this in the directory containing the downloaded ZIP:

```powershell
Get-FileHash -LiteralPath .\bugless-fit-source.zip -Algorithm SHA256
```

Check:

- [ ] The displayed hash exactly matches the value supplied by the sender.
- [ ] Stop and ask the sender for a new copy if it does not match.

Extract the archive into a new empty folder, then open PowerShell in that
folder. Confirm that it is the project root:

```powershell
Get-ChildItem manage.py, requirements.txt, package.json
```

Check:

- [ ] All three files are listed.
- [ ] There is no received `.env` or `*.sqlite3` file.

### 2. Check Python

Run:

```powershell
py -3.13 --version
```

Check:

- [ ] A Python 3.13 version is displayed.
- [ ] If the launcher cannot find Python 3.13, install it from the official
  Python distribution before continuing.

### 3. Create an isolated virtual environment

Run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
```

Check:

- [ ] `.venv` was created inside the project folder.
- [ ] The second command displays the expected Python version.
- [ ] Do not copy or share this virtual environment between computers.

Activation is not required by this guide because every Python command uses the
virtual environment's interpreter explicitly.

### 4. Install Python dependencies

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Check:

- [ ] Installation finishes without an error.
- [ ] `pip check` reports `No broken requirements found`.

Only install dependencies from the repository's `requirements.txt`. Do not
copy another computer's global Python packages or virtual environment.

### 5. Select safe local settings

Use SQLite for the first local run. Run these commands in the same PowerShell
window that will run Django:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:SQLITE_DATABASE_PATH -ErrorAction SilentlyContinue
$env:DEBUG = "True"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:SECRET_KEY = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))")
```

Check:

- [ ] `DATABASE_URL` is unset, so Django will use local SQLite.
- [ ] `DEBUG` is enabled only for local development.
- [ ] `ALLOWED_HOSTS` contains only the local host names.
- [ ] The secret exists only in the current PowerShell process.

The repository does not automatically load `.env` files. `.env.example` is a
reference, not a file that should be copied unchanged. If a new PowerShell
window is opened, repeat this settings step before starting Django.

### 6. Create the fresh local database

Run:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py showmigrations accounts store
```

Check:

- [ ] Migration completes without an error.
- [ ] Every listed `accounts` and `store` migration has `[X]` beside it.
- [ ] A new ignored `db.sqlite3` file now exists locally.

### 7. Load the demonstration catalog and staff roles

Run:

```powershell
.\.venv\Scripts\python.exe manage.py seed_catalog
.\.venv\Scripts\python.exe manage.py configure_staff_roles
```

Check:

- [ ] Catalog seeding completes without an error.
- [ ] The four staff groups are configured without an error.
- [ ] Do not use `--with-demo-promotions` unless demonstration promotion codes
  are intentionally wanted.

The seeded catalog is demonstration data. Product images and some presentation
resources are remote, so the complete visual presentation requires an internet
connection.

### 8. Run the required project checks

Run each command separately:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Check:

- [ ] Django reports no system-check issues.

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations --check
```

Check:

- [ ] Django reports `No changes detected`.

```powershell
.\.venv\Scripts\python.exe manage.py test -v 1
```

Check:

- [ ] The test suite finishes with `OK`.
- [ ] Four PostgreSQL-only concurrency tests being skipped while using SQLite
  is expected.

### 9. Create a local administrator if needed

Run:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Check:

- [ ] Use an email address and a unique development password.
- [ ] Do not reuse a real production password.
- [ ] Do not place the password in source files, screenshots, or messages.

This step is optional if only the public storefront is being reviewed.

### 10. Start Django on the loopback interface

Run:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Check:

- [ ] The terminal reports that the development server is running.
- [ ] It is bound to `127.0.0.1`, not `0.0.0.0`.
- [ ] If Windows Firewall asks about public-network access, do not grant public
  access.

Open these local addresses:

- Store: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>
- Health check: <http://127.0.0.1:8000/health/>

From a second PowerShell window, verify the health response:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ | ConvertTo-Json -Compress
```

Check:

- [ ] The response is `{"ok":true,"database":"ok"}`.

Press `Ctrl+C` in the server terminal when finished.

## Optional browser end-to-end checks

Node.js is not required to run the store. It is required only for the optional
Playwright browser suite. The suite uses its own isolated local database.

Check Node.js and npm:

```powershell
node --version
npm --version
```

Then activate the Python virtual environment so Playwright's server command
finds the correct `python` executable:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
npm ci
npx playwright install chromium
npm run test:e2e
```

Check:

- [ ] `python --version` points to the virtual environment's Python.
- [ ] `npm ci` uses the committed lock file and finishes successfully.
- [ ] Chromium installation finishes successfully.
- [ ] Ten desktop/mobile browser runs pass.

## Local safety rules

- [ ] Use fake customer, order, address, and contact data while learning.
- [ ] Never expose Django's development server to a LAN or the internet.
- [ ] Never commit `.env`, SQLite databases, uploaded media, passwords, or
  tokens.
- [ ] Do not turn on real contact email delivery for a local demonstration.
- [ ] Password-reset messages use the console locally; links appear in the
  server terminal rather than being emailed.
- [ ] Back up the local `db.sqlite3` before experiments that intentionally
  change catalog, inventory, or order data.
- [ ] Use a real deployment design, production database, secret manager,
  HTTPS, backups, and production server before considering any public launch.

## Common problems

### Django tries to connect to PostgreSQL

`DATABASE_URL` is probably defined in the shell or IDE. Clear it and rerun the
command:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
```

### Python cannot import Django

Use the virtual environment interpreter explicitly:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
```

### Port 8000 is already in use

Use another loopback-only port:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

### Remote images, fonts, or the map do not appear

The authored storefront uses remote presentation resources. Confirm the
computer has internet access. Catalog, accounts, checkout, and local database
behavior remain Django-controlled.
