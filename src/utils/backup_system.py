import os
import shutil
import glob
from datetime import datetime

BACKUP_ROOT = "backups"
DATA_FILES = ["data/analysis_summary.csv"]
RESULTS_DIR = "analysis_results"

def create_backup(description="manual"):
    """
    Creates a timestamped backup of critical data (CSVs and JSONs).
    Returns the path to the backup folder.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}_{description}"
    backup_path = os.path.join(BACKUP_ROOT, backup_name)
    
    # Create backup structure
    os.makedirs(backup_path, exist_ok=True)
    os.makedirs(os.path.join(backup_path, "data"), exist_ok=True)
    os.makedirs(os.path.join(backup_path, "analysis_results"), exist_ok=True)
    
    # Backup Data Files (CSV)
    files_backed_up = 0
    for f in DATA_FILES:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(backup_path, "data"))
            files_backed_up += 1
            
    # Backup JSON Analysis Results
    json_files = glob.glob(os.path.join(RESULTS_DIR, "*.json"))
    for f in json_files:
        shutil.copy2(f, os.path.join(backup_path, "analysis_results"))
        files_backed_up += 1
        
    return backup_path, files_backed_up

def list_backups():
    """Returns list of existing backups sorted by date desc."""
    if not os.path.exists(BACKUP_ROOT):
        return []
    dirs = [d for d in os.listdir(BACKUP_ROOT) if os.path.isdir(os.path.join(BACKUP_ROOT, d))]
    return sorted(dirs, reverse=True)

def create_backup_zip(backup_name):
    """
    Zips a specific backup folder for download.
    Returns the path to the zip file.
    """
    backup_path = os.path.join(BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_path):
        return None
        
    zip_path = shutil.make_archive(backup_path, 'zip', backup_path)
    return zip_path

def restore_from_zip(zip_file_obj):
    """
    Restores a backup from an uploaded zip file.
    Extracts to a new backup folder in BACKUP_ROOT.
    Returns the name of the new backup folder.
    """
    try:
        # Create a temp name for the imported backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"imported_{timestamp}"
        backup_path = os.path.join(BACKUP_ROOT, backup_name)
        
        # Save zip temporarily
        temp_zip = f"{backup_path}.zip"
        with open(temp_zip, "wb") as f:
            f.write(zip_file_obj.read())
            
        # Extract
        shutil.unpack_archive(temp_zip, backup_path)
        
        # Clean up zip
        os.remove(temp_zip)
        
        return backup_name
    except Exception as e:
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path) # Cleanup partial
        raise e

def delete_backup(backup_name):
    """Safely deletes a backup folder."""
    backup_path = os.path.join(BACKUP_ROOT, backup_name)
    if os.path.exists(backup_path):
        shutil.rmtree(backup_path)
        return True
    return False

def restore_backup(backup_name):
    """
    Restores data from a specific backup folder.
    WARNING: Overwrites current data!
    Returns dictionary with status and details.
    """
    backup_path = os.path.join(BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_path):
        return {"success": False, "error": "Backup not found"}
        
    try:
        restored_count = 0
        
        # 1. Restore Data Files (CSV)
        backup_data_dir = os.path.join(backup_path, "data")
        if os.path.exists(backup_data_dir):
            for f in os.listdir(backup_data_dir):
                src = os.path.join(backup_data_dir, f)
                dst = os.path.join("data", f)
                shutil.copy2(src, dst)
                restored_count += 1
                
        # 2. Restore JSON Analysis Results
        backup_results_dir = os.path.join(backup_path, "analysis_results")
        if os.path.exists(backup_results_dir):
            for f in os.listdir(backup_results_dir):
                if f.endswith(".json"):
                    src = os.path.join(backup_results_dir, f)
                    dst = os.path.join(RESULTS_DIR, f)
                    shutil.copy2(src, dst)
                    restored_count += 1
                    
        return {"success": True, "files_restored": restored_count, "path": backup_path}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
