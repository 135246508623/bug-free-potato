import random
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

SENTRY_BASE = "https://sentry.platorelay.com/.gs/pow/captcha"

# Base telemetry values from the user's example – we add random noise to them
BASE_TELEMETRY = {
    "dwellMs": 446629,
    "moves": 592,
    "velocityVar": 17.2058786473109,
    "velocityMedian": 1.455788671386738,
    "velocityAvg": 3.2309785421350123,
    "velocityMin": 0.0005871534893303571,
    "velocityMax": 18.108148421848494,
    "velocityP25": 0.42923229467905805,
    "velocityP75": 3.793246599138705,
    "directionChanges": 31,
    "keypresses": 0,
    "speedSamples": 592,
    "moveDensity": 754.4408783783783
}

def generate_telemetry(variation=0.1):
    """Generate telemetry by applying random variation (±variation%) to base values."""
    telemetry = {}
    for key, value in BASE_TELEMETRY.items():
        factor = 1 + random.uniform(-variation, variation)
        telemetry[key] = value * factor
    # Ensure integer fields are integers
    telemetry["dwellMs"] = int(telemetry["dwellMs"])
    telemetry["moves"] = int(telemetry["moves"])
    telemetry["directionChanges"] = int(telemetry["directionChanges"])
    telemetry["keypresses"] = 0
    telemetry["speedSamples"] = telemetry["moves"]  # must equal moves
    telemetry["moveDensity"] = telemetry["moveDensity"]  # keep as float
    return telemetry

def generate_fingerprint():
    """Generate a random device fingerprint like '-47a1ca5b'."""
    return "-" + ''.join(random.choices("0123456789abcdef", k=8))

def solve_puzzle(puzzle_data):
    """
    Extract instruction and shapes, then return the index of the correct shape.
    Instruction format: "Click the largest circle." (or smallest)
    """
    instruction = puzzle_data["puzzle"]["instruction"]
    shapes = puzzle_data["puzzle"]["shapes"]

    # Parse instruction
    match = re.search(r"Click the (largest|smallest) (\w+)", instruction, re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not parse instruction: {instruction}")
    comparator = match.group(1).lower()
    shape_type = match.group(2).lower()

    # Filter shapes by type
    candidates = [(i, s) for i, s in enumerate(shapes) if s["type"].lower() == shape_type]
    if not candidates:
        raise ValueError(f"No shapes of type '{shape_type}' found")

    # Find shape with largest or smallest size
    if comparator == "largest":
        best = max(candidates, key=lambda x: x[1]["size"])
    else:  # smallest
        best = min(candidates, key=lambda x: x[1]["size"])

    return best[0]  # index

@app.route("/bypass", methods=["POST"])
def bypass():
    """
    Main endpoint: triggers the captcha bypass flow.
    Optional JSON body can provide custom telemetry and deviceFingerprint.
    """
    data = request.get_json() or {}

    # Use provided telemetry/fingerprint or generate fresh ones
    telemetry = data.get("telemetry") or generate_telemetry()
    fingerprint = data.get("deviceFingerprint") or generate_fingerprint()

    # Step 1: Request a puzzle
    req_payload = {
        "telemetry": telemetry,
        "deviceFingerprint": fingerprint,
        "forcePuzzle": False
    }
    try:
        r = requests.post(f"{SENTRY_BASE}/request", json=req_payload, timeout=15)
        r.raise_for_status()
        puzzle_response = r.json()
    except Exception as e:
        return jsonify({"error": f"Puzzle request failed: {str(e)}"}), 500

    if "puzzle" not in puzzle_response:
        return jsonify({"error": "No puzzle in response", "response": puzzle_response}), 500

    # Step 2: Solve the puzzle
    try:
        answer_index = solve_puzzle(puzzle_response)
    except Exception as e:
        return jsonify({"error": f"Solving failed: {str(e)}"}), 500

    # Step 3: Verify the answer
    # We assume the verify endpoint expects the puzzle ID and the shape index.
    # Adjust the key names if the actual endpoint requires different fields.
    verify_payload = {
        "id": puzzle_response["id"],
        "answer": answer_index
    }
    try:
        v = requests.post(f"{SENTRY_BASE}/verify", json=verify_payload, timeout=15)
        v.raise_for_status()
        verify_result = v.json()
    except Exception as e:
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "puzzle_id": puzzle_response["id"],
        "answer_index": answer_index,
        "verification_result": verify_result
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
