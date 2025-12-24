"""
PTOF Downloaders
================

Modulo per il download dei PTOF dalle anagrafiche MIUR con campionamento stratificato.
"""

from .ptof_downloader import (
    PTOFDownloader,
    PTOFValidator,
    SchoolRecord,
    DownloadState,
    load_schools_statali,
    load_schools_paritarie,
    stratify_schools,
    sample_stratified
)

__all__ = [
    'PTOFDownloader',
    'PTOFValidator', 
    'SchoolRecord',
    'DownloadState',
    'load_schools_statali',
    'load_schools_paritarie',
    'stratify_schools',
    'sample_stratified'
]
