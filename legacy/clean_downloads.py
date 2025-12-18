import os

def clean_small_files(directory, min_size=20000): # 20KB
    if not os.path.exists(directory):
        return
        
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            if size < min_size:
                print(f"Removing {f} (Size: {size} bytes) - Likely invalid.")
                os.remove(path)

if __name__ == "__main__":
    clean_small_files("scuola_in_chiaro")
