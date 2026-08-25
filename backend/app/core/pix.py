import qrcode
import io
import base64
from qrcode.image.pil import PilImage


def gerar_pix_payload(chave: str, nome: str, cidade: str, valor: float) -> str:
    """Gera o payload PIX no padrao BRCode (EMV)."""

    def campo(id_campo: str, valor_campo: str) -> str:
        return f"{id_campo}{len(valor_campo):02d}{valor_campo}"

    # Merchant Account Information (GUI PIX + chave)
    gui = campo("00", "br.gov.bcb.pix")
    # Se chave parece celular, adiciona +55
    if chave.isdigit() and len(chave) == 11:
        chave = "+55" + chave
    chave_campo = campo("01", chave)
    merchant = campo("26", gui + chave_campo)

    # Monta o payload sem CRC
    payload = ""
    payload += campo("00", "01")                    # Payload Format Indicator
    payload += merchant                              # Merchant Account
    payload += campo("52", "0000")                  # Merchant Category Code
    payload += campo("53", "986")                   # Transaction Currency (BRL)

    if valor > 0:
        valor_str = f"{valor:.2f}"
        payload += campo("54", valor_str)           # Transaction Amount

    payload += campo("58", "BR")                    # Country Code
    payload += campo("59", nome[:25])               # Merchant Name
    payload += campo("60", cidade[:15])             # Merchant City
    payload += campo("62", campo("05", "***"))      # Additional Data

    # CRC16 placeholder
    payload += "6304"

    # Calcula CRC16-CCITT
    crc = _crc16(payload)
    payload += f"{crc:04X}"

    return payload


def _crc16(data: str) -> int:
    """CRC16-CCITT para PIX."""
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def gerar_qrcode_pix_base64(chave: str, nome: str, cidade: str, valor: float) -> str:
    """Gera QR Code PIX e retorna como base64 PNG."""
    payload = gerar_pix_payload(chave, nome, cidade, valor)

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def gerar_qrcode_pix_bytes(chave: str, nome: str, cidade: str, valor: float) -> bytes:
    """Gera QR Code PIX e retorna como bytes PNG."""
    payload = gerar_pix_payload(chave, nome, cidade, valor)

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.read()