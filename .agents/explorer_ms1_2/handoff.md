# Handoff Report

## 1. Observation
I directly inspected the following files in the `C:\Final_outfitAR\outfit-ar` repository:
- `backend/ml/cnn/train_cnn.py`
- `backend/ml/cnn/efficientnet_backbone.py`

Key observations:
1. **No Data Augmentation**: In `backend/ml/cnn/train_cnn.py`, lines 62-65, only prefetching and caching are configured:
   ```python
   # Optimasi kecepatan baca data (Prefetching)
   AUTOTUNE = tf.data.AUTOTUNE
   train_dataset = train_dataset.cache().prefetch(buffer_size=AUTOTUNE)
   valid_dataset = valid_dataset.cache().prefetch(buffer_size=AUTOTUNE)
   ```
2. **Incorrect Layer Order in Dense Head**: In `backend/ml/cnn/efficientnet_backbone.py`, lines 46-48:
   ```python
   x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
   x = keras.layers.Dropout(0.4, name="head_dropout")(x)
   x = keras.layers.BatchNormalization(name="head_bn")(x)
   ```
   No `kernel_regularizer` was defined.
3. **No Class Weights**: In `backend/ml/cnn/train_cnn.py`, lines 105-110, `model.fit()` runs without `class_weight`:
   ```python
   history = model.fit(
       train_dataset,
       validation_data=valid_dataset,
       epochs=EPOCHS,
       callbacks=[checkpoint, early_stopping]
   )
   ```
4. **Incorrect Learning Rate**: In `backend/ml/cnn/train_cnn.py`, lines 74-78, the compile step uses a learning rate of `0.001`:
   ```python
   model.compile(
       optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
       loss='categorical_crossentropy',
       metrics=['accuracy']
   )
   ```

---

## 2. Logic Chain
- **Bug #2**: Since no data augmentation is present, the model is highly prone to overfitting. Introducing a data augmentation layer (`RandomFlip`, `RandomRotation(10.0/360.0)`, `RandomBrightness(0.2, (0, 255))`, `RandomContrast(0.2)`) mapped to `train_dataset` before prefetching dynamically perturbs the training samples.
- **Bug #8 & Bug #15 (Part 1)**: Batch normalization should be applied to the pre-activation outputs of the dense layer to stabilize learning, and dropout should follow the activation function. Therefore, ordering the layers as `Dense(activation=None) -> BatchNormalization -> Activation('relu') -> Dropout` corrects the ordering. Incorporating `kernel_regularizer=keras.regularizers.L2(1e-4)` directly into the `Dense` constructor enforces weight decay.
- **Bug #13**: Calculating class weights from the file counts of each class folder (i.e. `dark`, `fair`, `light`) via $total\_samples / (num\_classes \times count)$ maps directory distribution to loss weights. Passing this mapping as `class_weight` to `model.fit()` compensates for the class imbalance.
- **Bug #15 (Part 2)**: Changing the Adam optimizer's learning rate in `model.compile` from `0.001` to `1e-4` prevents large gradient steps from degrading pretrained EfficientNet-B0 weights during transfer learning.

---

## 3. Caveats
- Checked class names in the actual dataset using Python (`['dark', 'fair', 'light']`). The proposed class weight counting method handles directories dynamically, so it will adapt even if the class structure changes.
- Assumed standard Keras 3 behavior where preprocessing/augmentation layers behave as identity mappings when `training=False` is passed (meaning validation dataset mapping is not strictly required if we set `training=True` in train dataset mapping).

---

## 4. Conclusion
The four bugs can be resolved cleanly with:
- Prefacing dataset training with a mapped Sequential data augmentation layer.
- Changing the Dense head layers sequence in `efficientnet_backbone.py` to: `Dense (linear, L2 regularized)` -> `BatchNormalization` -> `Activation ('relu')` -> `Dropout`.
- Dynamically scanning the class directories in `train_cnn.py` to construct `class_weights` and passing it to `model.fit()`.
- Updating the Adam compile learning rate in `train_cnn.py` to `1e-4`.

---

## 5. Verification Method
- Execute the build command (syntax and startup check):
  ```powershell
  backend\venv\Scripts\python backend\ml\cnn\train_cnn.py
  ```
- To verify the model layer order and regularizer configuration, run:
  ```powershell
  backend\venv\Scripts\python -c "from backend.ml.cnn.efficientnet_backbone import build_skin_tone_classifier; model = build_skin_tone_classifier(3); model.summary()"
  ```
  Ensure that the layer outputs and order match:
  1. `head_dense (Dense)` (kernel_regularizer set to L2)
  2. `head_bn (BatchNormalization)`
  3. `head_activation (Activation)`
  4. `head_dropout (Dropout)`
  5. `skin_tone_output (Dense)`
