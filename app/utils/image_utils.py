def is_base64_data_uri(image_input: str) -> bool:
    """Verilen görsel girdisinin Base64 Data URI şemasına sahip olup olmadığını kontrol eder."""
    if not image_input:
        return False
    return image_input.strip().startswith("data:image/")


def ensure_image_data_uri(image_input: str) -> str:
    """
    Görsel girdisinin geçerli bir URL (http/https) veya Base64 Data URI
    (data:image/...;base64,...) formatında olmasını sağlar.
    Saf (raw) Base64 verisi gelmişse data URI ön eki ekler.
    """
    if not image_input:
        return ""
    s = image_input.strip()
    if s.startswith("data:image/") or s.startswith("http://") or s.startswith("https://"):
        return s
    # Saf base64 verisi ise data URI şemasını ekle
    return f"data:image/jpeg;base64,{s}"
