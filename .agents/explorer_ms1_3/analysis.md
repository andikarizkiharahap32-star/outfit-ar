# Exploration Report — CNN & Backbone Fixes

This report contains findings and proposed changes for Bug #2, Bug #8, Bug #13, and Bug #15 in `backend/ml/cnn/train_cnn.py` and `backend/ml/cnn/efficientnet_backbone.py`.

---

## 1. Findings & Observations

### Bug #2: Data Augmentation in CNN Training
*   **File**: `backend/ml/cnn/train_cnn.py`
*   **Current Code (Lines 41-65)**:
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
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    ```
*   **Observation**: No data augmentation is performed. The dataset is cached and prefetched directly, exposing the model to potential overfitting and poor generalization.
*   **Analysis**: We need to introduce a safe, non-aggressive data augmentation pipeline (horizontal flip, random brightness/contrast 20%, rotation 10 degrees) on the training dataset. We should apply augmentation **after** `.cache()` and **before** `.prefetch()` to ensure random variations are computed on-the-fly per epoch on cached raw tensors, avoiding caching the same augmented images repeatedly.

### Bug #8: Layer Order in Dense Head
*   **File**: `backend/ml/cnn/efficientnet_backbone.py`
*   **Current Code (Lines 46-48)**:
    ```python
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    ```
*   **Observation**: The current order is `Dense (activation="relu") -> Dropout -> BatchNormalization`.
*   **Analysis**: This is suboptimal. Applying Batch Normalization after Dropout and after Activation means BN operates on rectified (all non-negative) and zeroed-out features. The standard, mathematically sound order is:
    `Dense (linear / activation=None) -> BatchNormalization -> Activation (relu) -> Dropout -> Output`.

### Bug #13: Class Weights in CNN Training
*   **File**: `backend/ml/cnn/train_cnn.py`
*   **Current Code (Lines 105-110)**:
    ```python
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping]
    )
    ```
*   **Observation**: Class weights are not computed or passed to `model.fit()`. If the skin tone dataset is imbalanced, the model will bias towards the majority class.
*   **Analysis**: Class weights should be calculated from class counts. Iterating through the batched training dataset is slow and memory-intensive; instead, we can count the files in each subdirectory of `TRAIN_DIR` corresponding to the classes in `class_names`. Using the balanced class weight formula `total_samples / (num_classes * class_count)`, we can generate the `class_weight` dictionary and pass it to `model.fit()`.

### Bug #15: Learning Rate and Regularization
*   **Files**: `backend/ml/cnn/train_cnn.py` & `backend/ml/cnn/efficientnet_backbone.py`
*   **Current Code**:
    *   **Learning Rate** (`train_cnn.py` Line 75):
        ```python
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001)
        ```
    *   **Regularization** (`efficientnet_backbone.py` Line 46):
        ```python
        x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
        ```
*   **Observation**: The learning rate is set to `0.001` (too high for fine-tuning/transfer learning with pre-trained backbones), and there is no kernel regularization on the Dense head layer.
*   **Analysis**:
    *   The learning rate should be reduced to `1e-4` (`0.0001`) to stabilize training.
    *   `kernel_regularizer=keras.regularizers.L2(1e-4)` must be added to the Dense head layer to prevent overfitting.

---

## 2. Proposed Exact Code Changes

### Proposed Changes for `backend/ml/cnn/train_cnn.py`

#### Modification 1: Data Augmentation & Class Weights (Lines 60-66)
*   **Target Content**:
    ```python
    # Optimasi kecepatan baca data (Prefetching)
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    ```
*   **Replacement Content**:
    ```python
    # ==========================================
    # 2.5 DATA AUGMENTATION & CLASS WEIGHTS (Bug #2 & Bug #13)
    # ==========================================
    # Safe data augmentation strategy (Bug #2)
    # factor=10/360 = 0.0278 for 10 degrees rotation
    data_augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(factor=10/360),
        tf.keras.layers.RandomBrightness(factor=0.20),
        tf.keras.layers.RandomContrast(factor=0.20)
    ], name="data_augmentation")

    # Calculate class weights (Bug #13)
    logger.info("⚖️ Menghitung class weights dari dataset training...")
    class_counts = {}
    total_samples = 0
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')
    
    for class_name in class_names:
        class_path = os.path.join(TRAIN_DIR, class_name)
        if os.path.isdir(class_path):
            count = len([
                f for f in os.listdir(class_path) 
                if f.lower().endswith(image_extensions)
            ])
            class_counts[class_name] = count
            total_samples += count
            logger.info(f"   Kategori '{class_name}': {count} gambar")
            
    class_weights = {}
    for i, class_name in enumerate(class_names):
        count = class_counts.get(class_name, 0)
        class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0
        
    logger.info(f"⚖️ Bobot kelas terhitung: {class_weights}")

    # Optimasi kecepatan baca data (Prefetching & Data Augmentation)
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache()
    # Terapkan augmentasi dinamis per epoch
    train_dataset = train_dataset.map(
        lambda x, y: (data_augmentation(x, training=True), y),
        num_parallel_calls=AUTOTUNE
    )
    train_dataset = train_dataset.prefetch(buffer_size=AUTOTUNE)
    
    valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    ```

#### Modification 2: Learning Rate (Line 75)
*   **Target Content**:
    ```python
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    ```
*   **Replacement Content**:
    ```python
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4), # Bug #15
    ```

#### Modification 3: Passing Class Weights to fit() (Lines 105-110)
*   **Target Content**:
    ```python
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping]
    )
    ```
*   **Replacement Content**:
    ```python
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping],
        class_weight=class_weights # Bug #13
    )
    ```

---

### Proposed Changes for `backend/ml/cnn/efficientnet_backbone.py`

#### Modification 1: Correct Layer Order & L2 Regularization (Lines 46-48)
*   **Target Content**:
    ```python
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    ```
*   **Replacement Content**:
    ```python
    # Dense (linear activation) + L2 Regularization (Bug #15)
    x = keras.layers.Dense(
        256,
        activation=None,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense"
    )(x)
    
    # Batch Normalization (Bug #8)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    
    # Activation (ReLU) (Bug #8)
    x = keras.layers.Activation("relu", name="head_activation")(x)
    
    # Dropout (Bug #8)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    ```

---

## 3. Verification Instructions

After implementing the code changes:
1.  **Environment Check**: Activate the python virtual environment (`.\venv\Scripts\activate`) and verify that TensorFlow and Keras can import:
    ```powershell
    python -c "import tensorflow as tf; import keras; print(tf.__version__, keras.__version__)"
    ```
2.  **Dry Run Model Creation**: Run a sanity check script to verify the backbone model compiles and has the correct layer order and regularization:
    ```powershell
    python -c "from backend.ml.cnn.efficientnet_backbone import build_skin_tone_classifier; model = build_skin_tone_classifier(3); model.summary(); print([l.name for l in model.layers])"
    ```
    *   Verify that `head_dense` does not use activation (`activation=None`), and is followed by `head_bn`, then an activation/ReLU, and then `head_dropout`.
    *   Verify the trainable parameter count is consistent.
3.  **Execute Training**: Start a quick test training process (possibly with a reduced number of epochs or subset of the dataset) to verify that `class_weights` are correctly computed and logged, data augmentation runs without errors, and loss decreases under `learning_rate=1e-4`:
    ```powershell
    python backend/ml/cnn/train_cnn.py
    ```
