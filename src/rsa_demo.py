"""
RSA baseline utilities for the Quantum Threats to RSA project.

This file contains a small educational RSA implementation used to support the
notebooks and report. It is intentionally simple and should NOT be used for
real cryptographic applications.

Main ideas:
- Generate a small RSA keypair.
- Encrypt/decrypt numbers.
- Encrypt/decrypt a short text message character by character.
- Reproduce the toy RSA setup used throughout the project: n = 21.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class RSAKeyPair:
    """Small educational RSA keypair."""

    p: int
    q: int
    n: int
    phi_n: int
    e: int
    d: int


def is_prime(num: int) -> bool:
    """
    Return True if num is prime, otherwise False.

    This is a simple trial-division check. It is fine for this educational
    project, but it is not meant for real cryptography.
    """
    if num < 2:
        return False

    for divisor in range(2, int(math.sqrt(num)) + 1):
        if num % divisor == 0:
            return False

    return True


def generate_prime(min_value: int, max_value: int, rng: random.Random | None = None) -> int:
    """Generate a random prime number in [min_value, max_value]."""
    if min_value > max_value:
        raise ValueError("min_value must be <= max_value.")

    rng = rng or random
    candidate = rng.randint(min_value, max_value)

    while not is_prime(candidate):
        candidate = rng.randint(min_value, max_value)

    return candidate


def generate_small_rsa_keypair(
    min_prime: int = 1000,
    max_prime: int = 5000,
    seed: int | None = 42,
) -> RSAKeyPair:
    """
    Generate a small educational RSA keypair.

    Returns
    -------
    RSAKeyPair
        p, q, n, phi_n, e, and d.
    """
    rng = random.Random(seed)

    p = generate_prime(min_prime, max_prime, rng)
    q = generate_prime(min_prime, max_prime, rng)

    while p == q:
        q = generate_prime(min_prime, max_prime, rng)

    n = p * q
    phi_n = (p - 1) * (q - 1)

    e = rng.randint(3, phi_n - 1)
    while math.gcd(e, phi_n) != 1:
        e = rng.randint(3, phi_n - 1)

    d = pow(e, -1, phi_n)

    return RSAKeyPair(p=p, q=q, n=n, phi_n=phi_n, e=e, d=d)


def rsa_encrypt_number(message: int, e: int, n: int) -> int:
    """
    Encrypt one integer message using RSA.

    The message must be smaller than n.
    """
    if message < 0:
        raise ValueError("Message must be non-negative.")

    if message >= n:
        raise ValueError("Message must be smaller than n.")

    return pow(message, e, n)


def rsa_decrypt_number(ciphertext: int, d: int, n: int) -> int:
    """Decrypt one integer ciphertext using RSA."""
    if ciphertext < 0:
        raise ValueError("Ciphertext must be non-negative.")

    return pow(ciphertext, d, n)


def rsa_encrypt_text(message: str, e: int, n: int) -> List[int]:
    """
    Encrypt a short text message character by character.

    Note
    ----
    This is only for demonstration. Real RSA does not encrypt raw text
    character by character and must use secure padding.
    """
    encoded_message = [ord(char) for char in message]
    return [rsa_encrypt_number(value, e, n) for value in encoded_message]


def rsa_decrypt_text(ciphertext: Iterable[int], d: int, n: int) -> str:
    """Decrypt a character-by-character RSA ciphertext back into text."""
    decoded_values = [rsa_decrypt_number(value, d, n) for value in ciphertext]
    return "".join(chr(value) for value in decoded_values)


def get_toy_rsa_keypair() -> RSAKeyPair:
    """
    Return the fixed toy RSA setup used across the project.

    p = 3
    q = 7
    n = 21
    phi(n) = 12
    e = 5
    d = 5
    """
    p = 3
    q = 7
    n = p * q
    phi_n = (p - 1) * (q - 1)
    e = 5
    d = pow(e, -1, phi_n)

    return RSAKeyPair(p=p, q=q, n=n, phi_n=phi_n, e=e, d=d)


def run_basic_rsa_demo() -> dict:
    """Run the random small-prime RSA demonstration from the notebook."""
    keys = generate_small_rsa_keypair(seed=42)

    message = "Hello World"
    ciphertext = rsa_encrypt_text(message, keys.e, keys.n)
    decoded_message = rsa_decrypt_text(ciphertext, keys.d, keys.n)

    assert decoded_message == message

    return {
        "public_key": (keys.e, keys.n),
        "private_key": (keys.d, keys.n),
        "p": keys.p,
        "q": keys.q,
        "phi_n": keys.phi_n,
        "message": message,
        "ciphertext": ciphertext,
        "decoded_message": decoded_message,
    }


def run_toy_rsa_demo(message: int = 5) -> dict:
    """
    Run the fixed toy RSA demo used for the Shor and Grover connections.

    For message = 5, this produces ciphertext = 17.
    """
    keys = get_toy_rsa_keypair()

    ciphertext = rsa_encrypt_number(message, keys.e, keys.n)
    decrypted_message = rsa_decrypt_number(ciphertext, keys.d, keys.n)

    assert decrypted_message == message

    return {
        "p": keys.p,
        "q": keys.q,
        "n": keys.n,
        "phi_n": keys.phi_n,
        "public_key": (keys.e, keys.n),
        "private_key": (keys.d, keys.n),
        "message": message,
        "ciphertext": ciphertext,
        "decrypted_message": decrypted_message,
    }


def main() -> None:
    """Print both RSA demonstrations."""
    print("===== Basic RSA Demo =====")
    basic = run_basic_rsa_demo()
    for key, value in basic.items():
        print(f"{key}: {value}")

    print("\n===== Toy RSA Demo =====")
    toy = run_toy_rsa_demo(message=5)
    for key, value in toy.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
