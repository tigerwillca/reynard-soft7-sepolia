#!/usr/bin/env bash
# Compile contracts/Soft7MascotCards.sol with the pinned solc settings.
# Writes contracts/compiler-input.json, the file Blockscout needs for a blue check.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOLC="${SOLC:-$ROOT/.tools/solc-0.8.24}"
mkdir -p "$ROOT/.tools" "$ROOT/contracts/out"

if [[ ! -x "$SOLC" ]]; then
  curl -fsSL -o "$SOLC" \
    "https://github.com/ethereum/solc-bin/raw/gh-pages/linux-amd64/solc-linux-amd64-v0.8.24%2Bcommit.e11b9ed9"
  chmod +x "$SOLC"
fi

python3 - "$ROOT" << 'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
source = (root / "contracts" / "Soft7MascotCards.sol").read_text()
job = {
    "language": "Solidity",
    "sources": {"Soft7MascotCards.sol": {"content": source}},
    "settings": {
        "optimizer": {"enabled": True, "runs": 200},
        "evmVersion": "cancun",
        "outputSelection": {
            "*": {
                "*": ["abi", "evm.bytecode", "evm.deployedBytecode", "metadata"],
                "": ["ast"]
            }
        },
        "metadata": {"bytecodeHash": "ipfs"},
    },
}
(root / "contracts" / "compiler-input.json").write_text(json.dumps(job, indent=2) + "\n")
PY

"$SOLC" --standard-json "$ROOT/contracts/compiler-input.json" > "$ROOT/contracts/out/compiler-output.json"

python3 - "$ROOT" << 'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
out = json.loads((root / "contracts" / "out" / "compiler-output.json").read_text())
errors = [e for e in out.get("errors", []) if e.get("severity") == "error"]
if errors:
    for e in errors:
        print(e.get("formatted", e.get("message")))
    raise SystemExit(1)
contract = out["contracts"]["Soft7MascotCards.sol"]["Soft7MascotCards"]
byte = contract["evm"]["bytecode"]["object"]
print(f"compiled Soft7MascotCards bytecode bytes {len(byte)//2}")
(root / "contracts" / "out" / "Soft7MascotCards.bin").write_text(byte + "\n")
PY
