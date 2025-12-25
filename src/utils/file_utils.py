import os
import json
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)

def atomic_write(file_path, content, mode='w', encoding='utf-8', backup=False):
    """
    Writes content to a file atomically.
    Writes to a temporary file first, then renames it to the target file.
    If backup=True, creates a backup of the existing file before overwriting.
    """
    dir_name = os.path.dirname(file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        
    if backup and os.path.exists(file_path):
        backup_path = f"{file_path}.bak"
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created at {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup for {file_path}: {e}")
        
    fd, temp_path = tempfile.mkstemp(dir=dir_name, text='b' not in mode)
    try:
        with os.fdopen(fd, mode, encoding=encoding if 'b' not in mode else None) as f:
            f.write(content)
        # Atomic rename
        os.replace(temp_path, file_path)
    except Exception as e:
        logger.error(f"Failed to write atomically to {file_path}: {e}")
        os.remove(temp_path)
        raise

def is_valid_markdown(text):
    """
    Checks if the text looks like valid Markdown and not a JSON dump.
    """
    if not isinstance(text, str):
        return False
    
    stripped = text.strip()
    if not stripped:
        return False
        
    # Check if it looks like a JSON object or array
    if (stripped.startswith('{') and stripped.endswith('}')) or \
       (stripped.startswith('[') and stripped.endswith(']')):
        try:
            json.loads(stripped)
            # If it parses as JSON, it's likely NOT what we want as Markdown content
            # unless it's a code block, but here we are checking the whole file content
            return False
        except json.JSONDecodeError:
            pass
            
    return True

def ensure_string_content(content):
    """
    Ensures the content is a string. If it's a dict or list, tries to extract narrative or dumps it.
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, dict):
        return content.get('narrative', json.dumps(content, ensure_ascii=False, indent=2))
        
    if isinstance(content, list):
        # If it's a list, it might be a list of strings or dicts
        if content and isinstance(content[0], str):
            return "\n\n".join(content)
        return json.dumps(content, ensure_ascii=False, indent=2)
        
    return str(content)
