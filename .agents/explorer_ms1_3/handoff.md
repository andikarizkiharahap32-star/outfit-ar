# Handoff Report — Explorer Milestone 1 (CNN & Backbone Fixes)

This handoff report summarizes the analysis and recommended fixes for Bug #2, Bug #8, Bug #13, and Bug #15.

---

## 1. Observation

### Observation 1: Data Augmentation
*   **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
*   **Lines 41-47**:
    ```python
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR,
        shuffle=True,
        batch_size=BATCH_SIZE,
        image_size=IMG_SIZE,
        label_mode='categorical' # Memakai One-Hot Encoding
    )
    ```
*   **Lines 63-65**:
    ```python
    # Optimasi kecepatan baca data (Prefetching)
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    ```
*   **Verbatim Observation**: No data augmentation pipeline (such as RandomFlip, RandomRotation, etc.) exists in `train_cnn.py` or is applied to `train_dataset`.

### Observation 2: Dense Head Layer Order
*   **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py`
*   **Lines 46-48**:
    ```python
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    ```
*   **Verbatim Observation**: The layers are defined with ReLU activation inside `Dense`, followed by `Dropout` and then `BatchNormalization`.

### Observation 3: Class Weights Calculation & Usage
*   **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
*   **Lines 105-110**:
    ```python
    history = model.fit(
        train_dataset,
        validation_data=valid_dataset,
        epochs=EPOCHS,
        callbacks=[checkpoint, early_stopping]
    )
    ```
*   **Verbatim Observation**: There is no calculation of class weights or assignment of `class_weight` to `model.fit()`.

### Observation 4: Learning Rate & Regularization
*   **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py` (Line 75):
    ```python
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    ```
*   **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py` (Line 46):
    ```python
    x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
    ```
*   **Verbatim Observation**: The learning rate is set to `0.001` and the `head_dense` layer does not specify any `kernel_regularizer`.

---

## 2. Logic Chain

1.  **Bug #2 (Data Augmentation)**:
    *   *Premise*: Deep learning model training on smaller/imbalanced datasets is highly prone to overfitting. Data augmentation provides regularization.
    *   *Observation 1* shows that no data augmentation is performed.
    *   *Deduction*: Adding data augmentation via `tf.keras.Sequential` containing `RandomFlip("horizontal")`, `RandomRotation(factor=10/360)`, `RandomBrightness(factor=0.20)`, and `RandomContrast(factor=0.20)` is required. Applying `.map()` after `.cache()` but before `.prefetch()` ensures the data is augmented dynamically in memory per epoch.
2.  **Bug #8 (Dense Head Layer Order)**:
    *   *Premise*: Batch Normalization performs best when normalizing linear activations (pre-activation) or at least before dropout is applied, to avoid computing statistics on sparse (zeroed-out) representations.
    *   *Observation 2* shows `Dense(relu) -> Dropout -> BN`.
    *   *Deduction*: We must change the layer definition so that the Dense layer output has no activation (linear), followed by Batch Normalization, then an explicit ReLU Activation, and finally Dropout.
3.  **Bug #13 (Class Weights)**:
    *   *Premise*: Imbalanced datasets lead to class bias, which is countered by weighting the loss of each class inversely proportional to its frequency.
    *   *Observation 3* shows no class weights are passed to `model.fit()`.
    *   *Deduction*: We must count files within each subfolder of `TRAIN_DIR` for each class in `class_names` (to avoid loading all image files into memory), compute balanced class weights using `total_samples / (num_classes * class_count)`, and pass this dictionary to the `class_weight` parameter in `model.fit()`.
4.  **Bug #15 (Learning Rate & Regularization)**:
    *   *Premise*: In transfer learning with a pre-trained feature extractor, a high learning rate (like 1e-3) can overwrite pre-trained weights or cause unstable convergence, and lack of regularization leads to overfitting in the classifier head.
    *   *Observation 4* shows learning rate is `0.001` and no kernel regularization is used.
    *   *Deduction*: Reducing the learning rate to `1e-4` and adding `kernel_regularizer=keras.regularizers.L2(1e-4)` to the dense classifier head will mitigate these risks.

---

## 3. Caveats

*   **TensorFlow Version Compatibility**: The proposed data augmentation layers (e.g. `RandomBrightness`, `RandomContrast`) are standard in TensorFlow 2.16.2 / Keras 3.3.3 (the project dependencies). If running in a deprecated TensorFlow environment, alternate functions might be required.
*   **File Counting assumption**: The file-counting logic assumes that the subdirectories of `TRAIN_DIR` contain only the dataset image files and that class names match folder names. Standard image file extension filters (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.webp`) have been implemented to ensure robustness against hidden files or system metadata.

---

## 4. Conclusion

The current codebase contains several classical CNN training and architecture issues:
1.  Absence of data augmentation.
2.  Incorrect ordering of Dense Head layers (BN after Dropout and Activation).
3.  Absence of class weights to handle imbalanced training.
4.  Overly high learning rate (1e-3) and lack of L2 regularization in the classifier head.

Implementing the exact modifications proposed in `analysis.md` will resolve all four bugs safely and effectively.

---

## 5. Verification Method

1.  **Architecture Verification**: Run the following command in PowerShell to compile the model structure and verify layer names, orders, and shapes:
    ```powershell
    python -c "from backend.ml.cnn.efficientnet_backbone import build_skin_tone_classifier; model = build_skin_tone_classifier(3); model.summary(); print([layer.name for layer in model.layers])"
    ```
    *   *Expected output order*: `['input_image', 'efficientnet_preprocessor', 'efficientnetb0', 'head_dense', 'head_bn', 'head_activation', 'head_dropout', 'skin_tone_output']`.
    *   *L2 Regularization verification*: `model.get_layer('head_dense').losses` should contain the L2 regularization loss tensor.
2.  **Dataset Pipeline Verification**: Run the training script directly to verify the dataset loads, class weights are printed, and training starts without keras serialization errors:
    ```powershell
    python backend/ml/cnn/train_cnn.py
    ```
    *   *Expected behavior*: Output log prints calculated class weights for each label class, starts epoch 1/20, shows augmentation mapping executing, and training runs successfully.
