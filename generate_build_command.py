import os

main_script = "main.py"
scripts_to_bundle = ["blender_extractor.py", "blender_fixer.py"]
assets_folder = "assets"

cmd = f'pyinstaller --noconsole --onedir --name "CameraChecker" '

# Add each blender script into the bundle root
for script in scripts_to_bundle:
    if os.path.exists(script):
        cmd += f'--add-data "{script};." '

# Add assets folder into the bundle root
if os.path.exists(assets_folder):
    cmd += f'--add-data "{assets_folder};assets" '

cmd += main_script

print("Run this command in your terminal:")
print("-" * 30)
print(cmd)