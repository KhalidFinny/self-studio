import threading
import time
import cv2
import os
from django.conf import settings
from .utils.camera import Camera
# Use YOLO detector since we have the model
from .utils.detection import GestureDetector 
# from .utils.efficientnet_detector import ResNet50GestureDetector

class CameraService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CameraService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.camera = Camera(camera_id=0, width=1280, height=720)
        
        # Initialize detector
        # Path to model
        model_path = os.path.join(settings.BASE_DIR, 'studio', 'models', 'yolov8n.pt')
        try:
            self.detector = GestureDetector(model_path=model_path, confidence=0.85)
            print(f"[SUCCESS] YOLO model loaded from {model_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load YOLO model: {e}")
            self.detector = None

        self.imaging_edge = None # Not implemented yet
        self.countdown_seconds = 3
        
        self.frame = None
        self.frame_lock = threading.Lock()
        self.is_running = True
        
        # Shared state
        self.state = {
            "countdown": None,
            "message": "",
            "flash": False
        }
        
        # Start camera thread
        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()
        
        self._initialized = True

    def _camera_loop(self):
        print("[INFO] Camera loop started")
        if not self.camera.open():
            print("[FAIL] Camera not accessible.")
            return

        while self.is_running:
            ret, frame = self.camera.read()
            if not ret:
                time.sleep(0.1)
                continue
                
            # Flip horizontally
            frame = cv2.flip(frame, 1)
            
            # Detect
            if self.detector:
                try:
                    frame, detected_gesture, should_trigger = self.detector.detect(frame)
                    
                    if should_trigger and self.state["countdown"] is None:
                        print("[INFO] Triggering countdown")
                        threading.Thread(target=self.start_countdown, daemon=True).start()
                except Exception as e:
                    print(f"[ERROR] Detection failed: {e}")
            
            with self.frame_lock:
                self.frame = frame
            
            time.sleep(0.01)

    def get_frame(self):
        with self.frame_lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def generate_frames(self):
        while self.is_running:
            frame = self.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03)

    def start_countdown(self):
        if self.detector:
            self.detector.set_trigger_active(True)
        
        self.state["message"] = "Get Ready..."
        
        for i in range(self.countdown_seconds, 0, -1):
            self.state["countdown"] = i
            self.state["message"] = str(i)
            time.sleep(1)
        
        self.state["countdown"] = 0
        self.state["message"] = "SMILE!"
        
        # Capture
        self._capture()
        
        time.sleep(2)
        self.state["countdown"] = None
        self.state["message"] = ""
        if self.detector:
            self.detector.set_trigger_active(False)

    def _capture(self):
        # Local capture
        try:
            save_dir = os.path.join(settings.BASE_DIR, "captures")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            filepath = os.path.join(save_dir, filename)
            
            frame = self.get_frame()
            if frame is not None:
                cv2.imwrite(filepath, frame)
                print(f"[SUCCESS] Saved locally to {filepath}")
                self.state["flash"] = True
                self.state["message"] = "Saved Locally!"
                
                def reset_flash():
                    self.state["flash"] = False
                    
                threading.Timer(0.5, reset_flash).start()
            else:
                print("[ERROR] No frame to save")
                self.state["message"] = "Capture Failed!"
        except Exception as e:
            print(f"[ERROR] Local save failed: {e}")
            self.state["message"] = "Save Failed!"

    def get_status(self):
        return self.state
