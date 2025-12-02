# Utility untuk deteksi gesture menggunakan ResNet50
import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
import os
import mediapipe as mp
from typing import Tuple, Optional, Dict, List, Any

from tensorflow.keras.applications.resnet50 import preprocess_input

class ResNet50GestureDetector:
    """
    Gesture detector using a pre-trained ResNet50 model and MediaPipe Hands.
    Detects 'Fist' (Class 0) and 'Palm' (Class 1).
    """
    
    def __init__(self, model_path: str = "models/resnet50/best_model.keras", confidence: float = 0.85):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to the .keras model file.
            confidence: Confidence threshold for classification.
        """
        
        # Resolve model path (relatif dari root project)
        if not os.path.isabs(model_path):
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            model_path = os.path.join(root_dir, model_path)
        
        # Cek apakah model path ada
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Please ensure the model file exists."
            )
        
        # Load model with custom_objects for preprocess_input
        self.model = keras.models.load_model(model_path, custom_objects={'preprocess_input': preprocess_input})
        self.confidence = confidence
        self.fist_detected_frames = 0
        self.trigger_active = False
        
        # Setup MediaPipe untuk deteksi tangan
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=True, # Changed to True to fix timestamp errors with frame skipping
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Class names (Alphabetical: 0=fist, 1=palm)
        self.class_names = ['fist', 'palm']
    
    def preprocess_frame(self, frame: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        Preprocess the frame for ResNet50 inference.
        
        Args:
            frame: BGR image frame.
            bbox: Optional (x, y, w, h) bounding box to crop.
            
        Returns:
            Preprocessed image batch (1, 224, 224, 3).
        """
        
        if bbox:
            x, y, w, h = bbox
            # Crop hand region dengan padding
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(frame.shape[1] - x, w + 2 * padding)
            h = min(frame.shape[0] - y, h + 2 * padding)
            cropped = frame[y:y+h, x:x+w]
        else:
            cropped = frame
        
        # Resize ke 224x224
        resized = cv2.resize(cropped, (224, 224))
        
        # Convert BGR ke RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize ke [0, 1]
        normalized = rgb.astype(np.float32) / 255.0
        
        # Expand dimensions untuk batch
        expanded = np.expand_dims(normalized, axis=0)
        
        return expanded
    
    def detect_hand(self, frame: np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], Any]:
        """
        Detect hand using MediaPipe.
        
        Returns:
            (bbox, landmarks) or (None, None)
        """
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # Get bounding box dari landmarks
            h, w = frame.shape[:2]
            x_coords = [lm.x * w for lm in hand_landmarks.landmark]
            y_coords = [lm.y * h for lm in hand_landmarks.landmark]
            
            x_min = int(min(x_coords))
            x_max = int(max(x_coords))
            y_min = int(min(y_coords))
            y_max = int(max(y_coords))
            
            bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
            
            return bbox, hand_landmarks
        
        return None, None
    
    def classify_gesture(self, preprocessed_img: np.ndarray) -> Tuple[int, float, Tuple[float, float]]:
        """
        Classify the gesture using the loaded ResNet50 model.
        
        Returns:
            (predicted_class, confidence, (palm_prob, fist_prob))
        """
        
        predictions = self.model.predict(preprocessed_img, verbose=0)
        
        # Binary classification: predictions[0][0] adalah probabilitas Class 1 (Palm)
        # Karena alphabetical: 0=Fist, 1=Palm
        palm_prob = float(predictions[0][0])
        fist_prob = 1.0 - palm_prob
        
        # Tentukan class berdasarkan threshold
        if palm_prob >= 0.5:
            predicted_class = 1  # palm
            confidence = palm_prob
        else:
            predicted_class = 0  # fist
            confidence = fist_prob
        
        return predicted_class, confidence, (palm_prob, fist_prob)
    
    def get_detection_result(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Perform full detection pipeline on a frame.
        
        Returns:
            Dictionary containing bbox, landmarks, label, confidence, etc.
        """
        
        bbox, landmarks = self.detect_hand(frame)
        
        result = {
            "bbox": bbox,
            "landmarks": landmarks,
            "detected_palm": False,
            "confidence": 0.0,
            "label": "no hand",
            "predicted_class": None
        }
        
        if bbox:
            # Preprocess dan classify
            preprocessed = self.preprocess_frame(frame, bbox)
            predicted_class, conf, probs = self.classify_gesture(preprocessed)
            
            result["confidence"] = conf
            result["predicted_class"] = predicted_class
            result["label"] = self.class_names[predicted_class]
            
            # Cek apakah PALM terdeteksi (Class 1)
            # User requested PALM trigger
            if predicted_class == 1 and conf >= self.confidence:
                result["detected_palm"] = True
                
        return result

    def annotate_frame(self, frame: np.ndarray, result: Dict[str, Any], min_frames: int = 5) -> Tuple[np.ndarray, bool, bool]:
        """
        Draw annotations on the frame and determine if trigger should fire.
        
        Args:
            frame: The image frame.
            result: The detection result dictionary.
            min_frames: Number of consecutive frames required for trigger stability.
            
        Returns:
            (annotated_frame, detected_palm_bool, should_trigger_bool)
        """
        if not result:
            return frame, False, False

        bbox = result.get("bbox")
        landmarks = result.get("landmarks")
        detected_palm = result.get("detected_palm", False)
        confidence = result.get("confidence", 0.0)
        label = result.get("label", "")
        
        # Update state based on current detection
        # Note: Ideally this should be separate, but for now we keep it here for visualization logic
        # logic moved to update_state in services.py loop, but we read it here?
        # Actually services.py calls update_state separately.
        
        should_trigger = self.fist_detected_frames >= min_frames and not self.trigger_active

        if bbox:
            x, y, w, h = bbox
            # Warna hijau jika Trigger terdeteksi dan stabil, kuning jika tidak
            color = (0, 255, 0) if detected_palm and self.fist_detected_frames >= min_frames else (0, 255, 255)
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Landmarks removed for cleaner "YOLO-style" look
            # if landmarks: ...
            
            # Draw label
            text = f"{label} {confidence:.2f}"
            cv2.putText(frame, text, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            # Tidak ada tangan terdeteksi
            cv2.putText(frame, "No hand detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
        return frame, detected_palm, should_trigger

    def update_state(self, result: Dict[str, Any]) -> None:
        """
        Update internal state (consecutive frames) based on result.
        """
        if result and result.get("detected_palm"):
            self.fist_detected_frames += 1
        else:
            self.fist_detected_frames = 0

    def detect(self, frame: np.ndarray, min_frames: int = 5) -> Tuple[np.ndarray, bool, bool]:
        """
        Wrapper for backward compatibility.
        """
        result = self.get_detection_result(frame)
        self.update_state(result)
        return self.annotate_frame(frame, result, min_frames)
    
    def reset_trigger(self) -> None:
        """Reset trigger state."""
        self.trigger_active = False
        self.fist_detected_frames = 0
    
    def set_trigger_active(self, value: bool) -> None:
        """Set trigger active state."""
        self.trigger_active = value
    
    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'hands'):
            self.hands.close()
