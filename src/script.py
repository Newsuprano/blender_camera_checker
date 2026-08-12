import argparse
import subprocess
from pathlib import Path
from assets import get_ressource_path


def run_batch_extraction(input_dir, output_dir, blender_exe, progress_callback=None, csv_filename="camera_data.csv"):
    input_folder_path = Path(input_dir)
    output_folder_path = Path(output_dir)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    raw_data_csv = output_folder_path / csv_filename
    if raw_data_csv.exists():
        raw_data_csv.unlink()

    extractor_path = Path(get_ressource_path("blender_extractor.py"))
    
    blend_files = list(input_folder_path.glob('*.blend'))
    total_files = len(blend_files)

    for index, file_path in enumerate(blend_files, start=1):
        if progress_callback:
            progress_callback(index, total_files, f"Extracting from {file_path.name} ({index}/{total_files})")
            
        # Pass BOTH the output folder AND the custom csv_filename to blender_extractor.py
        cmd = f'"{blender_exe}" --background "{file_path}" --python "{extractor_path}" -- "{output_folder_path}" "{csv_filename}"'
        subprocess.run(cmd, shell=True)

def run_batch_fixer(input_dir, output_dir, reference_filename, blender_exe, progress_callback=None, set_active=False, csv_path=None):
    input_folder_path = Path(input_dir)
    fixer_path = Path(get_ressource_path("blender_fixer.py"))
    
    # Use the explicitly provided csv_path, or fall back safely to camera_data.csv in output_dir
    target_csv = Path(csv_path) if csv_path else Path(output_dir) / "camera_data.csv"
    
    if not target_csv.exists():
        print(f"Error: Target CSV file not found at {target_csv}. Please run extraction first.")
        return

    blend_files = list(input_folder_path.glob('*.blend'))
    total_files = len(blend_files)

    for index, file_path in enumerate(blend_files, start=1):
        if file_path.name == reference_filename:
            print(f"Skipping reference file: {file_path.name}")
            continue

        if progress_callback:
            progress_callback(index, total_files, f"Fixing cameras in {file_path.name} ({index}/{total_files})")
            
        cmd = [
            blender_exe,
            str(file_path),
            "--background",
            "--python", str(fixer_path),
            "--",
            "--csv", str(target_csv),
            "--ref", reference_filename
        ]
        
        if set_active:
            cmd.append("--set-active")
        
        subprocess.run(cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Blender camera pipeline tools.")
    parser.add_argument("--mode", choices=["extract", "fix"], default="extract", help="Operation mode")
    parser.add_argument("--input", required=True, help="Path to input folder containing .blend files")
    parser.add_argument("--output", help="Path to output folder for CSV reports (required for extract and fix)")
    parser.add_argument("--reference", help="Reference filename selected from dropdown (required for fix)")
    parser.add_argument("--set-active", action="store_true", help="Set the fixed camera as the active camera")
    parser.add_argument("--blender", default=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe', help="Path to blender.exe")
    
    args = parser.parse_args()
    
    if args.mode == "extract":
        if not args.output:
            parser.error("--output is required for extraction mode.")
        run_batch_extraction(args.input, args.output, args.blender)
    elif args.mode == "fix":
        if not args.output:
            parser.error("--output is required to locate camera_data.csv for fix mode.")
        if not args.reference:
            parser.error("--reference filename is required for fix mode.")
        run_batch_fixer(args.input, args.output, args.reference, args.blender, set_active=args.set_active)