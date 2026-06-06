# ASN Cache

Lightweight self-hosted ASN prefix cache and aggregation service.

Supported data sources:

- RIPEstat
- RouteViews
- RADB

Designed for use with Bird4Static, BIRD Internet Routing Daemon, and other route automation systems.

## Features

* ASN → Prefix caching
* Multiple data sources:

  * RIPEstat
  * RouteViews
  * RADB
* Automatic aggregation of results from all available sources
* RIPEstat-compatible API
* Local SQLite storage
* Docker deployment support
* Low resource consumption
* Supports thousands of ASN records
* Can serve multiple routers from a single central instance

## Architecture

```text
Routers
    |
    v
ASN Cache API
    |
    +-- SQLite
    |
    +-- RIPEstat
    +-- RouteViews
    +-- RADB
```

Routers communicate only with the ASN Cache API.

The service automatically retrieves data from external sources and stores it locally.

## Supported API

### Get announced prefixes for an ASN

```http
GET /data/announced-prefixes/data.json?resource=AS15169
```

Example response:

```json
{
  "status": "ok",
  "data": {
    "resource": "AS15169",
    "prefixes": [
      {
        "prefix": "8.8.8.0/24"
      },
      {
        "prefix": "8.34.208.0/20"
      }
    ]
  }
}
```

### Health check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Using ASN Cache with Bird4Static

Bird4Static normally queries RIPEstat directly:

```bash
curl https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS15169
```

After deploying ASN Cache, simply replace the base URL:

```bash
curl https://asn-cache.example.com/data/announced-prefixes/data.json?resource=AS15169
```

No additional changes are required in the existing scripts.

## Docker Deployment

Build:

```bash
docker compose build
```

Start:

```bash
docker compose up -d
```

Verify:

```bash
curl http://127.0.0.1:8080/health
```

## Requirements

### Docker

* Docker Engine
* Docker Compose Plugin

### Native Installation

* Python 3.11+
* FastAPI
* Uvicorn
* SQLite

## Security

It is recommended to restrict API access by IP address using a firewall or reverse proxy.

Example iptables configuration:

```bash
iptables -A INPUT -p tcp -s <ROUTER_IP_1> --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp -s <ROUTER_IP_2> --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP
```

## Performance

Typical database sizes:

| ASN Count | Database Size |
| --------- | ------------- |
| 500       | < 5 MB        |
| 2,000     | 10–20 MB      |
| 10,000    | 50–100 MB     |

The service is suitable for low-resource VPS instances.

## Typical Use Case

* Deploy ASN Cache on a central VPS.
* Multiple routers use it as an ASN → Prefix source.
* The service reduces load on RIPEstat and other public services.
* Cached data remains available even if one of the upstream providers becomes temporarily unavailable.

## Roadmap

Planned features:

* Background ASN refresh scheduler
* IPv6 support
* Source attribution for prefixes
* Metrics and statistics endpoint
* Web-based ASN explorer
* PostgreSQL backend support
* Prefix change history

## License

MIT License
