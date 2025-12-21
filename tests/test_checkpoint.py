import sys
import os
import json
import glob
import shutil

# Mock config
CHECKPOINT_DIR = 'data/pending_analyses_test'
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# Define functions to test (copied from implementation to isolate from Streamlit)
def save_checkpoint(pending_data):
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"{pending_data['school_id']}_pending.json")
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(pending_data, f, ensure_ascii=False, indent=2)
    return checkpoint_path

def load_checkpoints():
    checkpoints = []
    for f in glob.glob(os.path.join(CHECKPOINT_DIR, '*_pending.json')):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                data['checkpoint_file'] = f
                checkpoints.append(data)
        except Exception as e:
            pass
    return checkpoints

def clear_checkpoint(school_id):
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"{school_id}_pending.json")
    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)

def clear_all_checkpoints():
    for f in glob.glob(os.path.join(CHECKPOINT_DIR, '*_pending.json')):
        try:
            os.remove(f)
        except:
            pass

# --- TESTS ---
print("Running Checkpoint Tests...")

# 1. Test Save
data1 = {'school_id': 'TEST001', 'result': {'score': 5}, 'filename': 'test1.pdf'}
save_checkpoint(data1)
assert os.path.exists(os.path.join(CHECKPOINT_DIR, 'TEST001_pending.json'))
print("✅ Save Checkpoint: PASS")

# 2. Test Load
loaded = load_checkpoints()
assert len(loaded) == 1
assert loaded[0]['school_id'] == 'TEST001'
print("✅ Load Checkpoints: PASS")

# 3. Test Save Second
data2 = {'school_id': 'TEST002', 'result': {'score': 3}, 'filename': 'test2.pdf'}
save_checkpoint(data2)
loaded = load_checkpoints()
assert len(loaded) == 2
print("✅ Multiple Checkpoints: PASS")

# 4. Test Clear Single
clear_checkpoint('TEST001')
assert not os.path.exists(os.path.join(CHECKPOINT_DIR, 'TEST001_pending.json'))
assert os.path.exists(os.path.join(CHECKPOINT_DIR, 'TEST002_pending.json'))
print("✅ Clear Single Checkpoint: PASS")

# 5. Test Clear All
clear_all_checkpoints()
assert len(glob.glob(os.path.join(CHECKPOINT_DIR, '*_pending.json'))) == 0
print("✅ Clear All Checkpoints: PASS")

# Cleanup
if os.path.exists(CHECKPOINT_DIR):
    shutil.rmtree(CHECKPOINT_DIR)
print("\n🎉 ALL TESTS PASSED!")
