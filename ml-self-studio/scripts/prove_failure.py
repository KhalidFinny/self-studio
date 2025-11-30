import tensorflow as tf
import numpy as np
import os

def main():
    model_path = "models/resnet50/best_model.keras"
    if not os.path.exists(model_path):
        print("Model not found.")
        return

    print(f"Loading model from {model_path}...")
    model = tf.keras.models.load_model(model_path)

    # Generate random noise image
    print("Generating random noise image...")
    noise_img = np.random.rand(1, 224, 224, 3).astype(np.float32)

    # Predict
    print("Predicting on random noise...")
    pred = model.predict(noise_img)
    
    # Since it's binary sigmoid (0-1), and we only have class 0 (Palm)...
    # Wait, if we only have 1 class folder, image_dataset_from_directory might have errored or assigned it index 0.
    # If it's binary, it usually expects 2 classes.
    # If pipeline.py ran successfully with 1 class, let's see what the output shape is.
    
    print(f"Raw Prediction Output: {pred}")
    print("Interpretation: The model likely predicts 'Palm' because it's the only class it knows.")

if __name__ == "__main__":
    main()
