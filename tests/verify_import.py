
import sys
import os
sys.path.append(os.getcwd())

try:
    from src.utils.backup_system import restore_backup, create_backup_zip, delete_backup
    print("✅ Import Successful (backup_system)")
except ImportError as e:
    print(f"❌ Import Failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
