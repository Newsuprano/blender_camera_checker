import sys
from pathlib import Path
import subprocess

input_folder_path = Path(r'D:\Desktop\blender-cam\camera_checker\test_files')
extractor_path = r'D:\Desktop\blender-cam\camera_checker\blender_extractor.py'
blender_exe = r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'

for file_path in input_folder_path.glob('*.blend') :
    file_path = str(file_path)
    subprocess.run(f'"{blender_exe}" --background "{file_path}" --python "{extractor_path}"', shell=True)