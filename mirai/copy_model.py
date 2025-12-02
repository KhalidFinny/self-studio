import shutil
import os

src = r'3d\Rbolox avatar.obj'
dst = r'studio\static\studio\models\Roblox_avatar.obj'

print(f"Copying {src} to {dst}")
try:
    shutil.copy(src, dst)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
