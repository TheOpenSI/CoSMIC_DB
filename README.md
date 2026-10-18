<h1 align="center">Directory Hierarchy</h1>

```md
COSMIC-DB/
├── apis/                   # CoSMIC BE API Endpoints (Implementation)
│   ├── data_models/        # Pydantic models for request validation and API responses
│   ├── table_models/       # SQLModel ORM table definitions mapped to PostgreSQL database tables
│   └── base_models.py      # SQLModel base classes inherited by both table and data models
├── bins/                   # Helper scripts, 3rd vendor binaries, etc
├── cores/                  # Central backend logic, database engines, and global configurations
├── docker/                 # Containerization resources and orchestration files
│   ├── configs/            # Non-sensitive configuration files for Docker services
│   ├── dockerfiles/        # Dockerfile for each services defined in Docker Compose file
│   └── secrets/            # Secure storage for sensitive data like database credentials
├── examples/               # Template files and default values for rapid environment setup
├── migrations/             # Alembic database migration scripts and utilities
│   ├── utils/              # Shell scripts for running migrations automatically on container startup
│   ├── versions/           # Versioned Alembic migration files for schema creation and data pre-population
│   └── README              # Alembic-generated readme describing the migration configuration
├── routers/                # CoSMIC BE API Endpoints (Interface)
│   ├── api_endpoints/      # Requests to CoSMIC BE's API endpoints goes here
│   └── normal_endpoints/   # Requests to CoSMIC BE's non-API endpoints goes here
├── scripts/                # One-off helper scripts (e.g. data seeding)
├── types/                  # Shared type definitions used across the application
│   └── api_responses/      # Pydantic response wrapper models returned to API clients
├── utils/                  # Helper functions and shared utility scripts
├── .dockerignore           # Files excluded from Docker builds
├── .gitattributes          # Git configuration for path attributes
├── .gitignore              # Files excluded from version control
├── .python-version         # Pinned Python version for the project (benefical to `uv` only)
├── CONTRIBUTING            # Guidelines for project contributors
├── LICENSE                 # Project licensing information (MIT)
├── README.md               # This's what you're seeing right now
├── __init__.py             # Package initialisation (mainly for relative import usages)
├── alembic.ini             # Alembic configuration file defining migration script location and logging
├── compose.yaml            # Docker Compose specification for orchestrating all BE-only services
├── main.py                 # Primary entry point for FastAPI application
├── pyproject.toml          # Project metadata and dependency definitions
└── uv.lock                 # Pinned dependency lockfile via `uv`
```

---
# Quick Start

Before setting up, decide which one is the correct purpose when you get to this modular repository:

> [!NOTE]
> The rest of this guide covers **Purpose 1**. For **Purpose 2**, refer to the
> setup instructions in [cosmic-docker repository](https://github.com/TheOpenSI/cosmic-docker)

1. **Module-only**: you are working on this part of the project in isolation (e.g., only CoSMIC BE).
2. **Full-stack**: you need an end-to-end test run across all services (**Front-end** &rarr; **Back-end** &rarr; **CoSMIC**).

Next, ensure you have the appropriate tools installed depending on your chosen execution method. This guide supports:

- **Native setup** (running **CoSMIC BE** directly on your machine)
- **Docker setup** (running **CoSMIC BE** in isolated containers)


| **Tool**   | **Docker Setup**                       | **Native Setup**                               |
| ---------- | -------------------------------------- | ---------------------------------------------- |
| Docker     | $\textcolor{green}{\text{Mandatory}}$  | $\textcolor{red}{\text{Not required}}$         |
| Python     | $\textcolor{red}{\text{Not required}}$ | $\textcolor{green}{\text{Mandatory (v3.14+)}}$ |
| uv         | $\textcolor{red}{\text{Not required}}$ | $\textcolor{green}{\text{Mandatory (latest)}}$ |
| PostgreSQL | $\textcolor{red}{\text{Not required}}$ | $\textcolor{green}{\text{Mandatory (v18+)}}$   |
| pgAdmin    | $\textcolor{red}{\text{Not required}}$ | $\textcolor{yellow}{\text{Optional}}$          |


Then, start by cloning the repository using your preferred method:

```bash
# Linux/MacOS
git clone https://github.com/TheOpenSI/CoSMIC_DB.git    # Using HTTPS (recommended for most users)
git clone git@github.com:TheOpenSI/CoSMIC_DB.git        # Using SSH (recommended if you've SSH keys configured)
```
```ps1
# Windows
git clone https://github.com/TheOpenSI/CoSMIC_DB.git    # Using HTTPS (recommended for most users)
git clone git@github.com:TheOpenSI/CoSMIC_DB.git        # Using SSH (recommended if you've SSH keys configured)
```

Once cloned, navigate to the project root directory:

```bash
# Linux/MacOS
cd CoSMIC_DB/
```
```ps1
# Windows
Set-Location CoSMIC_DB\
```

---
# Understanding Configuration Setup

Our backend expects configuration files to be organised in specific locations depending on your chosen setup method. Understanding this structure will help you prepare the environment correctly.

> [!TIP]
> You can follow the instructions below to understand what these 2 scripts will
> do, or simply run it to automatically configure your environment for running
> database micro-service as a Docker container.

```bash
# Linux/MacOS
./bins/setup.sh
```
```ps1
# Windows
.\bins\setup.ps1
```

## Docker Configuration

Create the necessary directories first:

```bash
# Linux/MacOS
mkdir -p docker/{secrets,configs}
```
```ps1
# Windows
New-Item -Type Directory -Name secrets -Path .\docker\
New-Item -Type Directory -Name configs -Path .\docker\
```

Then, copy the following files from the `examples/` directory to the following location:

> [!IMPORTANT]
> Remove `.example` suffix from each filename.

1. **Backend service**:
- `examples/cosmic_*.example.env` &rarr; `cores/cosmic_*.env` (contains core application environment variables).

2. **PostgreSQL service**:
- `examples/postgres_*.example.txt` &rarr; `docker/secrets/postgres_*.txt` (contains PostgreSQL database credentials and configuration files).

3. **pgAdmin service**:
- `examples/pgadmin_*.example.txt` &rarr; `docker/secrets/pgadmin_*.txt` (contains pgAdmin credentials and authentication files).
- `examples/pgadmin_*.example.json` &rarr; `docker/configs/pgadmin_*.json` (contains pgAdmin server definitions and non-sensitive configuration).

> [!TIP]
> Before finalising these files, review and adjust default values (Keep default setting if you're unsure about whether or not to modify it):
> - Password
> - Username
> - Port
> - Etc

## Native Configuration

> [!TIP]
> The `.env` file approach is recommended as it keeps your configuration
> organised and prevents accidentally committing secrets to version control.
> Make sure to add `.env` to your `.gitignore` file.

### **Option 1: Create a `.env` file in the `cores/` directory**

First, copy the `examples/cosmic_*.example.env` file to the correct location:

```bash
 # Linux/MacOS
cp ../examples/cosmic_*.example.env ./cores/cosmic_*.env
```
```ps1
# Windows
Copy-Item -Path ..\examples\cosmic_*.example.env -Destination .\cores\cosmic_*.env
```

Then, edit the `cores/cosmic_*.env` file to set your desired configuration values.

### **Option 2: Set environment variables directly in your shell**

Alternatively, export variables directly before running the application:

```bash
# Linux/MacOS
export DB_DIALECT=postgresql
export DB_DRIVER=psycopg
export DB_USER=postgres
export DB_PASSWORD=""
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=postgres
export OPENAI_API_KEY=
```
```ps1
# Windows
$env:DB_DIALECT="postgresql"
$env:DB_DRIVER="psycopg"
$env:DB_USER="postgres"
$env:DB_PASSWORD=""
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="postgres"
$env:OPENAI_API_KEY=
```

---
# Setup & Execution

> [!TIP]
> Docker provides an isolated environment where all services run in containers.
> This approach is recommended if you want to avoid installing PostgreSQL and
> other dependencies directly on your machine.

## Docker Setup

> [!NOTE]
> It's possible to run Docker in rootless mode on Linux. However, the way to set
> it up is different on each Linux distros. Please refer to [this](https://docs.docker.com/engine/install) and [this](https://docs.docker.com/engine/security/rootless/)
> (all sourced from Docker documentation) to choose the one that fits for your
> current Linux distro.

Before you begin, ensure you have **Docker** & **Docker Compose** installed on your system. These are required to run the platform:

1. [**Docker**](https://docs.docker.com/get-docker/)
2. [**Docker Compose**](https://docs.docker.com/compose/install/)

### **1. Starting Docker Services**

From the project root directory, ensure you've completed the steps in the [Docker Configuration](#docker-configuration) section above. Then start all the service using the Docker Compose file:

```bash
# Linux/MacOS
docker compose up --build -d # Refer to NOTE if running on rootless mode
```
```ps1
# Windows
docker compose up --build -d # Docker run through lightweight Linux VM on Windows so it's rootless by default
```

### **2. Verifying Docker Services**

Once the containers are running, you can verify that all services are working correctly by these way:

1. **FastAPI**: [localhost:3000/docs](http://localhost:3000/docs)
2. **pgAdmin**: [localhost:5050](http://localhost:5050) **(use credentials from `docker/secrets/pgadmin_*.txt`, and `PGADMIN_DEFAULT_EMAIL` environment value in compose file)**
3. **PostgreSQL**:
- We disabled direct access by default as this's totally viewable from **pgAdmin**. However, you can still do it by typing this in your terminal:

```bash
# Linux/MacOS
docker exec cosmic-postgres psql -U demo # Refer to NOTE if running on rootless mode
```
```ps1
# Windows
docker exec cosmic-postgres psql -U demo # Docker run through lightweight Linux VM on Windows so it's rootless by default
```

or go to **Docker Desktop**, search for `cosmic-postgres` service under `opensi-cosmic` top-level service, click on it then click on **Terminal** icon on the near top right corner.

If the connection is successful, you'll see the PostgreSQL prompt, which looks like this:

```
psql (18.3)
Type "help" for help.

postgres=#
```

The version number and exact format may vary depending on your PostgreSQL installation, but the prompt indicates a successful connection.

## Native Setup

Before you begin, ensure you have `python (v3.14+)`, `uv`, and `PostgreSQL (v18+)` running on your system:

```bash
# Linux/MacOS
python --version
uv --version
psql --version
```
```ps1
# Windows
py --version
uv --version
psql --version
```

### **1. Installing Dependencies**

Our backend uses **Python (v3.14+)** with the `uv` package manager for dependency management. Once **PostgreSQL (v18+)** is running and you're in the project root directory (`CoSMIC_DB/`), install the project's Python dependencies:

```bash
# Linux/MacOS
uv sync --frozen --no-cache
```
```ps1
# Windows
uv sync --frozen --no-cache
```

### **2. Starting Backend Server**

After dependencies are installed, ensure you've completed the steps from the [Native Configuration](#native-configuration) section above. Then, start the FastAPI development server:

```bash
# Linux/MacOS
uv run fastapi dev
```
```ps1
# Windows
uv run fastapi dev
```

### **3. Verifying Native Setup**

You can now verify that the backend is running correctly by these way:

1. **FastAPI**: [localhost:8000/docs](http://localhost:8000/docs)
2. **pgAdmin**:
- On `Windows/MacOS`, search for and open the **pgAdmin 4** application from your applications menu.
- On `Linux`, search for pgAdmin or type `pgadmin4` in your terminal to start the application.
- Default credentials on all OS environment are:

```txt
Host:       postgres
Username:   postgres
Password:   none, unless you set it explicitly during installation setup
Database:   postgres
```

3. **PostgreSQL**:
- We disabled direct access by default as this's totally viewable from **pgAdmin**. However, you can still do it by typing this in your terminal:

```bash
psql -U postgres # Linux/MacOS
```
```ps1
psql -U postgres # Windows
```

If the connection is successful, you'll see the PostgreSQL prompt, which looks like this:

```
psql (18.3)
Type "help" for help.

postgres=#
```

The version number and exact format may vary depending on your PostgreSQL installation, but the prompt indicates a successful connection.
