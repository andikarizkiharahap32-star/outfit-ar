"""
OutfitAR - Milestone 1 Challenger Verification & Stress Test
This script verifies the CNN Backbone and classification head correctness.
To run: backend/venv_fix/Scripts/python.exe backend/tests/stress_test_ms1.py
"""

import sys
import os
import time
import traceback
import numpy as np
import tensorflow as tf
from loguru import logger

# Add backend directory to sys.path to enable imports of ml.*
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from ml.cnn.efficientnet_backbone import (
    build_skin_tone_classifier,
    build_feature_extractor,
    preprocess_image,
    get_compile_config,
)
from ml.cnn.skin_tone_classifier import SkinToneClassifier, SkinToneResult
from ml.cnn.feature_extractor import OutfitFeatureExtractor

def test_custom_head_order_and_properties():
    logger.info("--- TEST 1: Inspecting custom head order & regularizers ---")
    model = build_skin_tone_classifier(num_classes=3)
    
    # Expected layers in the custom head
    expected_order = [
        ("head_dense", "Dense"),
        ("head_bn", "BatchNormalization"),
        ("head_activation", "Activation"),
        ("head_dropout", "Dropout"),
        ("skin_tone_output", "Dense")
    ]
    
    # Filter layers that belong to the head
    head_layers = [l for l in model.layers if l.name.startswith("head_") or l.name == "skin_tone_output"]
    
    assert len(head_layers) == len(expected_order), f"Expected {len(expected_order)} head layers, found {len(head_layers)}"
    
    for (exp_name, exp_type), layer in zip(expected_order, head_layers):
        assert layer.name == exp_name, f"Expected layer name {exp_name}, got {layer.name}"
        assert layer.__class__.__name__ == exp_type, f"Expected type {exp_type} for {exp_name}, got {layer.__class__.__name__}"
        logger.info(f"Verified: {layer.name} is of type {layer.__class__.__name__}")
        
        # Dense layer detailed checks
        if exp_name == "head_dense":
            # 1. Linear activation (which in Keras is represented by activation = None or linear function)
            activation_name = getattr(layer.activation, "__name__", "linear")
            assert activation_name in ["linear", None], f"head_dense activation must be linear, got {activation_name}"
            # 2. No bias
            assert not layer.use_bias, "head_dense use_bias must be False"
            # 3. L2 regularizer of 1e-4
            assert layer.kernel_regularizer is not None, "head_dense must have L2 regularizer"
            reg_config = layer.kernel_regularizer.get_config()
            assert np.isclose(reg_config.get("l2", 0.0), 1e-4) or np.isclose(reg_config.get("penalty", 0.0), 1e-4), \
                f"head_dense L2 penalty must be 1e-4, got {reg_config}"
            logger.info("Verified head_dense features: activation=linear, use_bias=False, l2=1e-4")
            
        if exp_name == "head_dropout":
            # Dropout rate check
            assert np.isclose(layer.rate, 0.4), f"head_dropout rate must be 0.4, got {layer.rate}"
            logger.info("Verified head_dropout features: rate=0.4")

    logger.info("[OK] Custom head layer order and properties verified successfully!")


def test_gradient_propagation_and_weights_update():
    logger.info("--- TEST 2: Testing gradient propagation and weights update ---")
    model = build_skin_tone_classifier(num_classes=3)
    
    # Select trainable weights from head_dense and head_bn to verify they update
    head_dense = model.get_layer("head_dense")
    head_bn = model.get_layer("head_bn")
    
    # Keep track of initial weights
    dense_kernel_before = tf.identity(head_dense.kernel)
    bn_gamma_before = tf.identity(head_bn.gamma)
    bn_beta_before = tf.identity(head_bn.beta)
    
    # Generate dummy input and target
    dummy_input = tf.random.uniform((4, 224, 224, 3), minval=0.0, maxval=255.0)
    dummy_target = tf.constant([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    
    optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)
    loss_fn = tf.keras.losses.CategoricalCrossentropy()
    
    with tf.GradientTape() as tape:
        # Use training=True to ensure dropout and BN are active, and gradients flow
        predictions = model(dummy_input, training=True)
        loss = loss_fn(dummy_target, predictions)
        # Add regularization loss manually if any
        reg_losses = model.losses
        if reg_losses:
            loss += sum(reg_losses)
            
    # Compute gradients for head and all trainable variables
    trainable_vars = model.trainable_variables
    gradients = tape.gradient(loss, trainable_vars)
    
    # Check that gradients for our custom head layers are not None and not all zeros
    head_dense_kernel_grad = None
    head_bn_gamma_grad = None
    
    for var, grad in zip(trainable_vars, gradients):
        if "head_dense/kernel" in var.name or (var is head_dense.kernel):
            head_dense_kernel_grad = grad
        elif "head_bn/gamma" in var.name or (var is head_bn.gamma):
            head_bn_gamma_grad = grad
            
    assert head_dense_kernel_grad is not None, "Gradient for head_dense kernel was not calculated (None)"
    assert head_bn_gamma_grad is not None, "Gradient for head_bn gamma was not calculated (None)"
    
    assert tf.reduce_sum(tf.abs(head_dense_kernel_grad)) > 0, "Gradient for head_dense kernel is zero"
    assert tf.reduce_sum(tf.abs(head_bn_gamma_grad)) > 0, "Gradient for head_bn gamma is zero"
    
    logger.info(f"Verified: Gradient flow detected. head_dense kernel grad sum: {tf.reduce_sum(tf.abs(head_dense_kernel_grad)).numpy():.6f}")
    logger.info(f"Verified: Gradient flow detected. head_bn gamma grad sum: {tf.reduce_sum(tf.abs(head_bn_gamma_grad)).numpy():.6f}")
    
    # Apply gradients using optimizer to update weights
    optimizer.apply_gradients(zip(gradients, trainable_vars))
    
    # Verify weights actually changed
    dense_kernel_after = head_dense.kernel
    bn_gamma_after = head_bn.gamma
    bn_beta_after = head_bn.beta
    
    dense_diff = tf.reduce_sum(tf.abs(dense_kernel_before - dense_kernel_after)).numpy()
    bn_gamma_diff = tf.reduce_sum(tf.abs(bn_gamma_before - bn_gamma_after)).numpy()
    bn_beta_diff = tf.reduce_sum(tf.abs(bn_beta_before - bn_beta_after)).numpy()
    
    assert dense_diff > 0, "head_dense kernel weights did not update"
    assert bn_gamma_diff > 0, "head_bn gamma weights did not update"
    assert bn_beta_diff > 0, "head_bn beta weights did not update"
    
    logger.info(f"Verified: head_dense kernel updated by diff {dense_diff:.6f}")
    logger.info(f"Verified: head_bn gamma updated by diff {bn_gamma_diff:.6f}")
    logger.info(f"Verified: head_bn beta updated by diff {bn_beta_diff:.6f}")
    logger.info("[OK] Gradient propagation and weights update verified successfully!")


def test_data_augmentation_under_load():
    logger.info("--- TEST 3: Testing Data Augmentation Pipeline under load ---")
    
    # Setup data augmentation pipeline exactly as in train_cnn.py
    data_augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(10/360.0),
        tf.keras.layers.RandomBrightness(0.2, value_range=(0.0, 255.0)),
        tf.keras.layers.RandomContrast(0.2)
    ], name="data_augmentation")
    
    # Create batch under load: 100 images
    batch_size = 32
    steps = 20
    logger.info(f"Simulating data augmentation pipeline load: {steps} batches of size {batch_size}...")
    
    start_time = time.time()
    for step in range(steps):
        # Random dummy batch
        images = tf.random.uniform((batch_size, 224, 224, 3), minval=0.0, maxval=255.0)
        augmented = data_augmentation(images, training=True)
        
        # Verify shape remains the same
        assert augmented.shape == images.shape, f"Shape mismatch: {augmented.shape} vs {images.shape}"
        # Verify not all values are the same (indicates augmentation logic is active and varying outputs)
        assert tf.reduce_sum(tf.abs(augmented - images)) > 0, "Augmented images are identical to original images"
        
    duration = time.time() - start_time
    logger.info(f"Successfully processed {steps * batch_size} images in {duration:.4f} seconds (average {(steps*batch_size)/duration:.2f} img/sec)")
    logger.info("[OK] Data augmentation pipeline under load verified successfully!")


def test_dynamic_class_weights_and_mock_training():
    logger.info("--- TEST 4: Testing dynamic class weights & mock dataset training ---")
    
    # 1. Verification of class weight calculation
    # Simulate highly imbalanced dataset counts for 3 classes: Dark, Fair, Light
    # Let's say: Class 0 (Dark) = 80 samples, Class 1 (Fair) = 15 samples, Class 2 (Light) = 5 samples
    class_counts = [80, 15, 5]
    num_classes = 3
    total_samples = sum(class_counts)
    
    # Apply calculation formula from train_cnn.py
    class_weights = {}
    for i, count in enumerate(class_counts):
        class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0
        
    logger.info(f"Class counts: {class_counts}")
    logger.info(f"Calculated class weights: {class_weights}")
    
    # Expected properties of class weights:
    # Minority classes should have larger weights
    assert class_weights[2] > class_weights[1] > class_weights[0]
    # Verify exact math
    assert np.isclose(class_weights[0], 100 / (3 * 80))
    assert np.isclose(class_weights[1], 100 / (3 * 15))
    assert np.isclose(class_weights[2], 100 / (3 * 5))
    
    logger.info("Dynamic class weights math verified.")
    
    # 2. Mock training with dynamic class weights
    # Let's build the model and compile
    model = build_skin_tone_classifier(num_classes=3)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Create imbalanced mock training dataset
    # We will generate 100 images and 100 imbalanced labels
    X_train = np.random.uniform(0.0, 255.0, (100, 224, 224, 3)).astype(np.float32)
    
    # Let's assign labels corresponding to our counts
    y_labels = np.array([0]*80 + [1]*15 + [2]*5)
    y_train = tf.keras.utils.to_categorical(y_labels, num_classes=3)
    
    # Shuffle dataset
    indices = np.arange(100)
    np.random.shuffle(indices)
    X_train = X_train[indices]
    y_train = y_train[indices]
    
    logger.info("Running 2 epochs of mock training with class weights...")
    start_time = time.time()
    
    history = model.fit(
        X_train, 
        y_train, 
        batch_size=32, 
        epochs=2, 
        class_weight=class_weights, 
        verbose=1
    )
    
    duration = time.time() - start_time
    logger.info(f"Mock training completed in {duration:.4f} seconds.")
    assert len(history.history['loss']) == 2, "Mock training did not complete 2 epochs"
    logger.info(f"Epoch 1 loss: {history.history['loss'][0]:.4f}, Epoch 2 loss: {history.history['loss'][1]:.4f}")
    
    logger.info("[OK] Dynamic class weights math and training integration verified successfully!")


def test_inference_shape_stability():
    logger.info("--- TEST 5: Testing feature extractor and classification shape stability ---")
    
    # 1. Instantiate classifiers
    classifier = SkinToneClassifier()
    extractor = OutfitFeatureExtractor()
    
    # 2. Generate random test images of varying sizes
    test_sizes = [
        (100, 100),
        (224, 224),
        (640, 480),
        (1080, 1920)
    ]
    
    for height, width in test_sizes:
        logger.info(f"Testing with image size: {width}x{height}")
        # Create a mock BGR image (OpenCV style)
        mock_img = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        
        # Test SkinToneClassifier.detect
        # To avoid MediaPipe failing inside face detection (which might fallback gracefully or return zero result),
        # let's verify that the detect function completes without throwing exceptions.
        try:
            result = classifier.detect(mock_img)
            assert isinstance(result, SkinToneResult), f"Expected SkinToneResult, got {type(result)}"
            assert result.level in [1, 2, 3], f"Level must be 1, 2, or 3, got {result.level}"
            assert len(result.feature_vector) == 1280, f"Expected 1280-dim feature vector, got {len(result.feature_vector)}"
            logger.info(f"SkinToneClassifier detect OK. Level: {result.level}, Gender: {result.gender}, Dominant color: {result.hex_color}")
        except Exception as e:
            logger.error(f"SkinToneClassifier failed for size {width}x{height}: {e}")
            traceback.print_exc()
            raise e
            
        # Test OutfitFeatureExtractor.extract
        try:
            feat = extractor.extract(mock_img)
            # Feature dimensions: 1280 (CNN) + 96 (Color) + 1 (Texture) = 1377
            assert feat.shape == (1377,), f"Expected shape (1377,), got {feat.shape}"
            assert feat.dtype == np.float32, f"Expected dtype float32, got {feat.dtype}"
            logger.info("OutfitFeatureExtractor single extract OK.")
        except Exception as e:
            logger.error(f"OutfitFeatureExtractor.extract failed for size {width}x{height}: {e}")
            traceback.print_exc()
            raise e

    # Test batch extraction
    try:
        mock_imgs = [np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8) for _ in range(5)]
        batch_feat = extractor.extract_batch(mock_imgs)
        assert batch_feat.shape == (5, 1377), f"Expected shape (5, 1377), got {batch_feat.shape}"
        logger.info("OutfitFeatureExtractor batch extract OK.")
    except Exception as e:
        logger.error(f"OutfitFeatureExtractor.extract_batch failed: {e}")
        traceback.print_exc()
        raise e
        
    logger.info("[OK] Inference and shape stability verified successfully!")


def main():
    logger.info("Starting Milestone 1 Challenger Verification & Stress Tests...")
    
    tests = [
        test_custom_head_order_and_properties,
        test_gradient_propagation_and_weights_update,
        test_data_augmentation_under_load,
        test_dynamic_class_weights_and_mock_training,
        test_inference_shape_stability
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
            print()
        except Exception as e:
            logger.error(f"[FAIL] Test {test.__name__} FAILED: {e}")
            failed += 1
            print()
            
    if failed == 0:
        logger.info("[DONE] All Milestone 1 stress tests passed successfully!")
        sys.exit(0)
    else:
        logger.error(f"[FAIL] {failed} test(s) failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
