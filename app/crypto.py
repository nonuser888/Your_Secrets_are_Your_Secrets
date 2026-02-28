"""
Encryption for chat history summaries.
Keys are derived from the user's secret (password/key); only the user can decrypt.
"""
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

BACKEND = default_backend()
KDF_ITERATIONS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32


def derive_key(secret: str | bytes, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derive a 256-bit key from the user secret. Returns (key, salt)."""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if salt is None:
        salt = os.urandom(SALT_BYTES)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        iterations=KDF_ITERATIONS,
        backend=BACKEND,
    )
    key = kdf.derive(secret)
    return key, salt


def encrypt_with_key(plaintext: str | bytes, key: bytes) -> bytes:
    """Encrypt with AES-256-GCM using raw key. Output: nonce (12) + ciphertext+tag."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    nonce = os.urandom(NONCE_BYTES)
    aes = AESGCM(key)
    ct = aes.encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_with_key(payload: bytes, key: bytes) -> bytes:
    """Decrypt payload from encrypt_with_key()."""
    if len(payload) < NONCE_BYTES + 16:
        raise ValueError("Payload too short")
    nonce = payload[:NONCE_BYTES]
    ciphertext = payload[NONCE_BYTES:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, None)


def encrypt_for_user(plaintext: str | bytes, user_secret: str | bytes) -> bytes:
    """Encrypt for user: derive key from user_secret (salt stored in output). Output: salt + nonce + ct."""
    key, salt = derive_key(user_secret)
    ct = encrypt_with_key(plaintext, key)
    return salt + ct


def decrypt_for_user(payload: bytes, user_secret: str | bytes) -> bytes:
    """Decrypt payload from encrypt_for_user()."""
    if len(payload) < SALT_BYTES + NONCE_BYTES + 16:
        raise ValueError("Payload too short")
    salt = payload[:SALT_BYTES]
    key, _ = derive_key(user_secret, salt=salt)
    return decrypt_with_key(payload[SALT_BYTES:], key)


def payload_to_hex(payload: bytes) -> str:
    return payload.hex()


def hex_to_payload(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)
