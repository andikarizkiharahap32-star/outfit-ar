"""
OutfitAR - CNN Training Script v4 (Production Grade - Fixed)
Two-Phase Training dengan perbaikan agresif dari v3

Perbaikan dari v3:
  - Phase 1 LR dinaikkan ke 3e-4 (dari 1e-4) untuk warm-up lebih cepat
  - Phase 2 LR dinaikkan ke 5e-5 (dari 1e-5) agar fine-tune benar-benar efektif
  - Unfreeze SEMUA layer backbone (bukan hanya 30)
  - Head lebih kuat: Dense(512) + Dense(128) untuk membedakan Fair vs Light
  - Patience EarlyStopping dinaikkan ke 10
  - Augmentasi diperkuat dengan color jitter
"""

import os
import sys
import numpy as np
import tensorflow as tf
from tensorflow import keras
from loguru import logger

# ==========================================
# 1. KONFIGURASI PATH & PARAMETER
# ==========================================
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset_Skin", "Dataset_Skin")
TRAIN_DIR   = os.path.join(DATASET_DIR, "train")
VALID_DIR   = os.path.join(DATASET_DIR, "valid")
TEST_DIR    = os.path.join(DATASET_DIR, "test")

WEIGHTS_DIR = os.path.join(BASE_DIR, "..", "weights")
os.makedirs(WEIGHTS_DIR, exist_ok=True)

BATCH_SIZE = 16           # Batch lebih kecil = gradient lebih stabil untuk dataset kecil
IMG_SIZE   = (224, 224)

PHASE1_EPOCHS = 20
PHASE1_LR     = 3e-4      # Lebih agresif untuk warm-up head

PHASE2_EPOCHS = 50        # Banyak epoch, EarlyStopping yang putuskan kapan berhenti
PHASE2_LR     = 5e-5      # 5x lebih besar dari v3


# ==========================================
# 2. DATA AUGMENTATION
# ==========================================
data_augmentation = keras.Sequential([
    keras.layers.RandomFlip("horizontal"),
    keras.layers.RandomRotation(0.08),          # +/- 29 derajat (sedikit lebih lebar)
    keras.layers.RandomBrightness(factor=0.15), # Kurangi sedikit agar warna kulit tidak terdistorsi
    keras.layers.RandomContrast(factor=0.15),
    keras.layers.RandomZoom(
        height_factor=(-0.08, 0.08),
        width_factor=(-0.08, 0.08),
    ),
], name="augmentation")


def build_stronger_classifier(num_classes: int = 3) -> keras.Model:
    """
    Arsitektur CNN dengan head yang lebih kuat.
    Head lebih dalam (512 -> 128 -> num_classes) untuk membedakan
    kategori yang mirip (Fair vs Light).
    """
    base_model = keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(*IMG_SIZE, 3),
        pooling="avg",          # GlobalAveragePooling2D
    )
    base_model.trainable = False  # Frozen dulu untuk Phase 1

    inputs = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
    x = base_model(inputs, training=False)      # (batch, 1280)

    # Head layer 1: Dense 512
    x = keras.layers.Dense(512, kernel_regularizer=keras.regularizers.L2(1e-4))(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.Dropout(0.5)(x)

    # Head layer 2: Dense 128 (bottleneck untuk fitur yang lebih spesifik)
    x = keras.layers.Dense(128, kernel_regularizer=keras.regularizers.L2(1e-4))(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.Dropout(0.3)(x)

    # Output
    outputs = keras.layers.Dense(num_classes, activation="softmax", name="skin_tone_output")(x)

    model = keras.Model(inputs, outputs, name="SkinToneClassifier_v4")
    logger.info(f"[CNN] Model v4 dibangun: {model.count_params():,} total params")
    return model


def main():
    logger.info("=" * 70)
    logger.info("[CNN v4] TWO-PHASE TRAINING - FIXED VERSION")
    logger.info("=" * 70)

    # ==========================================
    # 3. MEMUAT DATASET
    # ==========================================
    logger.info("[DATA] Membaca dataset...")

    train_dataset = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR, shuffle=True, batch_size=BATCH_SIZE,
        image_size=IMG_SIZE, label_mode="int",
    )
    valid_dataset = tf.keras.utils.image_dataset_from_directory(
        VALID_DIR, shuffle=False, batch_size=BATCH_SIZE,
        image_size=IMG_SIZE, label_mode="int",
    )
    test_dataset = tf.keras.utils.image_dataset_from_directory(
        TEST_DIR, shuffle=False, batch_size=BATCH_SIZE,
        image_size=IMG_SIZE, label_mode="int",
    )

    class_names = train_dataset.class_names
    num_classes = len(class_names)
    logger.info(f"[DATA] Kelas: {class_names}")

    # ==========================================
    # 4. CLASS WEIGHTS
    # ==========================================
    label_counts = np.zeros(num_classes, dtype=np.int64)
    for _, labels in train_dataset.unbatch():
        label_counts[int(labels.numpy())] += 1

    total_samples = label_counts.sum()
    class_weights = {}
    for i, count in enumerate(label_counts):
        class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0
    logger.info(f"[DATA] Distribusi: {dict(zip(class_names, label_counts))}")
    logger.info(f"[DATA] Class weights: {class_weights}")

    # ==========================================
    # 5. PREPROCESSING PIPELINE
    # ==========================================
    AUTOTUNE = tf.data.AUTOTUNE

    train_processed = (
        train_dataset.cache()
        .map(lambda x, y: (data_augmentation(x, training=True), y), num_parallel_calls=AUTOTUNE)
        .map(lambda x, y: (tf.keras.applications.efficientnet.preprocess_input(x), y), num_parallel_calls=AUTOTUNE)
        .prefetch(buffer_size=AUTOTUNE)
    )
    valid_processed = (
        valid_dataset
        .map(lambda x, y: (tf.keras.applications.efficientnet.preprocess_input(x), y), num_parallel_calls=AUTOTUNE)
        .cache().prefetch(buffer_size=AUTOTUNE)
    )
    test_processed = (
        test_dataset
        .map(lambda x, y: (tf.keras.applications.efficientnet.preprocess_input(x), y), num_parallel_calls=AUTOTUNE)
        .cache().prefetch(buffer_size=AUTOTUNE)
    )

    checkpoint_path = os.path.join(WEIGHTS_DIR, "best_skin_tone_model.keras")

    # ==========================================
    # 6. BANGUN MODEL v4
    # ==========================================
    model = build_stronger_classifier(num_classes=num_classes)

    # ==========================================
    # 7. FASE 1: HEAD TRAINING (Backbone Frozen)
    # ==========================================
    logger.info("=" * 70)
    logger.info(f"[FASE 1] HEAD WARM-UP | Epochs: {PHASE1_EPOCHS} | LR: {PHASE1_LR}")
    logger.info("=" * 70)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=PHASE1_LR),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=[
            keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            keras.metrics.SparseTopKCategoricalAccuracy(k=2, name="top2_accuracy"),
        ],
    )

    trainable_p = sum(keras.backend.count_params(w) for w in model.trainable_weights)
    logger.info(f"[MODEL] Trainable params (head only): {trainable_p:,}")

    callbacks_p1 = [
        keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_path, save_best_only=True,
            monitor="val_accuracy", mode="max", verbose=1,
        ),
        keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=7,
            restore_best_weights=True, verbose=1,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6, verbose=1,
        ),
    ]

    h1 = model.fit(
        train_processed, validation_data=valid_processed,
        epochs=PHASE1_EPOCHS, callbacks=callbacks_p1,
        class_weight=class_weights,
    )
    p1_best = max(h1.history.get("val_accuracy", [0]))
    logger.info(f"[FASE 1 DONE] Best Val Accuracy: {p1_best:.4f}")

    # ==========================================
    # 8. FASE 2: FULL FINE-TUNE (Semua Layer)
    # ==========================================
    logger.info("=" * 70)
    logger.info(f"[FASE 2] FULL FINE-TUNE | Epochs: {PHASE2_EPOCHS} | LR: {PHASE2_LR}")
    logger.info("         Semua layer EfficientNet di-unfreeze")
    logger.info("=" * 70)

    # Unfreeze SEMUA layer backbone
    for layer in model.layers:
        if "efficientnet" in layer.name.lower():
            layer.trainable = True
            frozen_count = 0
            trainable_count = 0
            for sub_layer in layer.layers:
                sub_layer.trainable = True
                trainable_count += 1
            logger.info(f"[MODEL] Backbone unfreeze: {trainable_count} layers aktif")
            break

    # Re-compile dengan LR lebih kecil
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=PHASE2_LR),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=[
            keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            keras.metrics.SparseTopKCategoricalAccuracy(k=2, name="top2_accuracy"),
        ],
    )

    trainable_p = sum(keras.backend.count_params(w) for w in model.trainable_weights)
    logger.info(f"[MODEL] Trainable params (full): {trainable_p:,}")

    callbacks_p2 = [
        keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_path, save_best_only=True,
            monitor="val_accuracy", mode="max", verbose=1,
        ),
        keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=10,    # Sangat sabar
            restore_best_weights=True, verbose=1,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=4,
            min_lr=1e-7, verbose=1,
        ),
    ]

    h2 = model.fit(
        train_processed, validation_data=valid_processed,
        epochs=PHASE2_EPOCHS, callbacks=callbacks_p2,
        class_weight=class_weights,
    )
    p2_best = max(h2.history.get("val_accuracy", [0]))
    logger.info(f"[FASE 2 DONE] Best Val Accuracy: {p2_best:.4f}")

    # ==========================================
    # 9. EVALUASI TEST SET
    # ==========================================
    logger.info("=" * 70)
    logger.info("[EVAL] EVALUASI PADA TEST SET (210 gambar)")
    logger.info("=" * 70)

    best_model = keras.models.load_model(checkpoint_path)
    test_loss, test_acc, test_top2 = best_model.evaluate(test_processed, verbose=1)

    logger.info(f"[EVAL] Test Loss     : {test_loss:.4f}")
    logger.info(f"[EVAL] Test Accuracy : {test_acc:.4f} ({test_acc*100:.1f}%)")
    logger.info(f"[EVAL] Test Top-2 Acc: {test_top2:.4f} ({test_top2*100:.1f}%)")

    # ==========================================
    # 10. CONFUSION MATRIX
    # ==========================================
    all_preds = []
    all_labels = []
    for images, labels in test_processed:
        preds = best_model.predict(images, verbose=0)
        pred_classes = np.argmax(preds, axis=1)
        all_preds.extend(pred_classes)
        all_labels.extend(labels.numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    cm = np.zeros((num_classes, num_classes), dtype=int)
    for tl, pl in zip(all_labels, all_preds):
        cm[int(tl)][int(pl)] += 1

    logger.info(f"\n{'='*50}")
    logger.info("CONFUSION MATRIX")
    logger.info(f"{'='*50}")
    logger.info(f"Predicted ->  {class_names}")
    for i, row in enumerate(cm):
        logger.info(f"  Actual {class_names[i]:>6}: {row}")

    logger.info(f"\n{'='*50}")
    logger.info("CLASSIFICATION REPORT")
    logger.info(f"{'='*50}")
    logger.info(f"{'Class':>10} | {'Precision':>9} | {'Recall':>6} | {'F1-Score':>8} | {'Support':>7}")
    logger.info(f"{'-'*55}")

    for i, name in enumerate(class_names):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(num_classes)) - tp
        fn = sum(cm[i]) - tp
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        support = sum(cm[i])
        logger.info(f"{name:>10} | {prec:>9.4f} | {rec:>6.4f} | {f1:>8.4f} | {support:>7}")

    total_correct = sum(cm[i][i] for i in range(num_classes))
    total_test = all_labels.shape[0]
    overall_acc = total_correct / total_test

    logger.info(f"{'-'*55}")
    logger.info(f"Accuracy: {overall_acc:.4f} ({overall_acc*100:.1f}%)")
    logger.info(f"Correct: {total_correct} / {total_test}")
    logger.info(f"Misclassified: {total_test - total_correct}")

    logger.info("=" * 70)
    logger.info(f"[FINAL] Phase 1 Best Val Acc: {p1_best:.4f}")
    logger.info(f"[FINAL] Phase 2 Best Val Acc: {p2_best:.4f}")
    logger.info(f"[FINAL] Test Accuracy       : {overall_acc:.4f} ({overall_acc*100:.1f}%)")
    logger.info("=" * 70)

    return h1, h2


if __name__ == "__main__":
    main()