import threading
import time
import cv2
import os
import sys
import atexit
import numpy as np
from typing import Optional, Generator, Dict, Any
from django.conf import settings
from django.core.files.base import ContentFile
from .utils.camera import Camera
from .utils.efficientnet_detector import ResNet50GestureDetector
from .models import Capture

class CameraService:
    # Singleton service to manage the camera feed, gesture detection, and photo capture.
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
        
        print(f"[INFO] Initializing CameraService in PID: {os.getpid()}")
        
        self.camera = Camera(camera_id=0, width=1280, height=720)
        
        # Register cleanup
        atexit.register(self.cleanup)
        
        # Initialize detector
        # Path to model: ../models/resnet50/best_model.keras relative to BASE_DIR
        model_path = os.path.join(settings.BASE_DIR.parent, 'models', 'resnet50', 'best_model.keras')
        try:
            # User requested 60% confidence threshold
            self.detector = ResNet50GestureDetector(model_path=model_path, confidence=0.60)
            print(f"[SUCCESS] ResNet50 model loaded from {model_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load ResNet50 model: {e}")
            self.detector = None

        self.imaging_edge = None # Not implemented yet
        self.countdown_seconds = 3
        
        self.frame: Optional[np.ndarray] = None
        self.clean_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        self.is_running = True
        
        # Shared state
        self.state: Dict[str, Any] = {
            "countdown": None,
            "message": "",
            "flash": False
        }
        
        self.frame_count = 0
        self.last_result: Optional[Dict[str, Any]] = None
        
        # Start camera thread
        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()
        
        self._initialized = True

    def cleanup(self):
        print(f"[INFO] Cleaning up CameraService in PID: {os.getpid()}")
        self.is_running = False
        if hasattr(self, 'camera') and self.camera:
            self.camera.release()

    def _camera_loop(self) -> None:
        """
        Main loop to read frames from the camera and perform gesture detection.
        Includes auto-recovery if camera fails.
        """
        print("[INFO] Camera loop started")
        
        # Initial Open
        if not self.camera.open():
            print("[FAIL] Camera not accessible on startup.")
            # Don't return, try to recover in loop
        
        consecutive_failures = 0
        
        while self.is_running:
            ret, frame = self.camera.read()
            
            if not ret:
                consecutive_failures += 1
                if consecutive_failures % 20 == 0: # Log every 20 failures (~2s)
                    print(f"[WARN] Failed to read frame ({consecutive_failures})")
                
                if consecutive_failures > 50: # ~5 seconds of failure
                    print("[WARN] Camera unresponsive. Attempting restart...")
                    self.camera.release()
                    time.sleep(1)
                    if self.camera.open():
                        print("[SUCCESS] Camera recovered!")
                        consecutive_failures = 0
                    else:
                        print("[FAIL] Camera recovery failed.")
                
                time.sleep(0.1)
                continue
            
            # Reset failure counter on success
            consecutive_failures = 0
                
            # Flip horizontally
            frame = cv2.flip(frame, 1)
            
            # Store clean frame for capture
            with self.frame_lock:
                self.clean_frame = frame.copy()
            
            # Detect
            if self.detector:
                try:
                    # Skip frames for detection to improve performance (Every 5th frame)
                    if self.frame_count % 5 == 0:
                        # Resize for faster detection (50% scale)
                        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                        self.last_result = self.detector.get_detection_result(small_frame)
                        
                        # Scale bbox back up
                        if self.last_result["bbox"]:
                            x, y, w, h = self.last_result["bbox"]
                            self.last_result["bbox"] = (x*2, y*2, w*2, h*2)
                            
                        self.detector.update_state(self.last_result)
                    
                    # Always draw annotations
                    # min_frames=10 ensures ~1.5s hold (at 30fps/5skip = 6 checks/sec -> 10 checks ~ 1.6s)
                    frame, detected_gesture, should_trigger = self.detector.annotate_frame(frame, self.last_result, min_frames=10)
                    
                    if should_trigger and self.state["countdown"] is None:
                        print("[INFO] Triggering countdown")
                        threading.Thread(target=self.start_countdown, daemon=True).start()
                except Exception as e:
                    print(f"[ERROR] Detection failed: {e}")
            
            self.frame_count += 1
            
            with self.frame_lock:
                self.frame = frame
            
            time.sleep(0.01)

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Thread-safe method to get the current frame.
        """
        with self.frame_lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def get_clean_frame(self) -> Optional[np.ndarray]:
        """
        Thread-safe method to get the current clean frame (no annotations).
        """
        with self.frame_lock:
            if self.clean_frame is None:
                return None
            return self.clean_frame.copy()

    def generate_frames(self) -> Generator[bytes, None, None]:
        """
        Generator to stream video frames (MJPEG).
        """
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

    def start_countdown(self) -> None:
        """
        Starts the countdown sequence and triggers capture.
        """
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

    def _capture(self) -> None:
        """
        Captures the current frame, saves locally, and attempts DB save.
        Always triggers flash/frontend download.
        """
        try:
            # Use clean frame for capture (no bounding box)
            frame = self.get_clean_frame()
            if frame is not None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                
                # 1. Save Locally (Server-side backup)
                save_dir = os.path.join(settings.MEDIA_ROOT, 'captures')
                os.makedirs(save_dir, exist_ok=True)
                local_path = os.path.join(save_dir, filename)
                cv2.imwrite(local_path, frame)
                print(f"[SUCCESS] Saved locally to: {local_path}")

                # 2. Try Save to DB (Optional)
                try:
                    # Convert to JPEG for DB
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        content = ContentFile(buffer.tobytes())
                        capture = Capture(gesture="Auto/Timer")
                        capture.image.save(filename, content)
                        capture.save()
                        print(f"[SUCCESS] Saved to DB: {capture}")
                except Exception as db_err:
                    print(f"[WARN] DB Save failed (ignoring): {db_err}")

                # 3. Trigger Frontend Download
                self.state["flash"] = True
                self.state["message"] = "Saved!"
                
                def reset_flash():
                    self.state["flash"] = False
                    
                threading.Timer(0.5, reset_flash).start()
            else:
                print("[ERROR] No frame to save")
                self.state["message"] = "Capture Failed!"
        except Exception as e:
            print(f"[ERROR] Capture process failed: {e}")
            self.state["message"] = "Error!"

    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current status (countdown, message, flash).
        """
        return self.state

    def __del__(self):
        if hasattr(self, 'camera') and self.camera:
            print("[INFO] Releasing camera resources...")
            self.camera.release()
            self.is_running = False
