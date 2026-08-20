# Detailed Exploration Report: Milestone 1 (CNN & Backbone Fixes)

This report details the findings and proposed solutions for Bugs #2, #8, #13, and #15 in the `outfit-ar` CNN training and backbone architecture.

---

## 1. Summary of Findings

| Bug ID | Description | File | Current Status | Corrective Action |
|---|---|---|---|---|
| **Bug #2** | Data Augmentation in CNN training | `train_cnn.py` | No data augmentation is implemented; only cache/prefetch is applied. | Implement horizontal flip, random brightness & contrast (20%), and rotation (10 degrees) using a `tf.keras.Sequential` augmentation pipeline mapped after dataset caching. |
| **Bug #8** | Layer order in Dense head | `efficientnet_backbone.py` | Dense (relu) -> Dropout -> BN. Incorrect order. | Reorder to: Dense (linear) -> BN -> Activation (relu) -> Dropout. |
| **Bug #13** | Class weights in training | `train_cnn.py` | `model.fit()` is called without `class_weight`, leading to imbalance issues. | Compute class weights dynamically from dataset folders and pass them to `model.fit()`. |
| **Bug #15** | Learning rate & Regularization | `train_cnn.py` & `efficientnet_backbone.py` | Learning rate is set to `0.001` (1e-3). No kernel regularization on the Dense head. | Change learning rate to `1e-4` and add `kernel_regularizer=L2(1e-4)` to the main Dense head layer. |

---

## 2. Deep Dive and Findings per Bug

### Bug #2: Data Augmentation in CNN Training
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
* **Direct Observation**:
  - The dataset loading on lines 41-55 loads the images using `tf.keras.utils.image_dataset_from_directory` with no image augmentation layer.
  - The pipeline on lines 63-65 only caches and prefetches:
    ```python
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    ```
* **Implications**: The model is prone to overfitting due to training on static images without variations.
* **Proposed Augmentation Strategy**:
  - A `tf.keras.Sequential` block containing:
    1. `tf.keras.layers.RandomFlip("horizontal")`
    2. `tf.keras.layers.RandomRotation(factor=10/360.0)` (representing 10 degrees)
    3. `tf.keras.layers.RandomBrightness(factor=0.2)` (random brightness adjustment up to 20%)
    4. `tf.keras.layers.RandomContrast(factor=0.2)` (random contrast adjustment up to 20%)
  - **Dataset Pipeline Placement**: The augmentation must be mapped to `train_dataset` *after* the `.cache()` call. This ensures that the raw file read/decode is cached once (saving IO time), but the random augmentation runs dynamically at each epoch (providing unique variations every epoch).
  - Validation dataset must *not* be augmented.

---

### Bug #8: Layer Order in Dense Head
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py`
* **Direct Observation**:
  - The classification head in `build_skin_tone_classifier` (lines 46-48) is constructed as:
    ```python
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    ```
  - Here, the order is `Dense (activation=relu)` $\rightarrow$ `Dropout` $\rightarrow$ `BatchNormalization`.
* **Implications**:
  - Applying Batch Normalization *after* activation and dropout violates the standard architecture layout.
  - The correct order should be `Dense (linear)` $\rightarrow$ `BatchNormalization` $\rightarrow$ `Activation (relu)` $\rightarrow$ `Dropout`.
* **Proposed Layer Ordering**:
  ```python
  x = keras.layers.Dense(256, activation=None, name="head_dense")(x)
  x = keras.layers.BatchNormalization(name="head_bn")(x)
  x = keras.layers.Activation("relu", name="head_activation")(x)
  x = keras.layers.Dropout(0.4, name="head_dropout")(x)
  ```
  *(Note: Disabling Dense bias via `use_bias=False` is optional but recommended when followed directly by BatchNormalization).*

---

### Bug #13: Class Weights in CNN Training
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
* **Direct Observation**:
  - The training code in `model.fit()` (lines 105-110) runs without a `class_weight` parameter.
* **Implications**: If the dataset exhibits class imbalance (e.g., more "Light" skin tone images than "Dark"), the model will bias towards the majority class.
* **Proposed Solution**:
  - Calculate class weights dynamically by counting files in the class folders under `TRAIN_DIR`.
  - Formula: $\text{weight}_c = \frac{\text{total\_samples}}{N_{\text{classes}} \times \text{count}_c}$.
  - Pass the calculated `class_weights` dictionary into the `class_weight` parameter of `model.fit()`.

---

### Bug #15: Learning Rate and Regularization
* **Files**:
  - `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py` (Learning Rate)
  - `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py` (Regularization)
* **Direct Observation**:
  - In `train_cnn.py` line 75, the optimizer is configured with a learning rate of `0.001`:
    ```python
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001)
    ```
  - In `efficientnet_backbone.py` line 46, `head_dense` has no regularizer specified.
* **Implications**:
  - A learning rate of `0.001` is too aggressive for fine-tuning or training with a pretrained backbone, often causing representation collapse or unstable loss.
  - Lack of kernel regularization in the dense head increases the risk of overfitting.
* **Proposed Solution**:
  - Update `learning_rate` in `train_cnn.py` to `1e-4` (`0.0001`).
  - Add `kernel_regularizer=keras.regularizers.L2(1e-4)` to the main `Dense` head layer in `efficientnet_backbone.py`.

---

## 3. Proposed Exact Code Changes

### Proposed Changes to `backend/ml/cnn/train_cnn.py`

```python
<<<<
    # Optimasi kecepatan baca data (Prefetching)
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)

    # ==========================================
    # 3. MEMBANGUN MODEL AI
    # ==========================================
    logger.info("🧠 Membangun Arsitektur EfficientNet-B0...")
    model = build_skin_tone_classifier(num_classes=num_classes)

    # Menentukan metode evaluasi & hukuman (Loss & Optimizer)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
====
    # 2a. DEFINISI DATA AUGMENTATION (Bug #2)
    # Horizontal flip, random brightness/contrast 20%, rotation 10 degrees (10/360 ≈ 0.0278)
    data_augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(10/360.0),
        tf.keras.layers.RandomBrightness(0.2),
        tf.keras.layers.RandomContrast(0.2),
    ], name="data_augmentation")

    # 2b. HITUNG CLASS WEIGHTS DINAMIS (Bug #13)
    class_counts = []
    for name in class_names:
        class_path = os.path.join(TRAIN_DIR, name)
        count = len([f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))])
        class_counts.append(count)
    
    total_samples = sum(class_counts)
    class_weights = {}
    for i, count in enumerate(class_counts):
        class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0
        logger.info(f"Class {i} ({class_names[i]}): {count} samples, weight: {class_weights[i]:.4f}")

    # Optimasi kecepatan baca data (Prefetching & Augmentation)
    AUTOTUNE = tf.data.AUTOTUNE
    # Cache before mapping augmentation to avoid repeated file I/O, 
    # but map augmentation after cache so that augmentations are randomized each epoch.
    train_dataset = train_dataset.cache()
    train_dataset = train_dataset.map(
        lambda x, y: (data_augmentation(x, training=True), y),
        num_parallel_calls=AUTOTUNE
    )
    train_dataset = train_dataset.prefetch(buffer_size=AUTOTUNE)
    
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)

    # ==========================================
    # 3. MEMBANGUN MODEL AI
    # ==========================================
    logger.info("🧠 Membangun Arsitektur EfficientNet-B0...")
    model = build_skin_tone_classifier(num_classes=num_classes)

    # Menentukan metode evaluasi & hukuman (Loss & Optimizer) - Bug #15 (Learning Rate 1e-4)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
>>>>
```

And update `model.fit` in `train_cnn.py`:

```python
<<<<
    # ==========================================
    # 5. MULAI LATIHAN! (TRAINING)
    # ==========================================
    logger.info(f"🔥 Memulai proses Training selama {EPOCHS} Epochs...")
    
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping]
    )
====
    # ==========================================
    # 5. MULAI LATIHAN! (TRAINING)
    # ==========================================
    logger.info(f"🔥 Memulai proses Training selama {EPOCHS} Epochs...")
    
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        class_weight=class_weights,  # Pass class weights (Bug #13)
        callbacks=[checkpoint, early_stopping]
    )
>>>>
```

---

### Proposed Changes to `backend/ml/cnn/efficientnet_backbone.py`

```python
<<<<
    # Build full model
    inputs = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
    x = keras.applications.efficientnet.preprocess_input(inputs)
    x = base_model(x, training=False)                        # Feature: (batch, 1280)
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    outputs = keras.layers.Dense(
        num_classes,
        activation="softmax",
        name="skin_tone_output",
    )(x)
====
    # Build full model
    inputs = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
    x = keras.applications.efficientnet.preprocess_input(inputs)
    x = base_model(x, training=False)                        # Feature: (batch, 1280)
    
    # Dense head with regularizer L2(1e-4) (Bug #15) and correct layer ordering (Bug #8)
    # Order: Dense (linear) -> BN -> Activation (relu) -> Dropout -> output
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=False,  # Bias is redundant when followed directly by BatchNormalization
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense"
    )(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    x = keras.layers.Activation("relu", name="head_activation")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    
    outputs = keras.layers.Dense(
        num_classes,
        activation="softmax",
        name="skin_tone_output",
    )(x)
>>>>
```

---

## 4. Verification Instructions

To verify that these changes are correct, perform the following steps after applying the changes:

1. **Verify Python Environment**:
   Ensure you are in the correct backend virtual environment:
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   ```

2. **Run a Dry-Run/Test of the Model Construction**:
   Construct the model from a Python shell or mini-script to ensure the layer order and regularizers are correctly instantiated:
   ```python
   from ml.cnn.efficientnet_backbone import build_skin_tone_classifier
   model = build_skin_tone_classifier(num_classes=3)
   model.summary()
   ```
   **Pass Condition**: 
   - Under the custom head layers, check that the output matches:
     - `head_dense` (Dense, Output shape: `(None, 256)`, Activation: `linear`, Regularizer: `L2`)
     - `head_bn` (BatchNormalization)
     - `head_activation` (Activation layer, Activation: `relu`)
     - `head_dropout` (Dropout)
     - `skin_tone_output` (Dense, Output shape: `(None, 3)`, Activation: `softmax`)

3. **Verify train_cnn.py Execution**:
   Run the training script (can be done with minimal epochs or mock directory check):
   ```powershell
   python ml/cnn/train_cnn.py
   ```
   **Pass Condition**:
   - The script logs the detected class names and class counts with weights (e.g. `Class 0 (dark): 120 samples, weight: 1.1000`).
   - The dataset structure caches successfully, and training commences without error using the specified learning rate `1e-4` and class weights.
