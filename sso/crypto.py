"""AES 加密工具"""

import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


def aes_encrypt(key_str: str, plaintext: str) -> str:
    """
    AES-128-ECB + PKCS7 加密

    Args:
        key_str: base64 编码的密钥（login-croypto 字段，解码后 16 字节）
        plaintext: 明文（密码或验证码）

    Returns:
        base64 编码的密文
    """
    key = base64.b64decode(key_str)
    pt = plaintext.encode("utf-8")
    cipher = AES.new(key, AES.MODE_ECB)
    ct = cipher.encrypt(pad(pt, AES.block_size))
    return base64.b64encode(ct).decode()
