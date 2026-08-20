# Handoff Report: Milestone 1 (CNN & Backbone Fixes)

This report details the findings, logic, and proposals for resolving the bugs identified in Milestone 1.

---

## 1. Observation

Direct observations made in the codebase:

### Bug #2: Data Augmentation
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
* **Observation**: Lines 63-65 define the cache and prefetch pipeline:
  ```python
  # Optimasi kecepatan baca data (Prefetching)
  AUTOTUNE = tf.data.AUTOTUNE
  train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
  valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
  ```
  There is no preprocessing/augmentation layer applied to the training dataset.

### Bug #8: Layer Order
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py`
* **Observation**: Lines 46-48 construct the classification head:
  ```python
  x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
  x = keras.layers.Dropout(0.4, name="head_dropout")(x)
  x = keras.layers.BatchNormalization(name="head_bn")(x)
  ```
  The order is: Dense (ReLU activation) -> Dropout -> BatchNormalization.

### Bug #13: Class Weights
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
* **Observation**: Lines 105-110 contain the training initiation:
  ```python
  history = model.fit(
      train_dataset,
      validation_data=valid_dataset,
      epochs=EPOCHS,
      callbacks=[checkpoint, early_stopping]
  )
  ```
  No `class_weight` parameter is supplied to `model.fit()`.

### Bug #15: Learning Rate and Regularization
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\train_cnn.py`
* **Observation**: Line 75 sets the learning rate of the optimizer:
  ```python
  optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
  ```
* **File**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\efficientnet_backbone.py`
* **Observation**: Line 46 defines the Dense layer without any `kernel_regularizer`:
  ```python
  x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
  ```

---

## 2. Logic Chain

1. **Bug #2 Solution**: Because there is no data augmentation, training is vulnerable to overfitting. A safe augmentation pipeline (horizontal flip, random brightness/contrast 20%, rotation 10 degrees) can be implemented via standard Keras preprocessing layers:
   ```python
   tf.keras.layers.RandomFlip("horizontal")
   tf.keras.layers.RandomRotation(10/360.0)
   tf.keras.layers.RandomBrightness(0.2)
   tf.keras.layers.RandomContrast(0.2)
   ```
   To avoid caching static/augmented tensors (which destroys variation), the `map()` of this augmentation sequence must be placed *after* the `.cache()` call on the dataset, ensuring different random variations are computed on every epoch.

2. **Bug #8 Solution**: In modern deep learning practice, Batch Normalization is best placed *before* the activation function (to normalize inputs to the non-linearity) and *before* Dropout (since Dropout scales/disrupts the inputs, which might skew BN's moving stats if BN is after Dropout). Therefore, the correct dense head order is:
   `Dense (linear/activation=None)` $\rightarrow$ `BatchNormalization` $\rightarrow$ `Activation (relu)` $\rightarrow$ `Dropout`.

3. **Bug #13 Solution**: In skin tone classification, datasets can be unbalanced (e.g. different number of images per skin tone category). Class weights can be computed dynamically from the training directory folders using:
   $$\text{weight}_c = \frac{\text{total\_samples}}{N_{\text{classes}} \times \text{count}_c}$$
   This can be calculated programmatically using Python's `os.listdir()` to count the files in each class subdirectory under `TRAIN_DIR` and then passing it as a dictionary to `model.fit(..., class_weight=class_weights)`.

4. **Bug #15 Solution**: A learning rate of `0.001` (1e-3) is too high when training with a pretrained backbone, which can cause representation collapse or unstable loss. Reducing the learning rate to `1e-4` (0.0001) is standard. Furthermore, regularizing the weights of the Dense projection layer helps avoid overfitting, which is achieved by passing `kernel_regularizer=keras.regularizers.L2(1e-4)` to `head_dense`.

---

## 3. Caveats

- **TensorFlow / Keras Version compatibility**: `tf.keras.layers.RandomBrightness` and `tf.keras.layers.RandomContrast` were introduced in TensorFlow 2.9. If an older version of TensorFlow is used, these layers will raise an AttributeError. In that case, alternative experimental layers (`tf.keras.layers.experimental.preprocessing`) or standard tf.image transformations must be mapped.
- **Verification environment**: The project lacks built-in unit tests for CNN training. Verification relies on importing the model builder and printing model layers, or running a mock training run.

---

## 4. Conclusion

The identified bugs are confirmed to be present. The proposed modifications to `train_cnn.py` and `efficientnet_backbone.py` will:
1. Safely augment the training dataset dynamically.
2. Structure the Dense head layer ordering correctly to standard specifications: `Dense -> BN -> Relu Activation -> Dropout`.
3. Account for class imbalance dynamically during training.
4. Scale down learning rate to `1e-4` and add L2 kernel regularization to prevent overfitting.

All changes are fully documented in `analysis.md`.

---

## 5. Verification Method

To verify the fixes:
1. **Model Architecture Order and Regularization**:
   Instantiate the model and run `model.summary()` to inspect the layer order:
   ```python
   from ml.cnn.efficientnet_backbone import build_skin_tone_classifier
   model = build_skin_tone_classifier(num_classes=3)
   model.summary()
   ```
   Check that `head_dense` has an L2 regularizer, followed by `head_bn` (BatchNormalization), `head_activation` (Activation relu), and `head_dropout` (Dropout).
2. **Dynamic Augmentation & Class Weights**:
   Launch the training script:
   ```powershell
   python ml/cnn/train_cnn.py
   ```
   Check that the console logs print the class weights dictionary and that training initializes without errors.
