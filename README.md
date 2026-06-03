# GridLock — A Custom Cloud Infrastructure for Data Science

GridLock is a custom cloud platform built for large-scale data science. Rather than deploying an
off-the-shelf cloud, it re-implements the core services a cloud provides — authentication, elastic
compute, object storage, containerised execution, and managed databases — as a set of independent
Python microservices running on top of an OpenStack (DevStack) installation. A web frontend ties the
services together into a single application.

## Architecture

The system has three tiers:

1. **Infrastructure layer** — OpenStack (via DevStack), providing virtual machines (Nova) and object
   storage (Swift).
2. **Service layer** — six independent Flask microservices, each exposing a REST API on its own port.
3. **Frontend** — static HTML/JS pages served by a web server, calling the services.

### Services

| Service        | Port | Backend                  | Responsibility                                            |
|----------------|------|--------------------------|-----------------------------------------------------------|
| Authentication | 5001 | SQLite                   | Registration, login (JWT), profile, storage tier          |
| Storage        | 5002 | OpenStack Swift          | Buckets, file upload/download, tiered quota enforcement   |
| Normalization  | 5003 | Swift + pandas           | CSV cleaning with preview/confirm                         |
| Database       | 5004 | Docker + PostgreSQL      | Per-user PostgreSQL instances and querying                |
| Container      | 5005 | Docker                   | Run and manage containers / ML jobs                       |
| Compute        | 5006 | OpenStack Nova           | Elastic VM pool, SLA job submission, autoscaler           |

The frontend is served separately (e.g. by nginx) on port **8082**.

## Requirements

The host must have the following installed and running before the services will work:

- **Ubuntu** (developed on 22.04)
- **OpenStack** via **DevStack** (provides Nova + Swift; sourced credentials required)
- **Docker Engine** (used by the database and container services)
- **Python 3.10+**
- A web server (e.g. **nginx**) to serve the frontend
- Python packages listed in `requirements.txt`

> Note: OpenStack, Docker, and the web server are system-level dependencies and are **not** included
> in this archive. They must be installed on the host first.

## Setup

### 1. Install DevStack
Follow the official DevStack guide to install a single-node OpenStack environment. Confirm the
`cirros` image, `m1.small` flavor, and `private` network exist:

```bash
source /opt/stack/devstack/openrc admin admin
openstack image list
openstack flavor list
openstack network list
```

### 2. Create the Python environment
```bash
cd cloud-services
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Deploy the frontend
Copy the frontend pages to the web server's document root:
```bash
sudo cp frontend/*.html /var/www/html/
sudo cp frontend/logo_branco.png /var/www/html/
```
(Configure the web server to serve `/var/www/html/` on port 8082.)

## Running

Activate the environment and load OpenStack credentials, then start all six services:

```bash
cd cloud-services
source venv/bin/activate
source /opt/stack/devstack/openrc admin admin

for s in auth storage normalization database container compute; do
  (cd ${s}_service && python3 ${s}_service.py &)
done
```

Verify they are up (a `404` on the root path means a service is listening):
```bash
for p in 5001 5002 5003 5004 5005 5006; do
  echo -n "port $p: "; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:$p/
done
```

Stop all services:
```bash
pkill -f _service.py
```

## Usage

Open the frontend in a browser:
```
http://localhost:8082/auth.html
```

1. **Register** an account, then **log in** — this stores a JWT used by all pages.
2. **Storage** — create buckets, upload/download files; usage is enforced against your storage tier
   (Free / Pro / Enterprise).
3. **Normalization** — clean a CSV from a bucket (preview, then confirm).
4. **Database** — provision a personal PostgreSQL instance and run SQL queries.
5. **Containers** — run containers/jobs from an image and view their logs.
6. **Compute** — submit jobs under an SLA and provision/scale VMs (manually or via the autoscaler).

## Notes & Known Limitations

- The compute service **schedules** jobs to VMs (enforcing a 60s SLA) but does not execute the
  user's script on the VM.
- The database service derives its host port from a hash of the username; a deterministic hash would
  be more robust across restarts.
- The generated database password is shown once at provisioning and held only for the session.
- Services bind to `127.0.0.1` by default; to reach them from another machine they must bind to
  `0.0.0.0` and the relevant ports must be opened in the firewall.
- Usage accounting scans all of a user's objects per upload — fine at small scale.

## Project Structure

```
cloud-services/
  auth_service/           auth_service.py          (port 5001)
  storage_service/        storage_service.py       (port 5002)
  normalization_service/  normalization_service.py (port 5003)
  database_service/       database_service.py      (port 5004)
  container_service/      container_service.py     (port 5005)
  compute_service/        compute_service.py       (port 5006)
  frontend/               dashboard.html, auth.html, storage.html, ...
  requirements.txt
  README.md
```
