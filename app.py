"""ASN Cache service (RIPEstat-compatible prefix aggregation API)."""
#!/usr/bin/env python3
import os
import subprocess

import sqlite3
import time
import requests

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

DB = os.getenv("DB", "/data/asn-cache.db")
TTL = 86400  # 24 часа

app = FastAPI(title="ASN Cache")

# ----------------------------------------------------
# DB
# ----------------------------------------------------

def db():
    """Create SQLite connection."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite schema."""
    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS prefixes (
        asn TEXT NOT NULL,
        prefix TEXT NOT NULL,
        updated INTEGER NOT NULL,
        PRIMARY KEY(asn,prefix)
    )
    """)

    conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_asn
    ON prefixes(asn)
    """)

    conn.commit()
    conn.close()


# ----------------------------------------------------
# SOURCES
# ----------------------------------------------------

def fetch_ripe(asn):
    """Fetch IPv4 prefixes from RIPEstat for given ASN."""
    url = (
        "https://stat.ripe.net/"
        f"data/announced-prefixes/data.json?resource={asn}"
    )

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    data = r.json()

    result = []

    for p in data.get("data", {}).get("prefixes", []):
        prefix = p.get("prefix")

        if prefix and "." in prefix:
            result.append(prefix)

    return result


def fetch_routeviews(asn):
    """Fetch IPv4 prefixes from RouteViews API."""
    asn_num = asn.replace("AS", "")

    url = f"https://api.routeviews.org/guest/asn/{asn_num}?af=4"

    try:
        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            return []

        data = r.json()

        if isinstance(data, list):
            return [x for x in data if "." in x]

    except (requests.RequestException, ValueError):
        pass

    return []


def fetch_radb(asn):
    """Fetch prefixes from RADB whois database."""
    try:
        output = subprocess.check_output(
            [
                "whois",
                "-h",
                "whois.radb.net",
                "--",
                f"-i origin {asn}"
            ],
            text=True,
            timeout=60
        )

        result = []

        for line in output.splitlines():
            if line.startswith("route:"):
                result.append(line.split()[1])

        return result

    except (subprocess.SubprocessError, OSError):
        return []


# ----------------------------------------------------
# CACHE
# ----------------------------------------------------

def cache_valid(asn):
    """Check if ASN cache is still valid based on TTL."""
    conn = db()

    row = conn.execute(
        """
        SELECT MAX(updated)
        FROM prefixes
        WHERE asn=?
        """,
        (asn,)
    ).fetchone()

    conn.close()

    if not row:
        return False

    ts = row[0]

    if ts is None:
        return False

    return (time.time() - ts) < TTL


def get_cached(asn):
    """Return cached prefixes for ASN."""
    conn = db()

    rows = conn.execute(
        """
        SELECT prefix
        FROM prefixes
        WHERE asn=?
        ORDER BY prefix
        """,
        (asn,)
    ).fetchall()

    conn.close()

    return [r["prefix"] for r in rows]


def save_prefixes(asn, prefixes):
    """Store prefixes into SQLite cache."""
    conn = db()

    conn.execute(
        "DELETE FROM prefixes WHERE asn=?",
        (asn,)
    )

    now = int(time.time())

    for p in sorted(set(prefixes)):
        conn.execute(
            """
            INSERT OR REPLACE
            INTO prefixes(asn,prefix,updated)
            VALUES(?,?,?)
            """,
            (asn, p, now)
        )

    conn.commit()
    conn.close()


def refresh_asn(asn):
    """Refresh ASN prefixes from all external sources."""
    prefixes = set()

    try:
        prefixes.update(fetch_ripe(asn))
    except requests.RequestException:
        pass

    try:
        prefixes.update(fetch_routeviews(asn))
    except requests.RequestException:
        pass

    try:
        prefixes.update(fetch_radb(asn))
    except requests.RequestException:
        pass

    prefixes.discard("0.0.0.0/0")

    save_prefixes(asn, prefixes)

    return sorted(prefixes)


# ----------------------------------------------------
# API
# ----------------------------------------------------

@app.get("/data/announced-prefixes/data.json")
def announced_prefixes(resource: str):
    """Return announced prefixes for given ASN."""

    resource = resource.upper()

    if not resource.startswith("AS"):
        raise HTTPException(
            status_code=400,
            detail="resource must be ASN"
        )

    if cache_valid(resource):
        prefixes = get_cached(resource)
    else:
        prefixes = refresh_asn(resource)

    return JSONResponse(
        {
            "status": "ok",
            "data": {
                "resource": resource,
                "prefixes": [
                    {"prefix": p}
                    for p in prefixes
                ]
            }
        }
    )


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ----------------------------------------------------

init_db()
