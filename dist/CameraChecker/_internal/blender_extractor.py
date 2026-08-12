import bpy 
import math
import csv
from pathlib import Path
import sys

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    # 1. Parse output directory from arguments (defaults to "output")
    output_dir = Path(argv[0] if argv else Path("output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Use a customizable filename if passed as a second argument, or default to camera_data.csv
    csv_filename = argv[1] if len(argv) > 1 else "camera_data.csv"
    output_path = output_dir / csv_filename

    scene = bpy.context.scene
    filename = Path(bpy.path.basename(bpy.data.filepath)).stem

    if scene.camera and scene.camera.type == 'CAMERA':
        camera = bpy.context.scene.camera
        camera_data = camera.data

        data = []

        for frame in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(frame)

            global_matrix = camera.matrix_world
            global_pos = global_matrix.to_translation()

            rotation_radians = global_matrix.to_euler()
            rotation_degrees = [math.degrees(angle) for angle in rotation_radians]

            focal_length = camera_data.lens

            data.append({
                "filename": filename,
                "frame": frame,
                "pos_x": global_pos.x,
                "pos_y": global_pos.y,
                "pos_z": global_pos.z,
                "rot_x": rotation_degrees[0],
                "rot_y": rotation_degrees[1],
                "rot_z": rotation_degrees[2],
                "focal": focal_length 
            })

        file_exists = output_path.is_file()

        with open(output_path, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            if not file_exists:
                writer.writeheader()
            writer.writerows(data)
            
        print(f"Successfully extracted {len(data)} frames to {output_path}")

    else:
        print("Error: No cameras found.")

if __name__ == "__main__":
    main()