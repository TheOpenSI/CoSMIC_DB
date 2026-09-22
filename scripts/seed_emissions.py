"""
scripts/seed_emissions.py

Generates fake CodeCarbon-style emissions rows AND fake chatbox histories
(with input_token / output_token) and inserts them DIRECTLY into PostgreSQL
via psycopg, bypassing the FastAPI layer.

There is no tokens table. Token usage lives in chatboxes.details JSONB.
Backdated timestamps are required for the 3/6/12 month dashboard charts.

User IDs are fetched from GET /users so they stay valid after a fresh rebuild.
Run from inside of the docker container to ensure all libraries are available.
    docker exec -it cosmic-backend-fastapi /bin/bash

Usage (one command seeds both tables):
    uv run --group dev scripts/seed_emissions.py --users 1
    uv run --group dev scripts/seed_emissions.py --rows 50 --users 1 --days-back 180 --chatboxes 6 --messages 12
"""

### Core modules ###
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from json import loads
from random import choice, randint, uniform
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4, uuid7

### Third-party modules ###
from psycopg import connect
from psycopg.types.json import Jsonb


# ── API / DB CONNECTION ────────────────────────────────────────────────────
API_BASE_URL: str = "http://127.0.0.1:8000"
USERS_ENDPOINT: str = f"{API_BASE_URL}/api/v1/users/"

# DB_HOST: str = "localhost"   # host machine, after port mapping 5432:5432
DB_HOST: str = "database"   # host machine (USING Docker), after port mapping 5432:5432
DB_PORT: int = 5432
DB_NAME: str = "demo"
DB_USER: str = "demo"
DB_PASSWORD: str = "demo123"
# ────────────────────────────────────────────────────────────────────────────

# ── FAKE DATA CONFIG — tweak these to change realism / variety ────────────
REGIONS: list[str] = [
    "new south wales", "victoria", "queensland",
    "western australia", "south australia", "tasmania",
]

OS_STRINGS: list[str] = [
    "Linux-6.6.114.1-microsoft-standard-WSL2-aarch64-with-glibc2.41",
    "Linux-5.15.0-generic-x86_64-with-glibc2.35",
    "Linux-6.8.0-aws-x86_64-with-glibc2.39",
]

CPU_MODELS: list[str] = [
    "Oryon",
    "AMD EPYC 7763",
    "Intel Xeon Platinum 8275CL",
]

TRACKING_MODES: list[str] = ["process", "machine"]

CHATBOX_NAMES: list[str] = [
    "Carbon footprint",
    "Scope 3 questions",
    "Model comparison",
    "Energy report",
    "Research session",
    "Weekly review",
]

CHAT_TURNS: list[tuple[str, str]] = [
    (
        "What is my carbon footprint this month?",
        "Your recent compute sessions produced a small amount of CO2. Check the dashboard trend for the exact kg value.",
    ),
    (
        "How many tokens did the last query use?",
        "Token counts are stored per inquiry in the chat history. Input tokens are usually larger than output tokens.",
    ),
    (
        "Compare CPU and GPU power for my last run.",
        "CPU and GPU power are recorded per emissions row. GPU may be zero if the run had no GPU.",
    ),
    (
        "Show a 6 month emissions trend.",
        "Use the dashboard 6M range. Months with no rows appear as gaps rather than zeros.",
    ),
    (
        "What region is the grid intensity based on?",
        "Seeded rows use Australian regions. Intensity is an approximation for local testing only.",
    ),
]

# NSW grid carbon intensity (kg CO2/kWh)
GRID_INTENSITY_NSW: float = 2.548692
# ────────────────────────────────────────────────────────────────────────────

INSERT_EMISSIONS_SQL: str = """
    INSERT INTO emissions (
        id, "timestamp", run_id, duration, emissions, emissions_rate,
        cpu_power, gpu_power, ram_power, cpu_energy, gpu_energy, ram_energy,
        energy_consumed, water_consumed, region, cloud_provider, cloud_region,
        os, cpu_count, cpu_model, gpu_count, gpu_model, longitude, latitude,
        ram_total_size, tracking_mode, cpu_utilization_percent,
        gpu_utilization_percent, ram_utilization_percent, ram_used_gb,
        on_cloud, pue, wue, user_id
    ) VALUES (
        %(id)s, %(timestamp)s, %(run_id)s, %(duration)s, %(emissions)s, %(emissions_rate)s,
        %(cpu_power)s, %(gpu_power)s, %(ram_power)s, %(cpu_energy)s, %(gpu_energy)s, %(ram_energy)s,
        %(energy_consumed)s, %(water_consumed)s, %(region)s, %(cloud_provider)s, %(cloud_region)s,
        %(os)s, %(cpu_count)s, %(cpu_model)s, %(gpu_count)s, %(gpu_model)s, %(longitude)s, %(latitude)s,
        %(ram_total_size)s, %(tracking_mode)s, %(cpu_utilization_percent)s,
        %(gpu_utilization_percent)s, %(ram_utilization_percent)s, %(ram_used_gb)s,
        %(on_cloud)s, %(pue)s, %(wue)s, %(user_id)s
    )
"""

INSERT_CHATBOXES_SQL: str = """
    INSERT INTO chatboxes (
        id, user_id, name, details, create_on
    ) VALUES (
        %(id)s, %(user_id)s, %(name)s, %(details)s, %(create_on)s
    )
"""


def fetch_user_ids() -> list[str]:
    """
    Call GET /api/v1/users/ and return each user UUID.

    user_id has a FOREIGN KEY referencing users(id), so these must be real
    IDs from the current database (they change on a fresh rebuild).
    """
    try:
        with urlopen(USERS_ENDPOINT, timeout=10) as response:
            payload = loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(
            f"Failed to fetch users from {USERS_ENDPOINT}. "
            "Is cosmic-backend-fastapi running on port 8000?"
        ) from exc

    users = payload.get("result") or []
    user_ids = [str(user["id"]) for user in users if "id" in user]

    if not user_ids:
        raise RuntimeError(
            "GET /api/v1/users/ returned no users. "
            "Create at least one user before seeding dashboard data."
        )

    return user_ids


def get_user_id_pool(num_users: int) -> list[str]:
    """Return up to `num_users` real user IDs from GET /users."""
    real_user_ids = fetch_user_ids()

    if num_users > len(real_user_ids):
        print(
            f"NOTE: --users {num_users} requested, but only "
            f"{len(real_user_ids)} user(s) exist. Using all {len(real_user_ids)}."
        )
        return real_user_ids

    return real_user_ids[:num_users]


def random_backdated_timestamp(days_back: int) -> datetime:
    """Random timestamp within the last `days_back` days, timezone-aware UTC."""
    now = datetime.now(tz=timezone.utc)
    delta_seconds = randint(0, days_back * 24 * 60 * 60)
    return now - timedelta(seconds=delta_seconds)


def build_fake_row(user_id: str, days_back: int) -> dict:
    """Build a single fake emissions row with every column populated."""
    duration = round(uniform(8.0, 28.0), 6)
    cpu_power = round(uniform(0.005, 0.035), 10)
    gpu_power = round(uniform(0.005, 0.035), 10)
    ram_power = 3.0
    cpu_energy = round(cpu_power * duration / 3_600_000, 12)
    gpu_energy = round(gpu_power * duration / 3_600_000, 12)
    ram_energy = round(ram_power * duration / 3_600_000, 12)
    energy_consumed = round(cpu_energy + gpu_energy + ram_energy, 12)

    emissions = round(energy_consumed * GRID_INTENSITY_NSW, 12)
    emissions_rate = round(emissions / duration, 12)

    cpu_utilization = round(uniform(55.0, 85.0), 6)
    ram_utilization = round(uniform(57.0, 65.0), 6)
    ram_used_gb = round(uniform(4.0, 8.0), 6)

    return {
        "id": str(uuid7()),
        "timestamp": random_backdated_timestamp(days_back),
        "run_id": str(uuid4()),
        "duration": duration,
        "emissions": emissions,
        "emissions_rate": emissions_rate,
        "cpu_power": cpu_power,
        "gpu_power": gpu_power,
        "ram_power": ram_power,
        "cpu_energy": cpu_energy,
        "gpu_energy": gpu_energy,
        "ram_energy": ram_energy,
        "energy_consumed": energy_consumed,
        "water_consumed": 0.0,
        "region": choice(REGIONS),
        "cloud_provider": "",
        "cloud_region": "",
        "os": choice(OS_STRINGS),
        "cpu_count": 10,
        "cpu_model": choice(CPU_MODELS),
        "gpu_count": 0,
        "gpu_model": "Tested with no GPU",
        "longitude": round(uniform(-180.0, 180.0), 6),
        "latitude": round(uniform(-90.0, 90.0), 6),
        "ram_total_size": round(uniform(4.0, 16.0), 6),
        "tracking_mode": choice(TRACKING_MODES),
        "cpu_utilization_percent": cpu_utilization,
        "gpu_utilization_percent": 0.0,
        "ram_utilization_percent": ram_utilization,
        "ram_used_gb": ram_used_gb,
        "on_cloud": "N",
        "pue": 1.0,
        "wue": 0.0,
        "user_id": user_id,
    }


def build_fake_history(query_at: datetime) -> dict:
    """One chatboxes.details item. Rolling token charts bucket on query_create_on."""
    user_query, llm_response = choice(CHAT_TURNS)
    respond_at = query_at + timedelta(seconds=randint(2, 30))

    return {
        "inquiry_cycle_id": str(uuid7()),
        "user_role": "user",
        "user_query": user_query,
        "query_create_on": query_at.isoformat(),
        "llm_role": "assistant",
        "llm_response": llm_response,
        "response_create_on": respond_at.isoformat(),
        "input_token": randint(120, 2500),
        "output_token": randint(20, 400),
    }


def build_fake_chatbox(user_id: str, days_back: int, num_messages: int, index: int) -> dict:
    timestamps = sorted(
        random_backdated_timestamp(days_back) for _ in range(num_messages)
    )
    details = [build_fake_history(query_at) for query_at in timestamps]
    create_on = timestamps[0] - timedelta(seconds=randint(1, 60))

    return {
        "id": str(uuid7()),
        "user_id": user_id,
        "name": f"{choice(CHATBOX_NAMES)} {index + 1}",
        "details": Jsonb(details),
        "create_on": create_on,
    }


def seed(
    num_rows: int,
    num_users: int,
    days_back: int,
    num_chatboxes: int,
    num_messages: int,
) -> None:
    user_ids = get_user_id_pool(num_users)
    print(
        f"Seeding {num_rows} emission row(s) and {num_chatboxes} chatbox(es) "
        f"({num_messages} message(s) each) across {len(user_ids)} user(s)..."
    )
    print("Using user IDs:")
    for uid in user_ids:
        print(f"  - {uid}")
    print()

    conn_str = (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASSWORD}"
    )

    emission_rows = [
        build_fake_row(user_id=choice(user_ids), days_back=days_back)
        for _ in range(num_rows)
    ]
    chatbox_rows = [
        build_fake_chatbox(
            user_id=choice(user_ids),
            days_back=days_back,
            num_messages=num_messages,
            index=i,
        )
        for i in range(num_chatboxes)
    ]

    try:
        with connect(conn_str) as conn:
            with conn.cursor() as cur:
                if emission_rows:
                    cur.executemany(INSERT_EMISSIONS_SQL, emission_rows)
                if chatbox_rows:
                    cur.executemany(INSERT_CHATBOXES_SQL, chatbox_rows)
            conn.commit()
        print(f"Successfully inserted {num_rows} rows into 'emissions'.")
        print(
            f"Successfully inserted {num_chatboxes} rows into 'chatboxes' "
            f"({num_chatboxes * num_messages} token history items)."
        )
    except Exception as e:
        print(f"FAILED to seed data: {e}")
        raise


def main() -> None:
    parser = ArgumentParser(
        description="Seed fake emissions and chatbox token data directly into Postgres."
    )
    parser.add_argument("--rows", type=int, default=50, help="Number of fake emission rows to create.")
    parser.add_argument(
        "--users",
        type=int,
        default=1,
        help="Number of real existing user IDs to juggle rows across (capped at available real users).",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=180,
        help="Spread timestamps randomly across the last N days (use 180+ for 6M charts).",
    )
    parser.add_argument(
        "--chatboxes",
        type=int,
        default=6,
        help="Number of fake chatbox sessions to create. Tokens are stored in details JSONB.",
    )
    parser.add_argument(
        "--messages",
        type=int,
        default=10,
        help="Number of inquiry cycles (token pairs) per chatbox.",
    )
    args = parser.parse_args()

    if args.messages < 1 and args.chatboxes > 0:
        parser.error("--messages must be >= 1 when --chatboxes > 0")

    seed(
        num_rows=args.rows,
        num_users=args.users,
        days_back=args.days_back,
        num_chatboxes=args.chatboxes,
        num_messages=args.messages,
    )


if __name__ == "__main__":
    main()
