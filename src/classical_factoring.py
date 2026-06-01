"""
Classical factoring attack utilities for the Quantum Threats to RSA project.

This file shows why factoring the RSA modulus n breaks RSA. It connects to the
toy RSA setup n = 21 used by the Shor and Grover notebooks.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

try:
    from .rsa_demo import (
        RSAKeyPair,
        get_toy_rsa_keypair,
        rsa_decrypt_number,
        rsa_encrypt_number,
    )
except ImportError:
    from rsa_demo import (
        RSAKeyPair,
        get_toy_rsa_keypair,
        rsa_decrypt_number,
        rsa_encrypt_number,
    )


@dataclass(frozen=True)
class FactoringResult:
    """Result of trial-division factoring."""

    p: int | None
    q: int | None
    trial_divisions: int
    runtime_seconds: float


def classical_factor_with_steps(n: int) -> FactoringResult:
    """
    Factor n using trial division.

    Returns the first non-trivial factor pair found and the number of divisions
    attempted. This is intentionally simple for educational comparison.
    """
    if n < 2:
        raise ValueError("n must be at least 2.")

    start_time = time.perf_counter()
    steps = 0

    for possible_factor in range(2, math.isqrt(n) + 1):
        steps += 1

        if n % possible_factor == 0:
            p = possible_factor
            q = n // possible_factor
            runtime = time.perf_counter() - start_time
            return FactoringResult(p=p, q=q, trial_divisions=steps, runtime_seconds=runtime)

    runtime = time.perf_counter() - start_time
    return FactoringResult(p=None, q=None, trial_divisions=steps, runtime_seconds=runtime)


def recover_private_exponent_from_factors(e: int, p: int, q: int) -> int:
    """Recover RSA private exponent d once p and q are known."""
    phi_n = (p - 1) * (q - 1)
    return pow(e, -1, phi_n)


def run_classical_factoring_attack(message: int = 5) -> dict:
    """
    Reproduce the toy RSA factoring attack.

    Public information:
    - n = 21
    - e = 5
    - ciphertext = 17

    Attacker factors n into 3 and 7, reconstructs d, and decrypts the message.
    """
    keys = get_toy_rsa_keypair()

    ciphertext = rsa_encrypt_number(message, keys.e, keys.n)
    factor_result = classical_factor_with_steps(keys.n)

    if factor_result.p is None or factor_result.q is None:
        raise RuntimeError("Failed to factor the toy RSA modulus.")

    recovered_d = recover_private_exponent_from_factors(
        e=keys.e,
        p=factor_result.p,
        q=factor_result.q,
    )

    attacker_decrypted = rsa_decrypt_number(ciphertext, recovered_d, keys.n)

    assert {factor_result.p, factor_result.q} == {keys.p, keys.q}
    assert recovered_d == keys.d
    assert attacker_decrypted == message

    return {
        "public_modulus_n": keys.n,
        "public_exponent_e": keys.e,
        "ciphertext": ciphertext,
        "recovered_p": factor_result.p,
        "recovered_q": factor_result.q,
        "trial_divisions": factor_result.trial_divisions,
        "runtime_seconds": factor_result.runtime_seconds,
        "recovered_private_exponent_d": recovered_d,
        "attacker_decrypted_message": attacker_decrypted,
    }


def build_factoring_cost_table() -> List[dict]:
    """Return small RSA-like moduli and their trial-division costs."""
    test_cases = [
        (3, 5),
        (3, 7),      # n = 21, the main toy RSA modulus
        (5, 7),
        (7, 11),
        (11, 13),
        (13, 17),
        (17, 19),
        (19, 23),
        (29, 31),
        (37, 41),
    ]

    rows = []

    for p_test, q_test in test_cases:
        n_test = p_test * q_test
        result = classical_factor_with_steps(n_test)

        rows.append({
            "p": p_test,
            "q": q_test,
            "n": n_test,
            "recovered_p": result.p,
            "recovered_q": result.q,
            "trial_divisions": result.trial_divisions,
        })

    return rows


def save_factoring_cost_figure(output_dir: str | Path = "figures") -> Path:
    """
    Save the classical factoring cost figure.

    Requires pandas and matplotlib.
    """
    import pandas as pd
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(build_factoring_cost_table())

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df["n"], df["trial_divisions"], marker="o")
    ax.set_xlabel("RSA modulus n = p × q")
    ax.set_ylabel("Number of trial divisions")
    ax.set_title("Classical Factoring Cost for Small RSA-Like Moduli")
    ax.grid(True)

    output_path = output_dir / "rsa_classical_factoring_cost.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200)
    plt.close(fig)

    return output_path


def main() -> None:
    """Run and print the classical factoring attack."""
    result = run_classical_factoring_attack(message=5)

    print("===== Classical Factoring Attack =====")
    for key, value in result.items():
        print(f"{key}: {value}")

    figure_path = save_factoring_cost_figure()
    print(f"\nSaved figure to: {figure_path}")


if __name__ == "__main__":
    main()
