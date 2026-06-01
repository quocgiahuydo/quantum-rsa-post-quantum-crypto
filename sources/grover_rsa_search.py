"""
Grover search demonstration for a toy RSA plaintext.

The search problem is:

Given public key (e, n) = (5, 21) and ciphertext c = 17,
find a plaintext m such that:

    m^5 mod 21 = 17

The correct answer is m = 5, represented as the 5-qubit state 00101.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List


def find_marked_states(e: int = 5, n: int = 21, ciphertext: int = 17) -> List[str]:
    """
    Find all plaintext values m such that m^e mod n equals ciphertext.

    This classical precomputation is used to define the simplified Grover
    oracle in the educational notebook.
    """
    num_qubits = math.ceil(math.log2(n))
    search_space_size = 2**num_qubits

    marked_states = []

    for candidate_message in range(search_space_size):
        if candidate_message < n and pow(candidate_message, e, n) == ciphertext:
            marked_states.append(format(candidate_message, f"0{num_qubits}b"))

    return marked_states


def classical_brute_force(e: int = 5, n: int = 21, ciphertext: int = 17) -> dict:
    """Classically search for m such that m^e mod n = ciphertext."""
    num_qubits = math.ceil(math.log2(n))
    search_space_size = 2**num_qubits

    attempts = 0

    for candidate_message in range(search_space_size):
        attempts += 1

        if candidate_message < n and pow(candidate_message, e, n) == ciphertext:
            return {
                "found_message": candidate_message,
                "attempts": attempts,
                "search_space_size": search_space_size,
            }

    return {
        "found_message": None,
        "attempts": attempts,
        "search_space_size": search_space_size,
    }


def optimal_grover_iterations(num_solutions: int, search_space_size: int) -> int:
    """Return the approximate optimal number of Grover iterations."""
    if num_solutions <= 0:
        raise ValueError("num_solutions must be positive.")

    if search_space_size <= 0:
        raise ValueError("search_space_size must be positive.")

    return math.floor(
        math.pi / (4 * math.asin(math.sqrt(num_solutions / search_space_size)))
    )


def grover_oracle(marked_states):
    """
    Build a Grover oracle for one or more marked states.

    Qiskit is imported inside this function so this file can still be imported
    when Qiskit is not installed.
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import MCMTGate, ZGate

    if isinstance(marked_states, str):
        marked_states = [marked_states]

    if not marked_states:
        raise ValueError("At least one marked state is required.")

    num_qubits = len(marked_states[0])

    if any(len(state) != num_qubits for state in marked_states):
        raise ValueError("All marked states must have the same length.")

    if any(bit not in "01" for state in marked_states for bit in state):
        raise ValueError("Marked states must be bitstrings containing only 0 and 1.")

    qc = QuantumCircuit(num_qubits)

    for target in marked_states:
        # Qiskit uses little-endian qubit ordering, so reverse the bitstring.
        reversed_target = target[::-1]

        zero_indices = [
            index for index, bit in enumerate(reversed_target)
            if bit == "0"
        ]

        qc.x(zero_indices)
        qc.compose(MCMTGate(ZGate(), num_qubits - 1, 1), inplace=True)
        qc.x(zero_indices)

    return qc


def build_grover_circuit(marked_states: List[str], iterations: int):
    """Build the full Grover circuit."""
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import grover_operator

    oracle = grover_oracle(marked_states)
    grover_op = grover_operator(oracle)

    qc = QuantumCircuit(grover_op.num_qubits)
    qc.h(range(grover_op.num_qubits))

    if iterations > 0:
        qc.compose(grover_op.power(iterations), inplace=True)

    qc.measure_all()

    return qc


def run_grover_simulation(
    e: int = 5,
    n: int = 21,
    ciphertext: int = 17,
    shots: int = 10_000,
) -> dict:
    """Run Grover search on the Aer simulator."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    marked_states = find_marked_states(e=e, n=n, ciphertext=ciphertext)
    num_qubits = math.ceil(math.log2(n))
    search_space_size = 2**num_qubits
    iterations = optimal_grover_iterations(len(marked_states), search_space_size)

    qc = build_grover_circuit(marked_states, iterations)

    simulator = AerSimulator(seed_simulator=42)
    qc_sim = transpile(qc, simulator, optimization_level=1, seed_transpiler=42)

    result = simulator.run(qc_sim, shots=shots).result()
    counts = result.get_counts()

    most_likely_bitstring = max(counts, key=counts.get)
    recovered_message = int(most_likely_bitstring, 2)

    success_probability = sum(
        counts.get(state, 0) for state in marked_states
    ) / shots

    return {
        "public_key": (e, n),
        "ciphertext": ciphertext,
        "marked_states": marked_states,
        "iterations": iterations,
        "counts": counts,
        "most_likely_bitstring": most_likely_bitstring,
        "recovered_message": recovered_message,
        "success_probability": success_probability,
        "shots": shots,
    }


def benchmark_iterations(
    marked_states: List[str],
    max_iterations: int = 9,
    shots: int = 10_000,
) -> List[dict]:
    """Test Grover success probability across different iteration counts."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    simulator = AerSimulator(seed_simulator=42)
    rows = []

    for iterations in range(max_iterations + 1):
        circuit = build_grover_circuit(marked_states, iterations)
        circuit_sim = transpile(
            circuit,
            simulator,
            optimization_level=1,
            seed_transpiler=42,
        )

        result = simulator.run(circuit_sim, shots=shots).result()
        counts = result.get_counts()

        success_probability = sum(
            counts.get(state, 0) for state in marked_states
        ) / shots

        most_likely_state = max(counts, key=counts.get)

        rows.append({
            "grover_iterations": iterations,
            "most_likely_state": most_likely_state,
            "success_probability": success_probability,
        })

    return rows


def save_distribution_figure(counts: Dict[str, int], output_dir: str | Path = "figures") -> Path:
    """Save the Grover measurement distribution figure."""
    from qiskit.visualization import plot_distribution

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig = plot_distribution(counts)
    output_path = output_dir / "grover_simulator_distribution.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Grover search on a toy RSA plaintext.")
    parser.add_argument("--shots", type=int, default=10_000)
    parser.add_argument("--save-figure", action="store_true")
    args = parser.parse_args()

    e = 5
    n = 21
    message = 5
    ciphertext = pow(message, e, n)

    classical = classical_brute_force(e=e, n=n, ciphertext=ciphertext)
    result = run_grover_simulation(e=e, n=n, ciphertext=ciphertext, shots=args.shots)

    print("===== Toy RSA Search Problem =====")
    print(f"Public key: (e, n) = ({e}, {n})")
    print(f"Ciphertext: {ciphertext}")
    print(f"Target message: {message}")

    print("\n===== Classical Brute Force =====")
    print(classical)

    print("\n===== Grover Simulator Result =====")
    for key in [
        "marked_states",
        "iterations",
        "most_likely_bitstring",
        "recovered_message",
        "success_probability",
    ]:
        print(f"{key}: {result[key]}")

    if args.save_figure:
        path = save_distribution_figure(result["counts"])
        print(f"\nSaved figure to: {path}")


if __name__ == "__main__":
    main()
