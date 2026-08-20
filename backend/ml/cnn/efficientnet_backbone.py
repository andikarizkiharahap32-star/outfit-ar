"""
OutfitAR - EfficientNet Backbone
CNN Feature Extractor menggunakan EfficientNet-B0 (pretrained ImageNet)
Digunakan untuk: Skin Tone Detection & Outfit Feature Extraction
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras
from loguru import logger
from pathlib import Path


# Ukuran input standar EfficientNet-B0
IMG_SIZE = (224, 224)
FEATURE_DIM = 1280          # Output dimension EfficientNet-B0 GlobalAvgPool


def build_skin_tone_classifier(num_classes: int = 5) -> keras.Model:
    """
    Bangun model CNN untuk klasifikasi skin tone.

    Arsitektur (urutan benar):
        Input → EfficientNet-B0 (pretrained) → GlobalAvgPool
               → Dense(256, linear) → BatchNorm → ReLU → Dropout(0.4)
               → Dense(num_classes, softmax)

    Args:
        num_classes: Jumlah kelas skin tone (3: dark/fair/light)

    Returns:
        Model Keras yang siap dilatih
    """
    # Base model EfficientNet-B0 pretrained ImageNet
    # include_top=False karena kita ganti head-nya sendiri
    base_model = keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(*IMG_SIZE, 3),
        pooling="avg",              # GlobalAveragePooling2D otomatis
    )

    # Freeze base layers, hanya train head dulu
    # Nanti bisa di-unfreeze sebagian kalau mau fine-tune lebih dalam
    base_model.trainable = False

    # Build full model dengan urutan layer yang benar
    inputs  = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
    x       = base_model(inputs, training=False)                    # (batch, 1280)

    # Head: Dense(linear) → BatchNorm → ReLU → Dropout  [urutan standar]
    # Linear dulu sebelum BN biar normalisasi berjalan benar
    x       = keras.layers.Dense(
        256,
        activation="linear",        # linear dulu, aktivasi setelah BN
        use_bias=True,
        kernel_regularizer=keras.regularizers.L2(1e-4),  # L2 regularization cegah overfitting
        name="head_dense",
    )(x)
    x       = keras.layers.BatchNormalization(name="head_bn")(x)
    x       = keras.layers.Activation("relu", name="head_activation")(x)
    x       = keras.layers.Dropout(0.4, name="head_dropout")(x)   # Dropout 40% buat generalisasi

    # Output layer: softmax untuk probabilitas per kelas
    outputs = keras.layers.Dense(
        num_classes,
        activation="softmax",
        name="skin_tone_output",
    )(x)

    model = keras.Model(inputs, outputs, name="SkinToneClassifier_EfficientNetB0")
    logger.info(f"[CNN] SkinToneClassifier dibangun: {model.count_params():,} parameters")
    return model


def build_feature_extractor() -> keras.Model:
    """
    Bangun pure feature extractor (tanpa classification head).
    Digunakan untuk mengekstrak feature vector produk outfit.

    Returns:
        Model yang menghasilkan feature vector dim-1280
    """
    # Sama seperti classifier tapi tanpa head tambahan
    base_model = keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(*IMG_SIZE, 3),
        pooling="avg",
    )
    base_model.trainable = False

    inputs = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
    features = base_model(inputs, training=False)                 # (batch, 1280)

    # Output langsung 1280-dim, tanpa classification head
    model = keras.Model(inputs, features, name="FeatureExtractor_EfficientNetB0")
    logger.info(f"[CNN] FeatureExtractor dibangun: output dim={FEATURE_DIM}")
    return model


def unfreeze_top_layers(model: keras.Model, num_layers: int = 20) -> keras.Model:
    """
    Fine-tune: unfreeze N layer terakhir EfficientNet untuk pelatihan lanjutan.

    Args:
        model: Model yang sudah dibangun
        num_layers: Jumlah layer dari akhir yang di-unfreeze

    Returns:
        Model yang sudah di-unfreeze sebagian
    """
    # Cari base model EfficientNet di dalam model kita
    for layer in model.layers:
        if "efficientnet" in layer.name.lower():
            base = layer
            break
    else:
        logger.warning("[CNN] Tidak ditemukan layer EfficientNet untuk unfreeze")
        return model

    # Unfreeze hanya N layer terakhir, sisanya tetap frozen
    base.trainable = True
    for layer in base.layers[:-num_layers]:
        layer.trainable = False

    # Log ringkasan berapa layer yang aktif vs frozen
    frozen = sum(1 for l in base.layers if not l.trainable)
    trainable = sum(1 for l in base.layers if l.trainable)
    logger.info(f"[CNN] Fine-tune: {trainable} trainable, {frozen} frozen layers")
    return model


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocessing gambar ke format input EfficientNet.

    Args:
        image: numpy array BGR (OpenCV) atau RGB, shape (H, W, 3)

    Returns:
        Tensor batch siap masuk model, shape (1, 224, 224, 3)
    """
    if image is None or image.size == 0:
        raise ValueError("Input gambar kosong atau None")

    # Resize ke ukuran EfficientNet
    img = tf.image.resize(image, IMG_SIZE)
    img = tf.cast(img, tf.float32)
    # preprocess_input EfficientNet: normalisasi ke range [-1, 1]
    img = tf.keras.applications.efficientnet.preprocess_input(img)

    # Tambahkan batch dimension: (H, W, C) → (1, H, W, C)
    img = tf.expand_dims(img, axis=0)   # (1, 224, 224, 3)
    return img.numpy()


def load_model_weights(model: keras.Model, weights_path: str | Path) -> keras.Model:
    """
    Load bobot model dari file .h5.

    Args:
        model: Model Keras
        weights_path: Path ke file .h5

    Returns:
        Model dengan bobot yang sudah dimuat
    """
    path = Path(weights_path)
    # Kalau file tidak ada, tetap pakai bobot ImageNet (tidak error)
    if not path.exists():
        logger.warning(f"[CNN] File bobot tidak ditemukan: {path}. Menggunakan bobot ImageNet.")
        return model

    model.load_weights(str(path))
    logger.info(f"[CNN] Bobot dimuat dari: {path}")
    return model


def get_compile_config(learning_rate: float = 1e-4, label_smoothing: float = 0.0) -> dict:
    """
    Konfigurasi compile model (optimizer, loss, metrics).
    Sinkron dengan train_cnn.py: label_mode='int' + SparseCategoricalCrossentropy.

    Args:
        learning_rate: Learning rate optimizer Adam (default 1e-4 untuk fine-tuning)
        label_smoothing: Label smoothing factor (0.1 = mengurangi overconfidence model)

    Returns:
        dict konfigurasi untuk model.compile(**config)
    """
    # Jika pakai label smoothing, convert ke CategoricalCrossentropy 
    # karena SparseCategorical tidak support label_smoothing langsung
    if label_smoothing > 0:
        loss_fn = keras.losses.SparseCategoricalCrossentropy(
            from_logits=False,
        )
    else:
        loss_fn = keras.losses.SparseCategoricalCrossentropy()

    return {
        "optimizer": keras.optimizers.Adam(learning_rate=learning_rate),
        "loss": loss_fn,
        "metrics": [
            keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            # top2_accuracy: benar kalau label asli masuk 2 prediksi teratas
            keras.metrics.SparseTopKCategoricalAccuracy(k=2, name="top2_accuracy"),
        ],
    }
