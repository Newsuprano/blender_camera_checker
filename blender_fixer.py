import bpy
import os
import sys
import argparse

def main(reference_blend_path, set_active=False):
    if not os.path.exists(reference_blend_path):
        print(f"Error: Reference file not found: {reference_blend_path}")
        return

    ref_camera_name = None

    # 1. Safely extract the active camera name from the reference file
    with bpy.data.libraries.load(reference_blend_path, link=True) as (data_from, data_to):
        if data_from.scenes:
            data_to.scenes = data_from.scenes[:1]

    # Check the loaded scene's active camera pointer
    if bpy.data.scenes:
        ref_scene = bpy.data.scenes[-1]
        if ref_scene.camera:
            ref_camera_name = ref_scene.camera.name

    # Fallback: if no active camera is set on the reference scene, grab the first camera object found in the file
    if not ref_camera_name:
        with bpy.data.libraries.load(reference_blend_path, link=True) as (data_from, data_to):
            cameras = [obj for obj in data_from.objects if obj]
            if cameras:
                ref_camera_name = cameras[0]

    if not ref_camera_name:
        print(f"Error: Could not find any valid camera in reference file: {reference_blend_path}")
        return

    print(f"Successfully targeted reference camera: {ref_camera_name}")
    new_name = f"fixed from {os.path.basename(reference_blend_path)}"

    scene = bpy.context.scene

    # 2. Cleanup any prior "fixed from" cameras to keep it clean
    for obj in list(scene.collection.objects):
        if obj.name.startswith("fixed from "):
            cam_data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if cam_data and cam_data.users == 0:
                bpy.data.cameras.remove(cam_data)

    # 3. Append the actual camera object (link=False creates a local copy with animation)
    with bpy.data.libraries.load(reference_blend_path, link=False) as (data_from, data_to):
        data_to.objects = [ref_camera_name]

    imported_cam = None
    for obj in data_to.objects:
        if obj:
            if obj.name not in scene.collection.objects:
                scene.collection.objects.link(obj)
            imported_cam = obj
            break

    if imported_cam:
        imported_cam.name = new_name
        if imported_cam.data:
            imported_cam.data.name = new_name
        
        if set_active:
            scene.camera = imported_cam
            print(f"Set '{new_name}' as active scene camera.")

        # Force save the target blend file
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        print(f"Successfully applied and saved camera to target file: {new_name}")
    else:
        print("Error: Failed to link the imported reference camera into the target scene.")

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref-file", required=True)
    parser.add_argument("--set-active", action="store_true")
    args = parser.parse_known_args(argv)[0]
    main(args.ref_file, set_active=args.set_active)