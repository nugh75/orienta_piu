import sys
import os
sys.path.insert(0, ".")
from src.utils.backup_system import create_backup, create_backup_zip, delete_backup

def test_backup_logic():
    print("Testing Backup Logic...")
    
    # 1. Create Backup
    try:
        path, count = create_backup(description="test_auto")
        print(f"✅ Backup created: {path} ({count} files)")
        
        # 2. Zip Backup
        backup_name = os.path.basename(path)
        zip_path = create_backup_zip(backup_name)
        if zip_path and os.path.exists(zip_path):
            print(f"✅ Backup zipped: {zip_path}")
        else:
            print("❌ Zip creation failed")
            
        # Clean up
        delete_backup(backup_name)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        print("✅ Cleanup successful")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_backup_logic()
