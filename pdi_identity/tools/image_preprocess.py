# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
"""Preprocesamiento de imágenes de documentos para mejorar el OCR.

Módulo de Python puro: solo depende de Pillow, no de Odoo.
"""
import io

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

# Una foto de celular puede pesar decenas de megapíxeles: se limita para no
# agotar la memoria del servidor.
MAX_SIDE = 4000
# Tesseract rinde mejor con texto de al menos ~30 px de alto; una INE
# fotografiada a baja resolución se amplía hasta este ancho.
MIN_WIDTH = 1600


class ImageError(ValueError):
    """La imagen no se pudo abrir o no es un formato soportado."""


def open_image(data):
    """Abre una imagen desde ``bytes`` y la devuelve ya cargada en memoria."""
    if not data:
        raise ImageError("No se recibió ninguna imagen.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("El archivo no es una imagen válida.") from exc
    return image


def otsu_threshold(image):
    """Umbral de Otsu (0-255) para una imagen en escala de grises."""
    histogram = image.histogram()
    total = sum(histogram)
    sum_all = sum(i * count for i, count in enumerate(histogram))
    sum_bg = weight_bg = 0
    best_variance = -1.0
    threshold = 127
    for level in range(256):
        weight_bg += histogram[level]
        if not weight_bg:
            continue
        weight_fg = total - weight_bg
        if not weight_fg:
            break
        sum_bg += level * histogram[level]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = level
    return threshold


def preprocess(data, min_width=MIN_WIDTH, binarize=False):
    """Prepara la imagen de un documento para el OCR.

    Pasos: orientación EXIF, escala de grises, límite de tamaño, ampliación a
    un ancho mínimo, autocontraste, nitidez y, opcionalmente, binarización.

    :param bytes data: contenido del archivo de imagen.
    :param int min_width: ancho mínimo en píxeles; si es menor, se amplía.
    :param bool binarize: aplicar umbral de Otsu (blanco y negro).
    :return: imagen ``PIL.Image`` en modo ``L`` (escala de grises).
    """
    image = ImageOps.exif_transpose(open_image(data))
    image = image.convert("L")

    longest = max(image.size)
    if longest > MAX_SIDE:
        ratio = MAX_SIDE / longest
        image = image.resize(
            (round(image.width * ratio), round(image.height * ratio)),
            Image.LANCZOS,
        )
    if image.width < min_width:
        ratio = min_width / image.width
        image = image.resize(
            (min_width, round(image.height * ratio)), Image.LANCZOS
        )

    image = ImageOps.autocontrast(image, cutoff=2)
    image = image.filter(ImageFilter.SHARPEN)
    if binarize:
        threshold = otsu_threshold(image)
        image = image.point(lambda value: 255 if value > threshold else 0)
    return image


def to_png_bytes(image):
    """Serializa una imagen a PNG (útil para guardarla o depurar)."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
