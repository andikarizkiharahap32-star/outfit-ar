# Detailed Exploration Report — CNN & Backbone Fixes (Milestone 1)

## Executive Summary
This report analyzes and details the current implementations and proposed fixes for four identified bugs within the CNN training and backbone architecture files:
1. **Bug #2 (Data Augmentation in train_cnn.py)**
2. **Bug #8 (Layer Order in efficientnet_backbone.py)**
3. **Bug #13 (Class Weights in train_cnn.py)**
4. **Bug #15 (Learning Rate and Regularization in train_cnn.py and efficientnet_backbone.py)**

No code has been modified or implemented. This document contains only the analytical findings and precise change proposals.

---

## 1. Bug #2: Data Augmentation in train_cnn.py

### Findings of Current Implementation
Currently, `train_cnn.py` loads the skin tone dataset using `tf.keras.utils.image_dataset_from_directory` and performs caching and prefetching directly. It does not apply any data augmentation, which can cause overfitting.
```python
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR,
        shuffle=True,
        batch_size=BATCH_SIZE,
        image_size=IMG_SIZE,
        label_mode='categorical'
    )
    ...
    # Optimasi kecepatan baca data (Prefetching)
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
```

### Proposed Exact Code Changes
We propose to define a data augmentation pipeline using Keras preprocessing layers and map it to `train_dataset` using `tf.data.Dataset.map` (specifying `training=True`). Caching is applied before mapping to ensure disk IO is cached, while the random augmentations are evaluated dynamically on-the-fly each epoch.

In `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`:
```python
<<<<
    # Optimasi kecepatan baca data (Prefetching)
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
====
    # Optimasi kecepatan baca data (Prefetching)
    AUTOTUNE = tf.data.AUTOTUNE
    
    # Safe data augmentation strategy (horizontal flip, random brightness/contrast 20%, rotation 10 degrees)
    # without aggressive cropping or color jitter.
    data_augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(factor=10.0 / 360.0),
        tf.keras.layers.RandomBrightness(factor=0.2, value_range=(0, 255)),
        tf.keras.layers.RandomContrast(factor=0.2)
    ], name="data_augmentation")
    
    train_dataset = train_dataset.cache().map(
        lambda x, y: (data_augmentation(x, training=True), y),
        num_parallel_calls=AUTOTUNE
    ).prefetch(buffer_size=AUTOTUNE)
    
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
>>>>
```

---

## 2. Bug #8 & Bug #15: Layer Order and Regularization in efficientnet_backbone.py

### Findings of Current Implementation
The dense head inside `build_skin_tone_classifier` is currently structured as:
```python
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
```
This has two issues:
1. **Incorrect layer order**: `BatchNormalization` is placed after `Dropout`. The correct order is `Dense (linear) -> BN -> Activation (relu) -> Dropout -> output`.
2. **Missing regularization**: No `kernel_regularizer` is configured on the `head_dense` layer.

### Proposed Exact Code Changes
Reorder the layers in the dense head and add `kernel_regularizer=keras.regularizers.L2(1e-4)` to the `head_dense` layer.

In `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py`:
```python
<<<<
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
====
    x = keras.layers.Dense(
        256,
        activation=None,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    x = keras.layers.Activation("relu", name="head_activation")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
>>>>
```

---

## 3. Bug #13: Class Weights in train_cnn.py

### Findings of Current Implementation
Currently, class weights are not computed or passed to `model.fit()`, causing the model to treat all classes equally in terms of loss, despite potential imbalance in the dataset directories (`dark`, `fair`, `light`).
```python
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping]
    )
```

### Proposed Exact Code Changes
Calculate class weights dynamically from class folder file counts in the training directory, using the standard balanced class weights formula:
$$w_j = \frac{N}{C \times n_j}$$
And pass `class_weight` to `model.fit()`.

In `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`:

**Step 1: Calculate class weights**
```python
<<<<
    # Deteksi otomatis jumlah kelas dari folder dataset
    class_names = train_dataset.class_names
    num_classes = len(class_names)
    logger.info(f"🎯 Ditemukan {num_classes} kategori warna kulit: {class_names}")
====
    # Deteksi otomatis jumlah kelas dari folder dataset
    class_names = train_dataset.class_names
    num_classes = len(class_names)
    logger.info(f"🎯 Ditemukan {num_classes} kategori warna kulit: {class_names}")

    # Hitung class weights secara otomatis dari jumlah file per kelas
    class_counts = {}
    total_samples = 0
    for class_name in class_names:
        class_path = os.path.join(TRAIN_DIR, class_name)
        count = len([f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))])
        class_counts[class_name] = count
        total_samples += count

    class_weights = {}
    for i, class_name in enumerate(class_names):
        count = class_counts[class_name]
        class_weights[i] = total_samples / (num_classes * count)
    
    logger.info(f"📊 Class counts: {class_counts}")
    logger.info(f"⚖️ Class weights: {class_weights}")
>>>>
```

**Step 2: Pass class weights to model.fit**
```python
<<<<
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping]
    )
====
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        class_weight=class_weights,
        callbacks=[checkpoint, early_stopping]
    )
>>>>
```

---

## 4. Bug #15: Learning Rate in train_cnn.py

### Findings of Current Implementation
The Adam optimizer in `train_cnn.py` is configured with a default learning rate of `0.001`:
```python
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
```

### Proposed Exact Code Changes
Change the learning rate of the Adam optimizer to `1e-4` (`0.0001`) to stabilize training with a pretrained backbone.

In `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`:
```python
<<<<
    # Menentukan metode evaluasi & hukuman (Loss & Optimizer)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
====
    # Menentukan metode evaluasi & hukuman (Loss & Optimizer)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
>>>>
```

---

## 5. Verification Instructions
To verify these proposals:
1. **Compilation & Syntax Check**:
   Once the implementer applies the changes, verify that the training script compiles and starts correctly by running:
   ```powershell
   backend\venv\Scripts\python backend\ml\cnn\train_cnn.py
   ```
   *Note: If data is missing or the run is interrupted, check that the console output logs the class counts and computed class weights correctly, and that data augmentation mapping starts successfully.*
2. **Model Structure Verification**:
   Verify the dense head layer names, ordering, and regularization parameters using:
   ```powershell
   backend\venv\Scripts\python -c "from backend.ml.cnn.efficientnet_backbone import build_skin_tone_classifier; model = build_skin_tone_classifier(3); model.summary()"
   ```
   Ensure the output printed model summary shows:
   - `head_dense (Dense)` (linear, followed by `kernel_regularizer` config)
   - `head_bn (BatchNormalization)`
   - `head_activation (Activation)` (relu)
   - `head_dropout (Dropout)`
   - `skin_tone_output (Dense)` (softmax)
