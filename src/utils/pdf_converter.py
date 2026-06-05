"""
Utility to convert Markdown reports to academic-style PDFs.
Requires 'pandoc' and 'pdflatex' installed on the system.
"""
import subprocess
import shutil
import tempfile
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
import re as _re_module


def _extract_titles_from_markdown(content: str, filename_stem: str) -> tuple:
    """
    Estrae titolo, sottotitolo, titolo breve e info provider/modello dal contenuto markdown.
    
    Returns:
        (title, subtitle, short_title, provider_model)
        - title: titolo principale dal heading # (o fallback dal filename)
        - subtitle: info contestuali (grado, ecc.) dalla riga *Target Analisi:*
        - short_title: versione breve per l'header delle pagine
        - provider_model: stringa "provider / model" dalla riga *Generato con:*
    """
    # 1. Estrai titolo dal primo heading #
    title_match = _re_module.search(r'^#\s+(.+)$', content, _re_module.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # Rimuovi eventuali formattazioni markdown residue
        title = _re_module.sub(r'[*_`]', '', title)
    else:
        # Fallback: dal filename, ma preservando acronimi
        title = _clean_filename_title(filename_stem)

    # Aggiungi numero progressivo dal filename (es. _n3 → " — Report #3")
    prog_match = _re_module.search(r'_n(\d+)$', filename_stem)
    if prog_match:
        title = f"{title} — Report \\#{prog_match.group(1)}"
    
    # 2. Estrai sottotitolo dalla riga *Target Analisi: ...*
    target_match = _re_module.search(
        r'^\*Target\s+Analisi:\s*(.+?)\*', content, _re_module.MULTILINE
    )
    if target_match:
        target = target_match.group(1).strip()
        subtitle = f"Scuole Secondarie di {target}"
    else:
        # Prova a estrarre il grado dal filename
        grade_match = _re_module.search(r'(I+\s*Grado)', filename_stem, _re_module.IGNORECASE)
        if grade_match:
            subtitle = f"Scuole Secondarie di {grade_match.group(1)}"
        else:
            subtitle = "Report di Sintesi e Analisi PTOF"
    
    # 3. Short title per l'header (compatto)
    short_title = "Sintesi PTOF"
    if target_match:
        short_title = f"Sintesi PTOF — {target_match.group(1).strip()}"
    
    # 4. Estrai provider/modello dalla riga *Generato con: provider / model*
    provider_match = _re_module.search(
        r'^\*Generato\s+con:\s*(.+?)\*', content, _re_module.MULTILINE
    )
    if provider_match:
        provider_model = provider_match.group(1).strip()
    else:
        provider_model = ""
    
    return title, subtitle, short_title, provider_model


def _clean_filename_title(stem: str) -> str:
    """Converte un filename stem in un titolo leggibile, preservando acronimi."""
    # Rimuovi timestamp iniziale (es. 20260215_1050__)
    stem = _re_module.sub(r'^\d{8}_\d{4}__?', '', stem)
    # Sostituisci __ e _ con spazi
    stem = stem.replace('__', ' — ').replace('_', ' ')
    # Preserva acronimi (sequenze di 2+ maiuscole)
    words = stem.split()
    result = []
    for w in words:
        if w.isupper() and len(w) >= 2:
            result.append(w)  # Mantieni acronimi come PTOF
        elif _re_module.match(r'^I+Grado$', w):
            result.append(w.replace('Grado', ' Grado'))  # IIGrado → II Grado
        else:
            result.append(w)
    return ' '.join(result)


# Embedded professional report template
ACADEMIC_TEMPLATE = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[scaled]{helvet} 
\renewcommand\familydefault{\sfdefault} % Use Sans-Serif font by default

\usepackage{geometry}
\geometry{top=2.5cm, bottom=2.5cm, left=2cm, right=2cm}

\usepackage{hyperref}
\usepackage{graphicx}
\usepackage[export]{adjustbox}  % for max width on images
% Make pandoc-inserted images respect line width by default
\makeatletter
\def\maxwidth{\ifdim\Gin@nat@width>\linewidth\linewidth\else\Gin@nat@width\fi}
\makeatother
\setkeys{Gin}{width=\maxwidth,keepaspectratio}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage[table,xcdraw]{xcolor} % Extended color support for tables
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{calc}
\usepackage{enumitem}
\usepackage{tabularx}
\usepackage[skip=12pt plus1pt]{parskip}

% --- Colors ---
\definecolor{primaryBlue}{RGB}{0, 51, 102}
\definecolor{headerGray}{RGB}{240, 240, 240}
\definecolor{tableStrip}{RGB}{245, 245, 245}

% --- Typography & Headings ---
\titleformat{\section}
  {\color{primaryBlue}\normalfont\Large\bfseries}
  {\thesection}{1em}{}

\titleformat{\subsection}
  {\color{primaryBlue}\normalfont\large\bfseries}
  {\thesubsection}{1em}{}

\titleformat{\subsubsection}
  {\color{black}\normalfont\normalsize\bfseries}
  {\thesubsubsection}{1em}{}

% --- Table Styling ---
\renewcommand{\arraystretch}{1.3}
\setlength{\tabcolsep}{8pt}
\rowcolors{2}{tableStrip}{white} % Interleave row colors starts from 2nd row

% --- Hyperlinks ---
\hypersetup{
    colorlinks=true,
    linkcolor=primaryBlue,
    filecolor=magenta,      
    urlcolor=primaryBlue,
    pdftitle={$title$},
    pdfpagemode=FullScreen,
}

\providecommand{\tightlist}{%
  \setlength{\itemsep}{3pt}\setlength{\parskip}{0pt}}

% --- Headers & Footers ---
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\textcolor{gray}{\small $short-title$}}
\fancyhead[R]{\textcolor{gray}{\small \today}}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{gray}\leaders\hrule height \headrulewidth\hfill}}

\title{$title$}
\date{\today}

\begin{document}

\begin{titlepage}
    \centering
    \vspace*{2cm}
    
    {\color{primaryBlue}\Huge \textbf{$title$}}
    
    \vspace{1cm}
    
    {\Large\color{primaryBlue!70} $subtitle$}
    
    \vspace{2cm}
    
    \textbf{Data generazione:} \today
    
    \vspace{0.8cm}
    
    $if(provider-model)$
    \textbf{Modello AI:} $provider-model$
    $endif$
    
    \vfill
    
    {\Large \textbf{ORIENTA+}} \\
    \vspace{0.2cm}
    {\large Sistema di Analisi Avanzata per l'Orientamento}
    
    \vspace{2cm}
    
\end{titlepage}

\tableofcontents
\newpage

$body$

\end{document}
"""

def check_dependencies() -> Tuple[bool, str]:
    """
    Check if pandoc and pdflatex are available.
    Returns (success, error_message).
    """
    # Common paths to check
    search_paths = [
        "/usr/bin", 
        "/usr/local/bin", 
        "/opt/homebrew/bin", 
        str(Path.home() / ".local/bin"),
        str(Path.home() / "bin")
    ]
    
    # Add to PATH if not present
    current_path = os.environ.get("PATH", "")
    for p in search_paths:
        if p not in current_path and os.path.exists(p):
            os.environ["PATH"] += os.pathsep + p
            
    pandoc = shutil.which("pandoc")
    pdflatex = shutil.which("pdflatex")
    
    # Explicit backup check for pandoc if not found
    if not pandoc and os.path.exists("/usr/bin/pandoc"):
         pandoc = "/usr/bin/pandoc"

    if not pdflatex and os.path.exists("/usr/bin/pdflatex"):
         pdflatex = "/usr/bin/pdflatex"
    
    if pandoc is None or pdflatex is None:
        missing = []
        if pandoc is None: missing.append("pandoc")
        if pdflatex is None: missing.append("pdflatex")
        
        debug_info = f"Missing: {', '.join(missing)}. PATH={os.environ.get('PATH')}"
        return False, debug_info
        
    return True, ""

def convert_markdown_to_pdf(source_path: str, output_path: str = None) -> Tuple[Optional[str], str]:
    """
    Convert a markdown file to PDF using pandoc.
    
    Args:
        source_path: Path to source markdown file
        output_path: Path to output PDF file (optional)
        
    Returns:
        (path_to_pdf, message)
        If success, path is string and message is "Success".
        If fail, path is None and message contains error details.
    """
    success, err_msg = check_dependencies()
    if not success:
        return None, f"Dependencies missing: {err_msg}"
        
    source = Path(source_path)
    if not source.exists():
        return None, f"Source file {source_path} not found"
        
    if output_path:
        dest = Path(output_path)
    else:
        # Default: same location as source but .pdf
        dest = source.with_suffix(".pdf")
        
    import re
    
    # Read source content
    try:
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return None, f"Error reading source file: {e}"

    # Extract title/subtitle from ORIGINAL content before stripping
    title, subtitle, short_title, provider_model = _extract_titles_from_markdown(content, source.stem)

    # Strip emojis (supplementary plane characters) to avoid LaTeX errors
    content = re.sub(r'[\U00010000-\U0010ffff]', '', content)
    content = re.sub(r'[\u2700-\u27bf]', '', content) # Dingbats
    content = re.sub(r'[\u2600-\u26ff]', '', content) # Misc Symbols
    content = re.sub(r'[\ufe00-\ufe0f]', '', content) # Variation Selectors
    # Strip CJK and other non-Latin characters that pdflatex can't handle
    content = re.sub(r'[\u2E80-\u9FFF]', '', content)  # CJK Radicals, Unified Ideographs
    content = re.sub(r'[\uAC00-\uD7AF]', '', content)  # Hangul
    content = re.sub(r'[\u0600-\u06FF]', '', content)   # Arabic
    content = re.sub(r'[\u0400-\u04FF]', '', content)   # Cyrillic (keep if needed)

    # Strip the first # heading from the body (it's already on the title page)
    # Also strip metadata lines (*Target Analisi:* and *Generato con:*)
    content = re.sub(r'^#\s+.+$', '', content, count=1, flags=re.MULTILINE)
    content = re.sub(r'^\*Target\s+Analisi:[^\n]*\*\s*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\*Generato\s+con:[^\n]*\*\s*$', '', content, flags=re.MULTILINE)
    # Clean up leading blank lines
    content = content.lstrip('\n')

    # Ensure blank line before every markdown heading (## or ###)
    # Without a blank line, pandoc treats them as inline text, not headings
    content = re.sub(r'([^\n])\n(#{2,}\s)', r'\1\n\n\2', content)

    # Fix broken LaTeX commands: includegraphics without leading backslash
    content = re.sub(r'(?<![\\])includegraphics\[', r'\\includegraphics[', content)

    # Convert relative image paths to absolute paths so pdflatex can find them
    # Handles both markdown ![alt](images/...) and LaTeX \includegraphics{images/...}
    source_dir = str(source.parent.resolve())
    def _abs_img_md(m):
        alt, path = m.group(1), m.group(2)
        if not os.path.isabs(path):
            abs_path = os.path.join(source_dir, path)
            if os.path.exists(abs_path):
                path = abs_path
        return f"![{alt}]({path})"
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _abs_img_md, content)

    def _abs_img_tex(m):
        pre, path = m.group(1), m.group(2)
        if not os.path.isabs(path):
            abs_path = os.path.join(source_dir, path)
            if os.path.exists(abs_path):
                path = abs_path
        return f"{pre}{{{path}}}"
    content = re.sub(r'(\\includegraphics\[[^\]]*\])\{([^}]+)\}', _abs_img_tex, content)

    # Write to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp_md:
        tmp_md.write(content)
        tmp_source = Path(tmp_md.name)

    # Create a temporary directory for the template
    with tempfile.TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template.tex"
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(ACADEMIC_TEMPLATE)
        
        # Use absolute path for pandoc if found in standard location, otherwise just 'pandoc'
        pandoc_cmd = "pandoc"
        if os.path.exists("/usr/bin/pandoc"):
             pandoc_cmd = "/usr/bin/pandoc"
        elif shutil.which("pandoc"):
             pandoc_cmd = shutil.which("pandoc")

        # Calculate resource path: original source directory and current working directory
        resource_path = f".:{source.parent.resolve()}"
        
        cmd = [
            pandoc_cmd,
            str(tmp_source),
            "-o", str(dest),
            "--pdf-engine=pdflatex",
            f"--template={template_path}",
            f"--metadata=title:{title}",
            f"--metadata=subtitle:{subtitle}",
            f"--metadata=short-title:{short_title}",
            "--toc",
            "--toc-depth=3",
            "--shift-heading-level-by=-1",
            f"--resource-path={resource_path}"
        ]
        
        # Add provider-model metadata if available
        if provider_model:
            cmd.append(f"--metadata=provider-model:{provider_model}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True)
            # Cleanup temp markdown
            try:
                os.unlink(tmp_source)
            except:
                pass
            return str(dest), "Success"
        except subprocess.CalledProcessError as e:
            err_output = e.stderr.decode() if e.stderr else "Unknown error"
            # Cleanup temp markdown
            try:
                os.unlink(tmp_source)
            except:
                pass
            return None, f"Pandoc Error: {err_output}"
        except Exception as e:
            try:
                os.unlink(tmp_source)
            except:
                pass
            return None, f"Unexpected Error: {str(e)}"

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_converter.py <source_md_file> [output_pdf_file]")
        sys.exit(1)
        
    source = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    
    path, msg = convert_markdown_to_pdf(source, output)
    if path:
        print(f"Successfully converted to {path}")
    else:
        print(f"Failed: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
