# Deployment Guide

## Step-by-Step PostgreSQL Setup and VM Deployment

---

## Part 1: PostgreSQL Database Setup

### Step 1: Connect to PostgreSQL

Connect to PostgreSQL using the following command in terminal:

```bash
psql -h 34.139.8.30 -U yl5961 -d proj1part2
```

**Password:** `115674`

Upon successful connection, you will see the following prompt:
```
proj1part2=>
```

### Step 2: Run Migrations (Add 3 Advanced Features)

While connected, run the migration using:

```sql
\i migrations.sql
```

Or run directly from terminal:

```bash
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f migrations.sql
```

**What this step creates:**
- ✅ `suspect_clue` table
- ✅ `suspect.weapons` column
- ✅ GIN indexes
- ✅ FTS triggers

### Step 3: Populate Data

```bash
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f populate_data.sql
```

Or within psql:

```sql
\i populate_data.sql
```

**What this step does:**
- ✅ Adds weapons arrays to at least 20 suspects
- ✅ Inserts at least 12 suspect_clue records
- ✅ Sets all remaining suspects as unarmed (empty array)

### Step 4: Verification

Verify that data was inserted correctly:

```sql
-- Check suspect_clue table
SELECT COUNT(*) FROM suspect_clue;
-- Expected result: >= 10

-- Check weapons column
SELECT COUNT(*) FROM suspect WHERE weapons IS NOT NULL;
-- Expected result: Should equal total number of suspect records

-- Check including empty arrays
SELECT COUNT(*) FROM suspect WHERE weapons IS NOT NULL OR weapons = ARRAY[]::TEXT[];
-- Expected result: Should equal total number of suspect records

-- Check triggers
SELECT trigger_name FROM information_schema.triggers 
WHERE trigger_name LIKE '%suspect_clue%';
-- Expected result: trigger_suspect_clue_insert_tsv, trigger_suspect_clue_update_tsv

-- Sample data check
SELECT suspect_id, incident_id, weapons FROM suspect LIMIT 5;
SELECT clue_id, incident_id, suspect_id, LEFT(clue_text, 50) FROM suspect_clue LIMIT 5;
```

### Step 5: Query Testing (Optional)

```bash
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f queries.sql
```

Or within psql:

```sql
\i queries.sql
```

---

## Part 2: Deploy Flask App on VM

### Step 1: Connect to VM

```bash
# SSH to VM (use VM's IP address)
ssh your_username@your_vm_ip
```

Or proceed to the next step if already connected to VM.

### Step 2: Upload Project Files

**Option A: Using Git (Recommended)**
```bash
# On VM
cd ~
git clone your_repository_url
cd nyc-crimedata
```

**Option B: Using SCP**
```bash
# From local machine
scp -r /Users/yubinsallygo/PycharmProjects/nyc-crimedata your_username@your_vm_ip:~/
```

**Option C: Direct File Copy**
- Use SFTP clients like FileZilla, WinSCP
- Or upload files via VM's web interface

### Step 3: Set Up Virtual Environment

On VM:

```bash
cd ~/nyc-crimedata  # or your project directory

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Verify Environment Variables

Verify database connection information in `server.py`:

```python
DATABASE_USERNAME = "yl5961"
DATABASE_PASSWRD = "115674"
DATABASE_HOST = "34.139.8.30"
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"
```

### Step 5: Run Flask App

**Development Mode (for testing):**
```bash
# With virtual environment activated
python server.py
```

**Production Mode (background execution):**

```bash
# Run in background with nohup
nohup python server.py --host 0.0.0.0 --port 8111 > app.log 2>&1 &

# Or use screen
screen -S flask_app
python server.py
# Press Ctrl+A, D to detach
```

**Run as systemd Service (Recommended):**

Create `/etc/systemd/system/flask-app.service`:

```ini
[Unit]
Description=NYC Crime Data Flask App
After=network.target

[Service]
User=your_username
WorkingDirectory=/home/your_username/nyc-crimedata
Environment="PATH=/home/your_username/nyc-crimedata/venv/bin"
ExecStart=/home/your_username/nyc-crimedata/venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl start flask-app
sudo systemctl enable flask-app  # Auto-start on boot
sudo systemctl status flask-app  # Check status
```

### Step 6: Configure Firewall

```bash
# Open port 8111
sudo ufw allow 8111/tcp
# Or
sudo iptables -A INPUT -p tcp --dport 8111 -j ACCEPT
```

### Step 7: Verify Access

Access from browser:
```
http://your_vm_ip:8111
```

Or if you have external IP:
```
http://34.148.79.232:8111
```

---

## Part 3: Troubleshooting

### Database Connection Error

```bash
# Test connection
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -c "SELECT 1;"
```

### Flask App Won't Start

```bash
# Check logs
tail -f app.log
# Or
journalctl -u flask-app -f
```

### Port Already in Use

```bash
# Check port usage
sudo lsof -i :8111
# Or
sudo netstat -tulpn | grep 8111

# Kill process
kill -9 <PID>
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Quick Reference Commands

### PostgreSQL

```bash
# Connect
psql -h 34.139.8.30 -U yl5961 -d proj1part2

# Run migrations
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f migrations.sql

# Populate data
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f populate_data.sql

# Test queries
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f queries.sql
```

### Flask App

```bash
# Activate virtual environment
source venv/bin/activate

# Run app
python server.py

# Run in background
nohup python server.py > app.log 2>&1 &
```

---

## Checklist

Pre-deployment checklist:

- [ ] Successfully connected to PostgreSQL
- [ ] `migrations.sql` executed successfully (no errors)
- [ ] `populate_data.sql` executed successfully (no errors)
- [ ] Data verification complete (suspect_clue >= 10, all suspects have weapons values)
- [ ] Files uploaded to VM
- [ ] Virtual environment set up
- [ ] Dependencies installed
- [ ] Flask app runs successfully
- [ ] Web browser access verified
- [ ] Tested suspect_clue add/edit in admin page
- [ ] Tested weapons array editing

---

## Additional Notes

- **VM IP Address:** `34.148.79.232:8111` (as specified in README.md)
- **Database Host:** `34.139.8.30`
- **Database:** `proj1part2`
- **User:** `yl5961`
- **Port:** `8111`

If issues occur, check logs or refer to the troubleshooting section above.
