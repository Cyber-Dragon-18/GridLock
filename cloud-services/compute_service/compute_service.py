import time
import threading
import openstack
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- SLA / Scaling Configuration ---
SLA_MAX_WAIT_SECONDS = 60
CPU_SCALE_UP_THRESHOLD = 70
CPU_SCALE_DOWN_THRESHOLD = 30
MIN_INSTANCES = 1
MAX_INSTANCES = 10
IDLE_TIMEOUT = 300
POLL_INTERVAL = 30

VM_FLAVOR = "m1.small"
VM_IMAGE = "cirros-0.6.3-x86_64-disk"
VM_NETWORK = "private"


def _get_connection():
    return openstack.connect()

def _vm_name(index):
    return f"compute-node-{index}"


# --- Core Functions ---

def list_vms():
    conn = _get_connection()
    servers = conn.compute.servers(details=True)
    return [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "created_at": s.created_at,
            "flavor": s.flavor.get("original_name", s.flavor.get("id")),
            "addresses": s.addresses,
        }
        for s in servers
        if s.name.startswith("compute-node-")
    ]


def provision_vm(index):
    conn = _get_connection()
    name = _vm_name(index)

    existing = list(conn.compute.servers(name=name))
    if existing:
        return {"status": "already_exists", "name": name, "id": existing[0].id}

    image = conn.compute.find_image(VM_IMAGE)
    flavor = conn.compute.find_flavor(VM_FLAVOR)
    network = conn.network.find_network(VM_NETWORK)

    server = conn.compute.create_server(
        name=name,
        image_id=image.id,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],
    )

    server = conn.compute.wait_for_server(server)
    return {"status": "provisioned", "name": name, "id": server.id}


def deprovision_vm(vm_id):
    conn = _get_connection()
    try:
        conn.compute.delete_server(vm_id, force=True)
        return {"status": "deleted", "id": vm_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_vm_status(vm_id):
    conn = _get_connection()
    try:
        server = conn.compute.get_server(vm_id)
        return {
            "id": server.id,
            "name": server.name,
            "status": server.status,
            "flavor": server.flavor.get("original_name", server.flavor.get("id")),
            "addresses": server.addresses,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_vm_cpu_usage(vm_id):
    conn = _get_connection()
    try:
        diagnostics = conn.compute.get_server_diagnostics(vm_id)
        cpu_time = diagnostics.get("cpu0_time", None)
        if cpu_time is not None:
            return min(float(cpu_time) / 1e10, 100.0)
        return -1.0
    except Exception:
        return -1.0


def submit_job(username, script):
    start = time.time()
    while time.time() - start < SLA_MAX_WAIT_SECONDS:
        vms = list_vms()
        active = [v for v in vms if v["status"] == "ACTIVE"]
        if active:
            assigned_vm = active[0]
            return {
                "status": "submitted",
                "vm": assigned_vm["name"],
                "vm_id": assigned_vm["id"],
                "user": username,
                "script": script,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            print("[JobSubmit] No active VM — provisioning one to meet SLA...")
            provision_vm(1)
            time.sleep(10)

    return {
        "status": "error",
        "message": f"No VM became available within SLA window of {SLA_MAX_WAIT_SECONDS}s.",
    }


# --- AutoScaler ---

class AutoScaler:
    def __init__(self):
        self._running = False
        self._thread = None
        self._last_activity = {}

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[AutoScaler] Started.")

    def stop(self):
        self._running = False
        print("[AutoScaler] Stopped.")

    def _loop(self):
        while self._running:
            try:
                self._evaluate()
            except Exception as e:
                print(f"[AutoScaler] Error: {e}")
            time.sleep(POLL_INTERVAL)

    def _evaluate(self):
        vms = list_vms()
        active_vms = [v for v in vms if v["status"] == "ACTIVE"]
        n = len(active_vms)
        print(f"[AutoScaler] Active VMs: {n}")

        if n == 0:
            print("[AutoScaler] Below minimum — provisioning VM.")
            provision_vm(1)
            return

        usages = []
        for vm in active_vms:
            usage = get_vm_cpu_usage(vm["id"])
            if usage >= 0:
                usages.append((vm["id"], usage))
                if usage > CPU_SCALE_DOWN_THRESHOLD:
                    self._last_activity[vm["id"]] = time.time()

        if not usages:
            return

        avg_cpu = sum(u for _, u in usages) / len(usages)
        print(f"[AutoScaler] Avg CPU: {avg_cpu:.1f}%")

        if avg_cpu > CPU_SCALE_UP_THRESHOLD and n < MAX_INSTANCES:
            print(f"[AutoScaler] Scaling UP to {n+1} VMs")
            provision_vm(n + 1)

        elif avg_cpu < CPU_SCALE_DOWN_THRESHOLD and n > MIN_INSTANCES:
            now = time.time()
            for vm_id, usage in usages:
                last_active = self._last_activity.get(vm_id, now)
                idle_for = now - last_active
                if idle_for > IDLE_TIMEOUT and n > MIN_INSTANCES:
                    print(f"[AutoScaler] Shutting down idle VM {vm_id}")
                    deprovision_vm(vm_id)
                    self._last_activity.pop(vm_id, None)
                    n -= 1


autoscaler = AutoScaler()


# --- Flask Endpoints ---

@app.route('/compute/provision', methods=['POST'])
def provision_endpoint():
    data = request.get_json()
    index = data.get('index', 1)
    try:
        result = provision_vm(index)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/compute/deprovision', methods=['DELETE'])
def deprovision_endpoint():
    data = request.get_json()
    vm_id = data.get('vm_id')
    result = deprovision_vm(vm_id)
    return jsonify(result), 200

@app.route('/compute/list', methods=['GET'])
def list_endpoint():
    result = list_vms()
    return jsonify(result), 200

@app.route('/compute/status', methods=['GET'])
def status_endpoint():
    vm_id = request.args.get('vm_id')
    result = get_vm_status(vm_id)
    return jsonify(result), 200

@app.route('/compute/job', methods=['POST'])
def job_endpoint():
    data = request.get_json()
    username = data.get('username')
    script = data.get('script')
    result = submit_job(username, script)
    return jsonify(result), 200

@app.route('/compute/autoscaler/start', methods=['POST'])
def autoscaler_start():
    autoscaler.start()
    return jsonify({"status": "autoscaler started"}), 200

@app.route('/compute/autoscaler/stop', methods=['POST'])
def autoscaler_stop():
    autoscaler.stop()
    return jsonify({"status": "autoscaler stopped"}), 200


if __name__ == '__main__':
    app.run(port=5006, debug=True)
