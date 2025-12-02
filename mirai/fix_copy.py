import os
import shutil

# Define paths
base_dir = r"d:\Projects\self-studio\mirai"
src_dir = os.path.join(base_dir, "3d")
dst_dir = os.path.join(base_dir, "studio", "static", "studio", "models")
src_file = os.path.join(src_dir, "Rbolox avatar.obj")
dst_file = os.path.join(dst_dir, "avatar.obj")

print(f"Checking source: {src_file}")
if os.path.exists(src_file):
    print("Source exists!")
else:
    print("Source NOT found!")
    print(f"Listing {src_dir}:")
    try:
        print(os.listdir(src_dir))
    except Exception as e:
        print(f"Error listing dir: {e}")

print(f"Checking destination dir: {dst_dir}")
if not os.path.exists(dst_dir):
    print("Creating destination directory...")
    os.makedirs(dst_dir, exist_ok=True)

print(f"Copying to {dst_file}...")
try:
    shutil.copy2(src_file, dst_file)
    print("Copy successful!")
except Exception as e:
    print(f"Copy failed: {e}")
