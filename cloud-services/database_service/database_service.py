import time
import secrets
import docker
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_PORT = 5500
MAX_INSTANCES = 100
POSTGRES_IMAGE = "postgres:15"


def _get_docker_client():
    return docker.from_env()

def _container_name(username):
    return f"db-{username}"

def _get_host_port(username):
    return BASE_PORT + (hash(username) % MAX_INSTANCES)

def _wait_for_postgres(host, port, user, password, db, retries=10):
    for _ in range(retries):
        try:
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=db)
            conn.close()
            return
        except Exception:
            time.sleep(2)
    raise TimeoutError("PostgreSQL did not become ready in time.")


# --- Core Functions ---

def provision_database(username):
    client = _get_docker_client()
    container_name = _container_name(username)

    try:
        existing = client.containers.get(container_name)
        if existing.status == "running":
            return {"status": "already_running", "container": container_name}
        else:
            existing.start()
            return {"status": "restarted", "container": container_name}
    except docker.errors.NotFound:
        pass

    password = secrets.token_urlsafe(16)
    db_name = f"{username}_db"
    db_user = username
    host_port = _get_host_port(username)

    client.containers.run(
        POSTGRES_IMAGE,
        name=container_name,
        detach=True,
        environment={
            "POSTGRES_USER": db_user,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": db_name,
        },
        ports={"5432/tcp": host_port},
        labels={"cloud.owner": username, "cloud.service": "database"},
        restart_policy={"Name": "unless-stopped"},
    )

    _wait_for_postgres(host="localhost", port=host_port, user=db_user, password=password, db=db_name)

    return {
        "status": "provisioned",
        "host": "localhost",
        "port": host_port,
        "db_name": db_name,
        "db_user": db_user,
        "password": password,
        "container": container_name,
    }


def deprovision_database(username):
    client = _get_docker_client()
    container_name = _container_name(username)

    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        return {"status": "removed", "container": container_name}
    except docker.errors.NotFound:
        return {"status": "not_found", "container": container_name}


def get_connection_info(username):
    client = _get_docker_client()
    container_name = _container_name(username)

    try:
        container = client.containers.get(container_name)
        port = _get_host_port(username)
        return {
            "status": container.status,
            "host": "localhost",
            "port": port,
            "db_name": f"{username}_db",
            "db_user": username,
            "container": container_name,
        }
    except docker.errors.NotFound:
        return {"status": "not_provisioned"}


def list_databases():
    client = _get_docker_client()
    containers = client.containers.list(filters={"label": "cloud.service=database"})
    return [
        {
            "container": c.name,
            "owner": c.labels.get("cloud.owner"),
            "status": c.status,
        }
        for c in containers
    ]


def execute_query(username, password, query):
    port = _get_host_port(username)
    db_name = f"{username}_db"
    conn = None

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=port,
            user=username,
            password=password,
            dbname=db_name,
        )
        conn.autocommit = True

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            if cur.description:
                rows = [dict(row) for row in cur.fetchall()]
                columns = [desc[0] for desc in cur.description]
                return {
                    "status": "success",
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                }
            else:
                return {
                    "status": "success",
                    "rows_affected": cur.rowcount,
                }

    except psycopg2.Error as e:
        return {"status": "error", "message": str(e)}

    finally:
        if conn:
            conn.close()


# --- Flask Endpoints ---

@app.route('/database/provision', methods=['POST'])
def provision_endpoint():
    data = request.get_json()
    username = data.get('username')
    try:
        result = provision_database(username)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/database/deprovision', methods=['DELETE'])
def deprovision_endpoint():
    data = request.get_json()
    username = data.get('username')
    result = deprovision_database(username)
    return jsonify(result), 200

@app.route('/database/info', methods=['GET'])
def info_endpoint():
    username = request.args.get('username')
    result = get_connection_info(username)
    return jsonify(result), 200

@app.route('/database/list', methods=['GET'])
def list_endpoint():
    result = list_databases()
    return jsonify(result), 200

@app.route('/database/query', methods=['POST'])
def query_endpoint():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    query = data.get('query')
    result = execute_query(username, password, query)
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(port=5004, debug=True)
