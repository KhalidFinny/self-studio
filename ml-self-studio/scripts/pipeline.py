import os
import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, applications
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import classification_report

# Set random seeds for reproducibility
tf.random.set_seed(72)
np.random.seed(72)

def get_args():
    parser = argparse.ArgumentParser(description="Train ResNet50 for Palm/Fist Recognition")
    parser.add_argument("--dataset_dir", type=str, default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset_cropped"), help="Path to the raw dataset directory")
    parser.add_argument("--model_dir", type=str, default="models/resnet50", help="Directory to save the trained model")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--epochs", type=int, default=25, help="Number of epochs")
    parser.add_argument("--img_size", type=int, default=224, help="Input image size")
    parser.add_argument("--learning_rate", type=float, default=1e-4, help="Initial learning rate")
    return parser.parse_args()

def build_model(input_shape):

    # Data Augmentation Layers
    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.1),
        layers.RandomZoom(0.1),
        layers.RandomContrast(0.1),
        layers.RandomBrightness(0.1),
    ], name="data_augmentation")

    # Base Model
    base_model = applications.ResNet50(
        include_top=False,
        weights="imagenet",
        input_shape=input_shape
    )
    
    # Fine-tuning configuration
    base_model.trainable = True
    # Freeze all layers except the last 30
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    inputs = tf.keras.Input(shape=input_shape)
    x = data_augmentation(inputs)
    
    # Preprocess input for ResNet50 (scales to [-1, 1] or similar expected by ResNet)
    # Wrapping in Lambda to avoid pickling issues with module references
    x = layers.Lambda(applications.resnet50.preprocess_input, name='preprocess_input')(x)
    
    x = base_model(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(1, activation="sigmoid")(x)

    model = models.Model(inputs, outputs)
    return model

def main():
    args = get_args()
    
    print(f"[INFO] Dataset Directory: {args.dataset_dir}")
    if not os.path.exists(args.dataset_dir):
        print(f"[ERROR] Dataset directory not found: {args.dataset_dir}")
        return

    # Custom Time-Based Splitting
    print("[INFO] Loading and splitting datasets based on timestamps...")
    
    def load_and_split_paths(dataset_dir, split_ratio=0.8):
        image_paths = []
        labels = []
        class_names = sorted([d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))])
        
        for label_idx, class_name in enumerate(class_names):
            class_dir = os.path.join(dataset_dir, class_name)
            # Get all files with full paths
            files = [os.path.join(class_dir, f) for f in os.listdir(class_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            # Sort by modification time
            files.sort(key=os.path.getmtime)
            
            # Split
            split_point = int(len(files) * split_ratio)
            train_files = files[:split_point]
            val_files = files[split_point:]
            
            image_paths.extend(train_files)
            labels.extend([label_idx] * len(train_files))
            
            image_paths.extend(val_files)
            labels.extend([label_idx] * len(val_files))
            
            # We need to return train/val separately to ensure we don't mix them up later
            # But the above approach mixes them in the lists. Let's redo to keep them separate.
            
        train_paths = []
        train_labels = []
        val_paths = []
        val_labels = []
        
        for label_idx, class_name in enumerate(class_names):
            class_dir = os.path.join(dataset_dir, class_name)
            files = [os.path.join(class_dir, f) for f in os.listdir(class_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            files.sort(key=os.path.getmtime)
            
            split_point = int(len(files) * split_ratio)
            
            train_paths.extend(files[:split_point])
            train_labels.extend([label_idx] * len(files[:split_point]))
            
            val_paths.extend(files[split_point:])
            val_labels.extend([label_idx] * len(files[split_point:]))
            
        return (train_paths, train_labels), (val_paths, val_labels), class_names

    (train_paths, train_labels), (val_paths, val_labels), class_names = load_and_split_paths(args.dataset_dir)
    
    print(f"[INFO] Classes found: {class_names}")
    print(f"[INFO] Training samples: {len(train_paths)}")
    print(f"[INFO] Validation samples: {len(val_paths)}")

    def load_image(path, label):
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, [args.img_size, args.img_size])
        return img, label

    # Create TensorFlow Datasets
    train_ds = tf.data.Dataset.from_tensor_slices((train_paths, train_labels))
    train_ds = train_ds.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.batch(args.batch_size)

    val_ds = tf.data.Dataset.from_tensor_slices((val_paths, val_labels))
    val_ds = val_ds.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.batch(args.batch_size)

    # class_names is already defined above
    # class_names = train_ds.class_names
    print(f"[INFO] Classes found: {class_names}")

    # Configure dataset for performance
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

    # Build Model
    print("[INFO] Building model...")
    model = build_model((args.img_size, args.img_size, 3))
    
    model.compile(
        optimizer=optimizers.Adam(learning_rate=args.learning_rate),
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )
    
    model.summary()

    # Callbacks
    os.makedirs(args.model_dir, exist_ok=True)
    checkpoint_path = os.path.join(args.model_dir, "best_model.keras")
    
    callbacks = [
        ModelCheckpoint(checkpoint_path, save_best_only=True, monitor="val_loss", mode="min"),
        EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.2, patience=3, min_lr=1e-6)
    ]

    # Train
    print("[INFO] Starting training...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks
    )

    print(f"[INFO] Training finished. Best model saved to {checkpoint_path}")

    # Evaluate on Validation Set
    print("[INFO] Evaluating on validation set...")
    # Load best model weights
    model.load_weights(checkpoint_path)

    y_true = []
    y_pred_probs = []

    # Iterate over the validation dataset to get true labels and predictions
    # Note: We iterate directly to ensure alignment between images and labels
    for images, labels in val_ds:
        preds = model.predict(images, verbose=0)
        y_true.extend(labels.numpy())
        y_pred_probs.extend(preds)

    y_true = np.array(y_true)
    y_pred_probs = np.array(y_pred_probs)
    
    # Convert probabilities to binary predictions (threshold 0.5)
    y_pred = (y_pred_probs > 0.5).astype(int)

    print("\n[INFO] Classification Report:")
    print(classification_report(y_true, y_pred, target_names=class_names))

if __name__ == "__main__":
    main()
