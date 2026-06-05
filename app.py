#!/usr/bin/env python3

import sqlite3
import time
import requests
import subprocess

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

DB = os.getenv("DB", "/data/asn-cache.db")
TTL = 86400  # 24 часа

app = FastAPI(title="ASN Cache")

# ----------------------------------------------------
# DB
# ----------------------------------------------------

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
    asn_num = asn.replace("AS", "")

    url = f"https://api.routeviews.org/guest/asn/{asn_num}?af=4"

    try:
        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            return []

        data = r.json()

        if isinstance(data, list):
            return [x for x in data if "." in x]

    except Exception:
        pass

    return []


def fetch_radb(asn):
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

    except Exception:
        return []


# ----------------------------------------------------
# CACHE
# ----------------------------------------------------

def cache_valid(asn):
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
    prefixes = set()

    try:
        prefixes.update(fetch_ripe(asn))
    except Exception:
        pass

    try:
        prefixes.update(fetch_routeviews(asn))
    except Exception:
        pass

    try:
        prefixes.update(fetch_radb(asn))
    except Exception:
        pass

    prefixes.discard("0.0.0.0/0")

    save_prefixes(asn, prefixes)

    return sorted(prefixes)


# ----------------------------------------------------
# API
# ----------------------------------------------------

@app.get("/data/announced-prefixes/data.json")
def announced_prefixes(resource: str):

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
    return {"status": "ok"}


# ----------------------------------------------------

init_db()