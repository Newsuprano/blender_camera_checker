import argparse
import subprocess
from pathlib import Path

def run_batch_extraction(input_dir, output_dir, blender_exe) :
    input_folder_path = Path(input_dir)
    output_folder_path = Path(output_dir)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    raw_data_csv = output_folder_path / "camera_data.csv"
    if raw_data_csv.exists() :
        raw_data_csv.unlink()

    extractor_path = Path(__file__).parent / "blender_extractor.py"

    for file_path in input_folder_path.glob('*.blend') :
        subprocess.run(f'"{blender_exe}" --background "{file_path}" --python "{extractor_path}" -- "{output_folder_path}"', shell=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Blender camera extraction pipeline.")
    parser.add_argument("--input", required=True, help="Path to input folder containing .blend files")
    parser.add_argument("--output", required=True, help="Path to output folder for CSV reports")
    parser.add_argument("--blender", default=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe', help="Path to blender.exe")
    
    args = parser.parse_args()
    run_batch_extraction(args.input, args.output, args.blender)