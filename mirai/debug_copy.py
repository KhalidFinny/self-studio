import shutil
import os
import sys

src = os.path.abspath(r'3d\Rbolox avatar.obj')
dst = os.path.abspath(r'studio\static\studio\models\Roblox_avatar.obj')

print(f"Source: {src}")
print(f"Dest: {dst}")

if not os.path.exists(src):
    print("Source does not exist!")
    # Try listing the dir
    print(f"Listing {os.path.dirname(src)}:")
    print(os.listdir(os.path.dirname(src)))
    sys.exit(1)

dst_dir = os.path.dirname(dst)
if not os.path.exists(dst_dir):
    print(f"Creating dir: {dst_dir}")
    os.makedirs(dst_dir)

try:
    shutil.copy2(src, dst)
    print("Copy successful")
    print(f"Size: {os.path.getsize(dst)}")
except Exception as e:
    print(f"Error: {e}")
