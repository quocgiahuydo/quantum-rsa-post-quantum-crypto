"""
Shor order-finding demonstration for N = 21.

This file contains a clean Python version of the Shor notebook. It focuses on
the educational workflow:

1. Choose N = 21 and a = 2.
2. Find/estimate the order r such that a^r = 1 mod N.
3. Use r to recover non-trivial factors of N.

The Qiskit circuit is included, but the default script behavior uses ideal
period counts so the file can run quickly on most machines. Use --simulate to
try the Aer simulator.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
from math import gcd, pi
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def classical_order(a: int, n: int) -> int | None:
    """Return the smallest r such that a^r ≡ 1 mod n."""
    if gcd(a, n) != 1:
        return None

    value = 1

    for r in range(1, n):
        value = (value * a) % n

        if value == 1:
            return r

    return None


def required_qubits(n: int) -> int:
    """Return number of qubits required to represent 0 through n - 1."""
    return (n - 1).bit_length()


def ideal_period_counts(r: int, num_control: int, shots: int = 4096) -> Dict[str, int]:
    """
    Generate ideal phase-measurement peaks for a period r.

    This is a lightweight fallback that mirrors what Shor's order-finding
    circuit is expected to reveal.
    """
    counts: Dict[str, int] = {}
    base = shots // r
    remainder = shots % r

    for s in range(r):
        decimal = round((s / r) * (2**num_control)) % (2**num_control)
        bitstring = format(decimal, f"0{num_control}b")
        counts[bitstring] = counts.get(bitstring, 0) + base

    first_key = next(iter(counts))
    counts[first_key] += remainder

    return counts


def estimate_order_from_phase(phase: float, a: int, n: int) -> tuple[Fraction, int | None]:
    """
    Estimate the order r from a measured phase.

    The denominator from continued fractions may be a divisor of the true order,
    so this function checks multiples until a valid order is found.
    """
    if phase == 0:
        return Fraction(0, 1), None

    frac = Fraction(phase).limit_denominator(n)
    denominator = frac.denominator

    for multiplier in range(1, n + 1):
        candidate_r = denominator * multiplier

        if pow(a, candidate_r, n) == 1:
            return frac, candidate_r

    return frac, denominator


def recover_factors_from_order(a: int, n: int, r: int | None) -> tuple[int | None, int | None]:
    """
    Recover non-trivial factors of n using a valid even order r.
    """
    if r is None or r % 2 != 0:
        return None, None

    x = pow(a, r // 2, n)

    # If x is -1 mod n, this order does not produce useful factors.
    if x == n - 1:
        return None, None

    factor_1 = gcd(x - 1, n)
    factor_2 = gcd(x + 1, n)

    if factor_1 in (1, n):
        factor_1 = None

    if factor_2 in (1, n):
        factor_2 = None

    return factor_1, factor_2


def analyze_counts(counts: Dict[str, int], a: int = 2, n: int = 21) -> List[dict]:
    """Convert measured bitstrings into phases, candidate orders, and factors."""
    num_control = len(next(iter(counts)))
    rows = []

    for bitstring, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        decimal = int(bitstring, 2)
        phase = decimal / (2**num_control)
        frac, recovered_r = estimate_order_from_phase(phase, a, n)
        factor_1, factor_2 = recover_factors_from_order(a, n, recovered_r)

        recovered_factors = [
            factor for factor in (factor_1, factor_2)
            if factor is not None
        ]

        rows.append({
            "bitstring": bitstring,
            "count": count,
            "decimal": decimal,
            "phase": phase,
            "fraction": f"{frac.numerator}/{frac.denominator}",
            "recovered_order_r": recovered_r,
            "factor_1": factor_1,
            "factor_2": factor_2,
            "recovered_factors": recovered_factors,
            "successful_factor": bool(recovered_factors),
        })

    return rows


def build_shor_circuit(a: int = 2, n: int = 21):
    """
    Build the Shor order-finding circuit for N = 21.

    Qiskit is imported inside this function so that basic analysis can run even
    when Qiskit is not installed.
    """
    import numpy as np
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit.library import UnitaryGate

    def mod_mult_gate(b: int, n: int):
        if gcd(b, n) != 1:
            raise ValueError(f"gcd({b}, {n}) must be 1.")

        num_target = required_qubits(n)
        dim = 2**num_target
        matrix = np.zeros((dim, dim), dtype=complex)

        for x in range(n):
            matrix[(b * x) % n, x] = 1

        for x in range(n, dim):
            matrix[x, x] = 1

        gate = UnitaryGate(matrix)
        gate.name = f"M_{b}_mod_{n}"

        return gate

    def inverse_qft(num_qubits: int):
        qc = QuantumCircuit(num_qubits, name="IQFT")

        for qubit in range(num_qubits // 2):
            qc.swap(qubit, num_qubits - qubit - 1)

        for j in range(num_qubits):
            for m in range(j):
                qc.cp(-pi / (2 ** (j - m)), m, j)
            qc.h(j)

        return qc.to_gate()

    num_target = required_qubits(n)
    num_control = 2 * num_target

    control = QuantumRegister(num_control, name="C")
    target = QuantumRegister(num_target, name="T")
    output = ClassicalRegister(num_control, name="out")

    circuit = QuantumCircuit(control, target, output)

    # Initialize target register to |1>.
    circuit.x(target[0])

    for k, control_qubit in enumerate(control):
        circuit.h(control_qubit)

        b = pow(a, 2**k, n)

        if b != 1:
            controlled_gate = mod_mult_gate(b, n).control()
            circuit.compose(
                controlled_gate,
                qubits=[control_qubit] + list(target),
                inplace=True,
            )

    circuit.append(inverse_qft(num_control), control)
    circuit.measure(control, output)

    return circuit


def run_qiskit_simulation(a: int = 2, n: int = 21, shots: int = 4096) -> Dict[str, int]:
    """Run the Shor circuit on Qiskit Aer."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    circuit = build_shor_circuit(a=a, n=n)
    simulator = AerSimulator(seed_simulator=42)
    circuit_sim = transpile(circuit, simulator, optimization_level=0)

    result = simulator.run(circuit_sim, shots=shots).result()
    return result.get_counts()


def save_histogram(counts: Dict[str, int], output_dir: str | Path = "figures") -> Path:
    """Save a histogram of Shor measurement results."""
    from qiskit.visualization import plot_histogram

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    top_counts = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:12])
    fig = plot_histogram(top_counts, title="Shor Measurement Results for N = 21")

    output_path = output_dir / "shor_measurement_histogram.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200)

    return output_path


def run_shor_demo(use_simulator: bool = False, shots: int = 4096) -> dict:
    """Run the Shor N = 21 demo."""
    n = 21
    a = 2
    expected_r = classical_order(a, n)
    num_control = 2 * required_qubits(n)

    if expected_r is None:
        raise RuntimeError("Could not compute expected order.")

    if use_simulator:
        counts = run_qiskit_simulation(a=a, n=n, shots=shots)
    else:
        counts = ideal_period_counts(expected_r, num_control, shots=shots)

    top_counts = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:12])
    rows = analyze_counts(top_counts, a=a, n=n)

    successful_rows = [row for row in rows if row["successful_factor"]]

    return {
        "N": n,
        "a": a,
        "expected_order_r": expected_r,
        "counts": top_counts,
        "analysis": rows,
        "successful_rows": successful_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Shor order-finding demo for N = 21.")
    parser.add_argument("--simulate", action="store_true", help="Run Qiskit Aer instead of ideal counts.")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--save-figure", action="store_true")
    args = parser.parse_args()

    result = run_shor_demo(use_simulator=args.simulate, shots=args.shots)

    print("===== Shor Demo for N = 21 =====")
    print(f"N: {result['N']}")
    print(f"a: {result['a']}")
    print(f"Expected order r: {result['expected_order_r']}")

    print("\nTop measurement outcomes:")
    for bitstring, count in result["counts"].items():
        print(f"{bitstring}: {count}")

    print("\nSuccessful factor recovery rows:")
    for row in result["successful_rows"]:
        print(row)

    if args.save_figure:
        path = save_histogram(result["counts"])
        print(f"\nSaved figure to: {path}")


if __name__ == "__main__":
    main()
