import subprocess
import tempfile
import os
from pathlib import Path

# Assuming run from /home/nugh75/LIste
# Pick an actual image file that exists
image_file = "reports/synthesis/images/bar_finalità_dellorientamento_20260214_201718.png"

# Check if image exists
if not os.path.exists(image_file):
    print(f"Error: Image file {image_file} not found! Cannot reproduce.")
    exit(1)

content = f"![Test Image]({image_file})"

# Simulate what pdf_converter.py does: create temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp_md:
    tmp_md.write(content)
    tmp_source = Path(tmp_md.name)

print(f"Temporary MD file created at: {tmp_source}")
print(f"Current working directory: {os.getcwd()}")
print("Attempting to convert...")

cmd = [
    "pandoc",
    str(tmp_source),
    "-o", "test_output.pdf",
    "--pdf-engine=pdflatex"
]

try:
    result = subprocess.run(cmd, check=True, capture_output=True)
    print("Conversion successful (technically). Check if PDF has image.")
except subprocess.CalledProcessError as e:
    print(f"Pandoc Error: {e.stderr.decode()}")

# Clean up
os.unlink(tmp_source)
