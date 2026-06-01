"""
Post-quantum ML-KEM demonstration using liboqs-python.

This file contains a clean Python version of the ML-KEM notebook.

ML-KEM is a key encapsulation mechanism, not direct message encryption. It lets
two parties establish the same shared secret. That shared secret can later be
used with a symmetric encryption algorithm such as AES.
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path
from typing import List


DEFAULT_ALGORITHMS = ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]


def _load_oqs():
    """
    Import oqs with a helpful error message.

    liboqs-python can be easier to run in Google Colab. On macOS, you may need:
        brew install cmake ninja openssl@3 wget
    """
    try:
        import oqs
        return oqs
    except Exception as exc:
        raise RuntimeError(
            "Could not import liboqs-python. If you are running locally on macOS, "
            "install build tools first: brew install cmake ninja openssl@3 wget. "
            "For the easiest workflow, run the ML-KEM notebook in Google Colab first."
        ) from exc


def available_ml_kem_algorithms() -> List[str]:
    """Return enabled ML-KEM algorithms from the local liboqs build."""
    oqs = _load_oqs()
    return [
        alg for alg in oqs.get_enabled_kem_mechanisms()
        if alg.startswith("ML-KEM")
    ]


def single_ml_kem_demo(kemalg: str = "ML-KEM-512") -> dict:
    """
    Run one ML-KEM key establishment demo.

    Alice generates a keypair. Bob encapsulates a shared secret using Alice's
    public key. Alice decapsulates Bob's ciphertext and recovers the same secret.
    """
    oqs = _load_oqs()

    with oqs.KeyEncapsulation(kemalg) as alice:
        with oqs.KeyEncapsulation(kemalg) as bob:
            public_key_alice = alice.generate_keypair()
            ciphertext, shared_secret_bob = bob.encap_secret(public_key_alice)
            shared_secret_alice = alice.decap_secret(ciphertext)

            secrets_match = shared_secret_alice == shared_secret_bob
            assert secrets_match

            return {
                "algorithm": kemalg,
                "public_key_bytes": len(public_key_alice),
                "ciphertext_bytes": len(ciphertext),
                "shared_secret_bytes": len(shared_secret_alice),
                "shared_secrets_match": secrets_match,
            }


def compare_ml_kem_parameter_sets(algorithms: List[str] | None = None) -> List[dict]:
    """Compare key size, ciphertext size, and one-run runtime for ML-KEM parameter sets."""
    oqs = _load_oqs()
    algorithms = algorithms or DEFAULT_ALGORITHMS

    enabled = set(oqs.get_enabled_kem_mechanisms())
    results = []

    for alg in algorithms:
        if alg not in enabled:
            print(f"{alg} is not enabled in this liboqs build. Skipping.")
            continue

        with oqs.KeyEncapsulation(alg) as alice:
            with oqs.KeyEncapsulation(alg) as bob:
                start = time.perf_counter()
                public_key = alice.generate_keypair()
                keygen_time = time.perf_counter() - start

                start = time.perf_counter()
                ciphertext, shared_secret_bob = bob.encap_secret(public_key)
                encap_time = time.perf_counter() - start

                start = time.perf_counter()
                shared_secret_alice = alice.decap_secret(ciphertext)
                decap_time = time.perf_counter() - start

                secrets_match = shared_secret_alice == shared_secret_bob
                assert secrets_match

                results.append({
                    "algorithm": alg,
                    "public_key_bytes": len(public_key),
                    "ciphertext_bytes": len(ciphertext),
                    "shared_secret_bytes": len(shared_secret_alice),
                    "keygen_time_seconds": keygen_time,
                    "encapsulation_time_seconds": encap_time,
                    "decapsulation_time_seconds": decap_time,
                    "shared_secrets_match": secrets_match,
                })

    return results


def benchmark_ml_kem(
    algorithms: List[str] | None = None,
    trials: int = 100,
) -> List[dict]:
    """Run repeated ML-KEM timing trials."""
    oqs = _load_oqs()
    algorithms = algorithms or DEFAULT_ALGORITHMS
    enabled = set(oqs.get_enabled_kem_mechanisms())

    benchmark_results = []

    for alg in algorithms:
        if alg not in enabled:
            print(f"{alg} is not enabled in this liboqs build. Skipping.")
            continue

        keygen_times = []
        encap_times = []
        decap_times = []

        for _ in range(trials):
            with oqs.KeyEncapsulation(alg) as alice:
                with oqs.KeyEncapsulation(alg) as bob:
                    start = time.perf_counter()
                    public_key = alice.generate_keypair()
                    keygen_times.append(time.perf_counter() - start)

                    start = time.perf_counter()
                    ciphertext, shared_secret_bob = bob.encap_secret(public_key)
                    encap_times.append(time.perf_counter() - start)

                    start = time.perf_counter()
                    shared_secret_alice = alice.decap_secret(ciphertext)
                    decap_times.append(time.perf_counter() - start)

                    assert shared_secret_alice == shared_secret_bob

        benchmark_results.append({
            "algorithm": alg,
            "trials": trials,
            "avg_keygen_time": statistics.mean(keygen_times),
            "avg_encapsulation_time": statistics.mean(encap_times),
            "avg_decapsulation_time": statistics.mean(decap_times),
            "std_keygen_time": statistics.stdev(keygen_times) if trials > 1 else 0.0,
            "std_encapsulation_time": statistics.stdev(encap_times) if trials > 1 else 0.0,
            "std_decapsulation_time": statistics.stdev(decap_times) if trials > 1 else 0.0,
        })

    return benchmark_results


def save_size_comparison_figure(results: List[dict], output_dir: str | Path = "figures") -> Path:
    """Save ML-KEM public key/ciphertext size comparison figure."""
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(results)

    x = np.arange(len(df["algorithm"]))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.bar(x - width / 2, df["public_key_bytes"], width, label="Public key")
    ax.bar(x + width / 2, df["ciphertext_bytes"], width, label="Ciphertext")

    ax.set_xlabel("ML-KEM parameter set")
    ax.set_ylabel("Size in bytes")
    ax.set_title("ML-KEM Public Key and Ciphertext Size Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(df["algorithm"])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()

    output_path = output_dir / "mlkem_key_ciphertext_size_comparison.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200)
    plt.close(fig)

    return output_path


def save_runtime_comparison_figure(results: List[dict], output_dir: str | Path = "figures") -> Path:
    """Save ML-KEM runtime comparison figure."""
    import pandas as pd
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(results)
    trials = int(df["trials"].iloc[0]) if not df.empty else 0

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(df["algorithm"], df["avg_keygen_time"], marker="o", label="Key generation")
    ax.plot(df["algorithm"], df["avg_encapsulation_time"], marker="o", label="Encapsulation")
    ax.plot(df["algorithm"], df["avg_decapsulation_time"], marker="o", label="Decapsulation")

    ax.set_xlabel("ML-KEM parameter set")
    ax.set_ylabel("Average runtime in seconds")
    ax.set_title(f"ML-KEM Average Runtime Comparison ({trials} Trials)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    output_path = output_dir / "mlkem_average_runtime_comparison.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200)
    plt.close(fig)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ML-KEM key establishment demo.")
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--save-figures", action="store_true")
    args = parser.parse_args()

    print("Available ML-KEM algorithms:")
    print(available_ml_kem_algorithms())

    print("\n===== Single ML-KEM Demo =====")
    single = single_ml_kem_demo("ML-KEM-512")
    print(single)

    print("\n===== Parameter Set Comparison =====")
    comparison = compare_ml_kem_parameter_sets()
    for row in comparison:
        print(row)

    print("\n===== Runtime Benchmark =====")
    benchmark = benchmark_ml_kem(trials=args.trials)
    for row in benchmark:
        print(row)

    if args.save_figures:
        size_path = save_size_comparison_figure(comparison)
        runtime_path = save_runtime_comparison_figure(benchmark)
        print(f"\nSaved figure to: {size_path}")
        print(f"Saved figure to: {runtime_path}")


if __name__ == "__main__":
    main()
