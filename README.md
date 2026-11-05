# GridLock — A Custom Cloud Infrastructure for Data Science

GridLock is a custom cloud platform built for large-scale data science. Rather than deploying an off-the-shelf cloud, it re-implements core cloud primitives — authentication, elastic compute, object storage, containerised execution, and managed databases — as a set of independent Python microservices running on top of an OpenStack (DevStack) installation. A web frontend ties the services together into a single application.

## Architecture

The system has three tiers:

1. **Infrastructure layer** — OpenStack (via DevStack), providing virtual machines (Nova) and object storage (Swift).
2. **Service layer** — Six independent Flask microservices, each exposing a REST API on its own dedicated port.
3. **Frontend** — Static HTML/JS pages served by a web server (e.g., Nginx), communicating directly with the service APIs.

### Services

| Service | Port | Backend | Responsibility |
| :--- | :--- | :--- | :--- |
| **Authentication** | `5001` | SQLite | Registration, login (JWT), profile, storage tier |
| **Storage** | `5002` | OpenStack Swift | Buckets, file upload/download, tiered quota enforcement |
| **Normalization** | `5003` | Swift + pandas | CSV cleaning with preview/confirm workflow |
| **Database** | `5004` | Docker + PostgreSQL | Per-user PostgreSQL instances and ad-hoc querying |
| **Container** | `5005` | Docker | Run and manage containers / ML task execution |
| **Compute** | `5006` | OpenStack Nova | Elastic VM pool, SLA job submission, autoscaler |

The frontend is served separately on port **8082**.

## Requirements

The host machine must have the following installed and running before starting the services:

- **Ubuntu** (tested on 22.04 LTS)
- **OpenStack** via **DevStack** (provides Nova + Swift; sourced credentials required)
- **Docker Engine** (used by Database and Container services)
- **Python 3.10+**
- A web server (e.g. **Nginx**) to serve the frontend
- Python packages listed in `requirements.txt`

> **Note:** OpenStack, Docker, and the web server are host-level dependencies and must be installed and active prior to launching the platform.

## Setup

### 1. Configure DevStack
Confirm your single-node OpenStack environment is running and verify that the `cirros` image, `m1.small` flavor, and `private` network are present:

```bash
source /opt/stack/devstack/openrc admin admin
openstack image list
openstack flavor list
openstack network list
```

### 2. Set Up the Python Environment
```bash
cd cloud-services
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Deploy the Frontend
Copy the static assets to your web server document root:
```bash
sudo cp frontend/*.html /var/www/html/
sudo cp frontend/logo_branco.png /var/www/html/
```
Ensure your web server configuration serves `/var/www/html/` on port **8082**.

## Running

Activate the environment, source your OpenStack credentials, and start all six services in the background:

```bash
cd cloud-services
source venv/bin/activate
source /opt/stack/devstack/openrc admin admin

for s in auth storage normalization database container compute; do
  (cd ${s}_service && python3 ${s}_service.py &)
done
```

Verify the services are listening (a `404` or valid response on the root path indicates the listener is active):
```bash
for p in 5001 5002 5003 5004 5005 5006; do
  echo -n "Port $p: " && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:$p/
done
```

To stop all services:
```bash
pkill -f _service.py
```

## Usage

Navigate to the frontend in your browser:
```text
http://localhost:8082/auth.html
```

1. **Authentication:** Register an account and sign in. The received JWT token is stored locally and used across all subsequent views.
2. **Storage:** Create Swift buckets and upload/download files. Usage limits are validated against the user's tier (*Free*, *Pro*, or *Enterprise*).
3. **Normalization:** Clean raw CSV datasets stored in Swift via a preview-and-confirm workflow.
4. **Database:** Provision dedicated containerized PostgreSQL instances and run SQL queries through the web interface.
5. **Containers:** Launch Docker containers from specified images and stream execution logs.
6. **Compute:** Submit workload jobs with defined SLAs (60s threshold) and monitor VM auto-scaling in the Nova pool.

## Technical Considerations & Known Limitations

- **Job Execution on Compute VMs:** The compute service schedules jobs to VMs to meet the 60s SLA threshold, but does not inject or execute arbitrary user scripts inside the CirrOS guest instances.
- **Port Mapping:** The database service dynamically derives host container ports from a hash of the username; a persistent state table would provide greater stability across container restarts.
- **Credential Storage:** Generated database passwords are displayed once upon provisioning and retained in session memory.
- **Network Binding:** Microservices bind to `127.0.0.1` by default; cross-host deployments require binding to `0.0.0.0` with matching firewall policies.
- **Quota Accounting:** Quota calculations currently scan user-owned objects per upload operation, which is intended for local/evaluation workloads rather than high-concurrency production storage.

## Project Structure

```text
cloud-services/
├── auth_service/
│   └── auth_service.py          # Port 5001 (JWT, SQLite auth)
├── storage_service/
│   └── storage_service.py       # Port 5002 (Swift object storage)
├── normalization_service/
│   └── normalization_service.py # Port 5003 (Pandas data cleaning)
├── database_service/
│   └── database_service.py      # Port 5004 (Dockerized PostgreSQL)
├── container_service/
│   └── container_service.py     # Port 5005 (Docker task execution)
├── compute_service/
│   └── compute_service.py       # Port 5006 (Nova VM & SLA autoscaler)
├── frontend/
│   ├── auth.html
│   ├── dashboard.html
│   └── storage.html
├── requirements.txt
└── README.md
```

## Author

Rodrigo Coelho · [GitHub](https://github.com/Cyber-Dragon-18) · [Website](https://cyber-dragon-18.github.io) | Catarina Aguiar [GitHub](https://github.com/catarina-aguiar)
