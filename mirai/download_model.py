import urllib.request
import os

url = 'https://raw.githubusercontent.com/mrdoob/three.js/master/examples/models/gltf/RobotExpressive/RobotExpressive.glb'
path = 'd:/Projects/self-studio/mirai/studio/static/studio/models/RobotExpressive.glb'

print(f"Downloading {url} to {path}...")
try:
    urllib.request.urlretrieve(url, path)
    print("Download complete.")
except Exception as e:
    print(f"Error: {e}")
