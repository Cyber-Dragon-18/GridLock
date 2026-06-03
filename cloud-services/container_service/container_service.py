import docker
from docker.errors import NotFound, ImageNotFound, APIError
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SERVICE_LABEL = "cloud.service=container"

def _get_docker_client():
    return docker.from_env()

def _container_name(username, name):
    return f"container-{username}-{name}"


# --- Core Functions ---

def run_container(username, name, image, command=None, env_vars=None, ports=None):
    client = _get_docker_client()
    full_name = _container_name(username, name)

    try:
        existing = client.containers.get(full_name)
        return {
            "status": "already_exists",
            "container": full_name,
            "state": existing.status,
        }
    except NotFound:
        pass

    try:
        container = client.containers.run(
            image=image,
            name=full_name,
            command=command,
            environment=env_vars or {},
            ports=ports or {},
            detach=True,
            labels={
                "cloud.owner": username,
                "cloud.service": "container",
                "cloud.friendly_name": name,
            },
        )
        return {
            "status": "running",
            "container": full_name,
            "container_id": container.short_id,
            "image": image,
        }
    except ImageNotFound:
        return {"status": "error", "message": f"Image '{image}' not found."}
    except APIError as e:
        return {"status": "error", "message": str(e)}


def stop_container(username, name):
    client = _get_docker_client()
    full_name = _container_name(username, name)
    try:
        container = client.containers.get(full_name)
        if container.labels.get("cloud.owner") != username:
            return {"status": "error", "message": "Permission denied."}
        container.stop()
        return {"status": "stopped", "container": full_name}
    except NotFound:
        return {"status": "not_found", "container": full_name}


def restart_container(username, name):
    client = _get_docker_client()
    full_name = _container_name(username, name)
    try:
        container = client.containers.get(full_name)
        if container.labels.get("cloud.owner") != username:
            return {"status": "error", "message": "Permission denied."}
        container.restart()
        return {"status": "restarted", "container": full_name}
    except NotFound:
        return {"status": "not_found", "container": full_name}


def remove_container(username, name, force=False):
    client = _get_docker_client()
    full_name = _container_name(username, name)
    try:
        container = client.containers.get(full_name)
        if container.labels.get("cloud.owner") != username:
            return {"status": "error", "message": "Permission denied."}
        container.remove(force=force)
        return {"status": "removed", "container": full_name}
    except NotFound:
        return {"status": "not_found", "container": full_name}


def list_containers(username):
    client = _get_docker_client()
    containers = client.containers.list(
        all=True,
        filters={"label": [SERVICE_LABEL, f"cloud.owner={username}"]},
    )
    return [
        {
            "name": c.labels.get("cloud.friendly_name", c.name),
            "full_name": c.name,
            "image": c.image.tags[0] if c.image.tags else "unknown",
            "status": c.status,
            "container_id": c.short_id,
        }
        for c in containers
    ]


def get_logs(username, name, tail=100):
    client = _get_docker_client()
    full_name = _container_name(username, name)
    try:
        container = client.containers.get(full_name)
        if container.labels.get("cloud.owner") != username:
            return {"status": "error", "message": "Permission denied."}
        logs = container.logs(tail=tail).decode("utf-8")
        return {"status": "success", "container": full_name, "logs": logs}
    except NotFound:
        return {"status": "not_found", "container": full_name}


def pull_image(image):
    client = _get_docker_client()
    try:
        client.images.pull(image)
        return {"status": "pulled", "image": image}
    except APIError as e:
        return {"status": "error", "message": str(e)}


# --- Flask Endpoints ---

@app.route('/container/run', methods=['POST'])
def run_endpoint():
    data = request.get_json()
    username = data.get('username')
    name = data.get('name')
    image = data.get('image')
    command = data.get('command')
    env_vars = data.get('env_vars')
    ports = data.get('ports')
    result = run_container(username, name, image, command, env_vars, ports)
    return jsonify(result), 201

@app.route('/container/stop', methods=['POST'])
def stop_endpoint():
    data = request.get_json()
    username = data.get('username')
    name = data.get('name')
    result = stop_container(username, name)
    return jsonify(result), 200

@app.route('/container/restart', methods=['POST'])
def restart_endpoint():
    data = request.get_json()
    username = data.get('username')
    name = data.get('name')
    result = restart_container(username, name)
    return jsonify(result), 200

@app.route('/container/remove', methods=['DELETE'])
def remove_endpoint():
    data = request.get_json()
    username = data.get('username')
    name = data.get('name')
    force = data.get('force', False)
    result = remove_container(username, name, force)
    return jsonify(result), 200

@app.route('/container/list', methods=['GET'])
def list_endpoint():
    username = request.args.get('username')
    result = list_containers(username)
    return jsonify(result), 200

@app.route('/container/logs', methods=['GET'])
def logs_endpoint():
    username = request.args.get('username')
    name = request.args.get('name')
    tail = int(request.args.get('tail', 100))
    result = get_logs(username, name, tail)
    return jsonify(result), 200

@app.route('/container/pull', methods=['POST'])
def pull_endpoint():
    data = request.get_json()
    image = data.get('image')
    result = pull_image(image)
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(port=5005, debug=True)
