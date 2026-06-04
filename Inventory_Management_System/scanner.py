from typing import Optional

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    np = None

try:
    from pyzbar.pyzbar import decode  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    decode = None


def normalize_scanned_value(value) -> str:
    return str(value or "").strip()


def scan_product_id_from_image(image) -> Optional[str]:
    if cv2 is None or decode is None or image is None:
        return None

    detector = cv2.QRCodeDetector()
    try:
        qr_data, _, _ = detector.detectAndDecode(image)
        qr_value = normalize_scanned_value(qr_data)
        if qr_value:
            return qr_value
    except Exception:  # pragma: no cover - detector fallback only
        pass

    grayscale_image = image
    if len(getattr(image, "shape", [])) == 3:
        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    for barcode in decode(grayscale_image):
        data = barcode.data.decode("utf-8", errors="ignore").strip()
        if data:
            return data
    return None


def scan_product_id_from_bytes(image_bytes: bytes) -> Optional[str]:
    if cv2 is None or np is None or not image_bytes:
        return None

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        return None

    return scan_product_id_from_image(image)


def scan_product_id_from_file(file_path: str) -> Optional[str]:
    if cv2 is None or not file_path:
        return None

    image = cv2.imread(file_path)
    if image is None:
        return None

    return scan_product_id_from_image(image)


def scan_product_id_from_camera(camera_index: int = 0, max_frames: int = 120) -> Optional[str]:
    if cv2 is None or decode is None:
        return None

    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        return None

    try:
        for _ in range(max_frames):
            ok, frame = capture.read()
            if not ok:
                continue

            product_id = scan_product_id_from_image(frame)
            if product_id:
                return product_id
    finally:
        capture.release()

    return None


def scan_or_fallback(product_id: Optional[str] = None, camera_index: int = 0) -> Optional[str]:
    normalized = normalize_scanned_value(product_id)
    if normalized:
        return normalized
    return scan_product_id_from_camera(camera_index=camera_index)