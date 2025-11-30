import os
import sys
import django
from django.conf import settings
from pathlib import Path

# Setup Django environment
sys.path.append('d:/Projects/self-studio/mirai')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mirai.settings')
django.setup()

from studio.utils.efficientnet_detector import ResNet50GestureDetector
import cv2
import numpy as np

def test_detector():
    print("Testing ResNet50GestureDetector...")
    
    # Path logic from services.py
    base_dir = settings.BASE_DIR
    model_path = os.path.join(base_dir.parent, 'models', 'resnet50', 'best_model.keras')
    
    print(f"Model path: {model_path}")
    
    if not os.path.exists(model_path):
        print("ERROR: Model file does not exist!")
        return

    try:
        detector = ResNet50GestureDetector(model_path=model_path)
        print("Model loaded successfully!")
        
        # Create dummy frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Test detect
        frame, detected, trigger = detector.detect(frame)
        print(f"Detection run successfully. Detected: {detected}, Trigger: {trigger}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detector()
