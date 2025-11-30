import os
import cv2
import mediapipe as mp
import argparse
from pathlib import Path

def get_args():
    parser = argparse.ArgumentParser(description="Preprocess dataset by cropping hands")
    parser.add_argument("--input_dir", type=str, default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset"), help="Path to raw dataset")
    parser.add_argument("--output_dir", type=str, default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset_cropped"), help="Path to save cropped dataset")
    parser.add_argument("--padding", type=int, default=20, help="Padding around the hand bounding box")
    parser.add_argument("--img_size", type=int, default=224, help="Target image size")
    return parser.parse_args()

def main():
    args = get_args()
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5
    )

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    if not input_path.exists():
        print(f"[ERROR] Input directory not found: {input_path}")
        return

    # Process each class
    for class_dir in input_path.iterdir():
        if not class_dir.is_dir():
            continue
            
        class_name = class_dir.name
        print(f"[INFO] Processing class: {class_name}")
        
        output_class_dir = output_path / class_name
        output_class_dir.mkdir(parents=True, exist_ok=True)
        
        files = list(class_dir.glob("*.[jJ][pP][gG]")) + list(class_dir.glob("*.[pP][nN][gG]"))
        
        count_saved = 0
        count_skipped = 0
        
        for file_path in files:
            img = cv2.imread(str(file_path))
            if img is None:
                continue
                
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)
            
            if class_name.lower() == "background":
                # For background, we expect NO hands.
                # If hands detected, we might want to skip to be safe (avoid polluting background with hands)
                # OR just save the full image anyway if we trust our labels.
                # Let's save full image if NO hand detected, to be pure.
                if not results.multi_hand_landmarks:
                    # Resize and save
                    img_resized = cv2.resize(img, (args.img_size, args.img_size))
                    cv2.imwrite(str(output_class_dir / file_path.name), img_resized)
                    count_saved += 1
                else:
                    # Hand detected in background class -> Skip
                    count_skipped += 1
            else:
                # For Palm/Fist, we expect hands.
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # Get bounding box
                        h, w, _ = img.shape
                        x_min, x_max, y_min, y_max = w, 0, h, 0
                        
                        for lm in hand_landmarks.landmark:
                            x, y = int(lm.x * w), int(lm.y * h)
                            x_min = min(x_min, x)
                            x_max = max(x_max, x)
                            y_min = min(y_min, y)
                            y_max = max(y_max, y)
                        
                        # Add padding
                        x_min = max(0, x_min - args.padding)
                        x_max = min(w, x_max + args.padding)
                        y_min = max(0, y_min - args.padding)
                        y_max = min(h, y_max + args.padding)
                        
                        # Crop
                        crop = img[y_min:y_max, x_min:x_max]
                        
                        if crop.size == 0:
                            continue
                            
                        # Resize
                        crop_resized = cv2.resize(crop, (args.img_size, args.img_size))
                        
                        # Save
                        cv2.imwrite(str(output_class_dir / file_path.name), crop_resized)
                        count_saved += 1
                        break # Only take the first hand
                else:
                    # No hand detected in Palm class -> Skip
                    count_skipped += 1

        print(f"  Saved: {count_saved}, Skipped: {count_skipped}")

if __name__ == "__main__":
    main()
