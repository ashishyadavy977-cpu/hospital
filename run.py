import os
import subprocess
import sys
from pathlib import Path


project_dir = Path(__file__).resolve().parent / 'hospital'
os.chdir(project_dir)
subprocess.run([sys.executable, 'run.py'])