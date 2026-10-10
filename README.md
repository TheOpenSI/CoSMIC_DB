<h1 align="center">Directory Hierarchy</h1>

```md
COSMIC-DB/
├── apis/                   # CoSMIC BE API Endpoints (Implementation)
│   ├── data_models/        # Pydantic models for request validation and API responses
│   ├── table_models/       # SQLModel ORM table definitions mapped to PostgreSQL database tables
│   └── base_models.py      # SQLModel base classes inherited by both table and data models
├── auth/                   # Auth BFF (Authlib → Keycloak; session, /me, JWKS)
│   ├── claims.py           # IdP userinfo mapped to one Cosmic claim shape
│   ├── keys.py             # RS256 session keypair loading + public JWKS
│   ├── oauth.py            # Authlib OAuth2/OIDC client registry (Keycloak only)
│   ├── secrets/            # RS256 keypair (gitignored; see bins/gen_session_keys.*)
│   └── session.py          # Cosmic session cookie (joserfc, RS256)
├── bins/                   # Helper scripts, 3rd vendor binaries, etc
├── cores/                  # Central backend logic, database engines, and global configurations
├── docker/                 # Containerization resources and orchestration files
│   ├── configs/            # Non-sensitive configuration files for Docker services
│   ├── dockerfiles/        # Dockerfile for each services defined in Docker Compose file
│   ├── keycloak/           # Keycloak realm export imported on first container start
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
├── tests/                  # pytest suite for the Auth BFF
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
> setup instructions in [CoSMIC_Docker repository](https://github.com/TheOpenSI/CoSMIC_Docker)

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
> BE as a Docker container.

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
> Remember to remove `.example` suffix from each filenames.

1. **Backend service**:
- `examples/cosmic_*.example.env` &rarr; `cores/cosmic_*.env` (contains core application environment variables).

2. **PostgreSQL service**:
- `examples/postgres_*.example.txt` &rarr; `docker/secrets/postgres_*.txt` (contains PostgreSQL database credentials and configuration files).

3. **pgAdmin service**:
- `examples/pgadmin_*.example.txt` &rarr; `docker/secrets/pgadmin_*.txt` (contains pgAdmin credentials and authentication files).
- `examples/pgadmin_*.example.json` &rarr; `docker/configs/pgadmin_*.json` (contains pgAdmin server definitions and non-sensitive configuration).

4. **Auth service**:
- `examples/cosmic_auth.example.env` &rarr; `auth/cosmic_auth.env` (contains Keycloak, Authlib session, and RS256 session-key settings). See [Configuring Authentication Credentials](#0-configuring-authentication-credentials).
- Generate the RS256 session keypair used to sign the Cosmic session cookie:
  - `.\bins\gen_session_keys.ps1` (Windows) or `./bins/gen_session_keys.sh` (Linux/macOS).

5. **Keycloak service**:
- `examples/keycloak_*.example.txt` &rarr; `docker/secrets/keycloak_*.txt` (contains Keycloak admin credentials, the confidential client secret, the seeded test user, and the Google/Microsoft client credentials brokered by Keycloak).

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

From the project root directory, ensure you've completed the steps in the [Docker Configuration](#docker-configuration) section above, including [Configuring Authentication Credentials](#0-configuring-authentication-credentials). Set the Keycloak client secret, the Google/Microsoft broker credentials, and session values **before** the first `docker compose up` so Keycloak imports a matching client secret. Then start all the service using the Docker Compose file:

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
docker exec cosmic-infrastructure-postgres psql -U demo # Refer to NOTE if running on rootless mode
```
```ps1
# Windows
docker exec cosmic-infrastructure-postgres psql -U demo # Docker run through lightweight Linux VM on Windows so it's rootless by default
```

or go to **Docker Desktop**, search for `cosmic-infrastructure-postgres` service under `opensi-cosmic-infrastructure` top-level service, click on it then click on **Terminal** icon on the near top right corner.

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

### **0. Configuring Authentication Credentials**

After running `./bins/setup.sh` (Linux/MacOS) or `.\bins\setup.ps1` (Windows), the setup script copies example files into:

- `auth/cosmic_auth.env` &mdash; Keycloak, Authlib session, and RS256 session-key settings used by the backend
- `auth/secrets/session_private.pem` &mdash; the RS256 key that signs the Cosmic session cookie (generated by `bins/gen_session_keys.*`)
- `docker/secrets/keycloak_client_secret.txt` &mdash; the same Keycloak confidential-client secret, mounted into the Keycloak container

Open `auth/cosmic_auth.env` and replace the defaults below. Do **not** commit real credentials.

> [!IMPORTANT]
> `KEYCLOAK_CLIENT_SECRET` in `auth/cosmic_auth.env` **must be identical** to the value in `docker/secrets/keycloak_client_secret.txt`. If they differ, Keycloak login will fail because the backend and Keycloak will not share the same client secret. The secrets file must contain **only** the secret string (no quotes, no `KEYCLOAK_CLIENT_SECRET=` prefix, no extra spaces).

#### **Google & Microsoft (brokered by Keycloak)**

The platform itself only talks to Keycloak. Google and Microsoft are configured
as Keycloak **identity providers**, so the Keycloak login page shows the normal
username/password form plus a "Google" and a "Microsoft" button by default.

Register each provider in its own console and use **Keycloak's broker callback**
as the redirect URI (not the CoSMIC BFF):

| Provider  | Redirect URI                                                     |
| --------- | ---------------------------------------------------------------- |
| Google    | `http://localhost:8080/realms/cosmic/broker/google/endpoint`      |
| Microsoft | `http://localhost:8080/realms/cosmic/broker/microsoft/endpoint`   |

1. **Google**: [Google Cloud Console](https://console.developers.google.com/) &rarr; **APIs & Services** &rarr; **Credentials** &rarr; **Create credentials** &rarr; **OAuth client ID** (type **Web application**). Add the Google redirect URI above, then put the client id/secret in `docker/secrets/keycloak_google_client_id.txt` and `docker/secrets/keycloak_google_client_secret.txt`.
2. **Microsoft**: [Azure Portal](https://portal.azure.com/) &rarr; **App registrations** &rarr; **New registration**. Add the Microsoft redirect URI above, then put the application (client) id/secret in `docker/secrets/keycloak_microsoft_client_id.txt` and `docker/secrets/keycloak_microsoft_client_secret.txt`, and the directory (tenant) id — or `common` for multi-tenant — in `docker/secrets/keycloak_microsoft_tenant_id.txt`.

> [!IMPORTANT]
> The realm import substitutes `${KEYCLOAK_GOOGLE_*}` / `${KEYCLOAK_MICROSOFT_*}` from those secrets on first boot. Set them **before** the first `docker compose up`. To change them later, either update the identity provider in the Keycloak admin console, or remove the `cosmic-keycloak-data` volume and start again so the realm is re-imported.

#### **Keycloak client secret**

The default `KEYCLOAK_CLIENT_SECRET` is only a local example. You may keep it for a first run, but we recommend replacing it with a unique value.

Generate a unique secret:

```bash
# Linux/MacOS
uuidgen
```
```ps1
# Windows
[guid]::NewGuid().ToString()
```

Put **the same value** in both places:

1. `auth/cosmic_auth.env`:

```txt
KEYCLOAK_CLIENT_SECRET=<your-unique-secret>
```

2. `docker/secrets/keycloak_client_secret.txt` (secret only, one line):

```txt
<your-unique-secret>
```

> [!TIP]
> Set this **before** the first Keycloak start. Keycloak imports `docker/keycloak/cosmic-realm.json` on first boot and substitutes `${KEYCLOAK_CLIENT_SECRET}` from `docker/secrets/keycloak_client_secret.txt`. If you change the secret later, also update the client secret in the Keycloak admin console (**Clients** &rarr; `cosmic-fastapi-keycloak` &rarr; **Credentials**), or remove the Keycloak volume and start again so the realm is re-imported.

You can leave `KEYCLOAK_CLIENT_ID=cosmic-fastapi-keycloak` and the Keycloak URLs/realm defaults unless you have changed those in the realm export.

#### **Session keys (RS256) and `SESSION_SECRET`**

The Cosmic session cookie is a JWT signed with **RS256** using a static RSA
keypair, so the other microservices can verify it with the public key only.

- Generate the keypair with `.\bins\gen_session_keys.ps1` or `./bins/gen_session_keys.sh`. It writes `auth/secrets/session_private.pem` and `auth/secrets/session_public.pem` (gitignored).
- The public half is published at `http://localhost:8081/api/v1/auth/jwks.json` for the other services.
- `SESSION_SECRET` is now only used to sign the temporary Authlib OAuth state/nonce cookie. It is separate from the RS256 keypair.

```txt
SESSION_SECRET=<your-unique-session-secret>
SESSION_COOKIE_NAME=cosmic_session
SESSION_MAX_AGE=900
OAUTH_SESSION_COOKIE=cosmic_oauth_session
```

> [!WARNING]
> Rotating the RS256 keypair invalidates every active session (users must log in again) and invalidates cached JWKS in the other services. Rotating `SESSION_SECRET` only interrupts logins that are in flight.

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
