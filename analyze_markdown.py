import re
import sys
from pathlib import Path

def analyze_markdown(file_path):
    content = Path(file_path).read_text(encoding='utf-8')
    lines = content.split('\n')
    
    issues = []
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Check 1: Unclosed bold (odd number of **)
        if line.count("**") % 2 != 0:
            issues.append(f"Line {line_num}: Odd number of '**'")

        # Check 2: Long bold sections (> 50 chars)
        long_bolds = re.findall(r'\*\*([^*]{50,})\*\*', line)
        for lb in long_bolds:
            issues.append(f"Line {line_num}: Long bold section ({len(lb)} chars): {lb[:30]}...")

        # Check 3: Acronyms/Initials issues (**C**.T.P. or **G**. De)
        # Matches **X**. where X is single letter
        if re.search(r'\*\*[A-Z]\*\*\.', line):
             issues.append(f"Line {line_num}: Potential malformed acronym/initial: {line.strip()}")

        # Check 4: Bold with internal space (** Text ** or **Text **)
        # Note: ** Text ** is essentially " Text " bolded.
        if re.search(r'\*\*\s+[^*]+\s+\*\*', line):
             issues.append(f"Line {line_num}: Bold with internal padding spaces")

        # Check 5: Empty bold
        if "**  **" in line or "****" in line:
             issues.append(f"Line {line_num}: Empty bold marker")

    if not issues:
        print("No issues found!")
    else:
        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(issue)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_markdown.py <file>")
        sys.exit(1)
    analyze_markdown(sys.argv[1])
