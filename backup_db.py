import os
import shutil
from datetime import datetime

# SECURITY IMPLEMENTATION: Data Recovery & Automated Backup
# Ensures high availability and operational continuity by isolating the core database 
# into timestamped snapshots, protecting against ransomware, data corruption, or catastrophic failure.

DB_FILE = 'instance/vetsync.db'
BACKUP_DIR = 'backups'

def perform_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    if not os.path.exists(DB_FILE):
        print(f"Error: Database file {DB_FILE} not found.")
        return

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f"vetsync_backup_{timestamp}.db")
    
    try:
        shutil.copy2(DB_FILE, backup_file)
        print(f"Backup successfully created at: {backup_file}")
    except Exception as e:
        print(f"Backup failed: {e}")

if __name__ == "__main__":
    perform_backup()
