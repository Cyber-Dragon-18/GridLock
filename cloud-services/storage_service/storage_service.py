from flask import Flask, request, jsonify
from flask_cors import CORS
import openstack
import requests

app = Flask(__name__)
CORS(app)

AUTH_SERVICE = "http://localhost:5001"

def get_connection():
    return openstack.connect()


# --- Usage / Quota helpers ---

def get_user_usage(username):
    """Total bytes stored across all of this user's containers."""
    conn = get_connection()
    total = 0
    for c in conn.object_store.containers():
        if c.name.startswith(f"{username}-"):
            for obj in conn.object_store.objects(c.name):
                total += (obj.content_length or 0)
    return total

def get_user_limit(username):
    """Ask the auth service for this user's tier limit (username is the email)."""
    try:
        r = requests.get(f"{AUTH_SERVICE}/limit", params={"email": username}, timeout=5)
        if r.ok:
            return r.json().get("limit_bytes")
    except Exception:
        pass
    return None  # unknown → don't block


# --- Container Operations ---

def create_container(username, container_name):
    conn = get_connection()
    full_name = f"{username}-{container_name}"
    conn.object_store.create_container(full_name)
    return {"status": "created", "container": full_name}

def list_containers(username):
    conn = get_connection()
    containers = conn.object_store.containers()
    user_containers = [c.name for c in containers if c.name.startswith(f"{username}-")]
    return user_containers

def delete_container(username, container_name):
    conn = get_connection()
    full_name = f"{username}-{container_name}"
    for obj in conn.object_store.objects(full_name):
        conn.object_store.delete_object(obj.name, container=full_name)
    conn.object_store.delete_container(full_name)
    return {"status": "deleted", "container": full_name}

def upload_file(username, container_name, object_name, data):
    conn = get_connection()
    full_container = f"{username}-{container_name}"
    conn.object_store.upload_object(
        container=full_container,
        name=object_name,
        data=data
    )
    return {"status": "uploaded", "object": object_name, "container": full_container}

def download_file(username, container_name, object_name):
    conn = get_connection()
    full_container = f"{username}-{container_name}"
    data = conn.object_store.download_object(object_name, container=full_container)
    return data

def list_files(username, container_name):
    conn = get_connection()
    full_container = f"{username}-{container_name}"
    objects = conn.object_store.objects(full_container)
    return [{"name": obj.name, "size_bytes": obj.content_length} for obj in objects]

def delete_file(username, container_name, object_name):
    conn = get_connection()
    full_container = f"{username}-{container_name}"
    conn.object_store.delete_object(object_name, container=full_container)
    return {"status": "deleted", "object": object_name}


# --- Flask Endpoints ---

@app.route('/container/create', methods=['POST'])
def create_container_endpoint():
    data = request.get_json()
    username = data.get('username')
    container_name = data.get('container_name')
    result = create_container(username, container_name)
    return jsonify(result), 201

@app.route('/container/list', methods=['GET'])
def list_containers_endpoint():
    username = request.args.get('username')
    result = list_containers(username)
    return jsonify(result), 200

@app.route('/container/delete', methods=['DELETE'])
def delete_container_endpoint():
    data = request.get_json()
    username = data.get('username')
    container_name = data.get('container_name')
    result = delete_container(username, container_name)
    return jsonify(result), 200

@app.route('/usage', methods=['GET'])
def usage_endpoint():
    username = request.args.get('username')
    used = get_user_usage(username)
    limit = get_user_limit(username)
    return jsonify({"used_bytes": used, "limit_bytes": limit}), 200

@app.route('/file/upload', methods=['POST'])
def upload_file_endpoint():
    username = request.form.get('username')
    container_name = request.form.get('container_name')
    file = request.files.get('file')
    object_name = file.filename
    data = file.read()

    # --- Quota enforcement ---
    limit = get_user_limit(username)
    if limit is not None:
        used = get_user_usage(username)
        incoming = len(data)
        if used + incoming > limit:
            return jsonify({
                "status": "error",
                "message": "Storage quota exceeded.",
                "used_bytes": used,
                "incoming_bytes": incoming,
                "limit_bytes": limit,
            }), 413

    result = upload_file(username, container_name, object_name, data)
    return jsonify(result), 201

@app.route('/file/download', methods=['GET'])
def download_file_endpoint():
    username = request.args.get('username')
    container_name = request.args.get('container_name')
    object_name = request.args.get('object_name')
    data = download_file(username, container_name, object_name)
    from flask import Response
    return Response(data, headers={
        "Content-Disposition": f'attachment; filename="{object_name}"',
        "Content-Type": "application/octet-stream",
    })

@app.route('/file/list', methods=['GET'])
def list_files_endpoint():
    username = request.args.get('username')
    container_name = request.args.get('container_name')
    result = list_files(username, container_name)
    return jsonify(result), 200

@app.route('/file/delete', methods=['DELETE'])
def delete_file_endpoint():
    data = request.get_json()
    username = data.get('username')
    container_name = data.get('container_name')
    object_name = data.get('object_name')
    result = delete_file(username, container_name, object_name)
    return jsonify(result), 200

if __name__ == '__main__':
    app.run(port=5002, debug=True)
