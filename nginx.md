## Publishing Behind Nginx

It is recommended to expose ASN Cache through Nginx instead of publishing the FastAPI service directly to the Internet.

### HTTP Configuration (Port 80)

```nginx
server {
    listen 80;
    server_name asn-cache.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS Configuration (Port 443)

```nginx
server {
    listen 443 ssl http2;
    server_name asn-cache.example.com;

    ssl_certificate     /etc/letsencrypt/live/asn-cache.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/asn-cache.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

After configuring Nginx, routers can access ASN Cache using:

```text
https://asn-cache.example.com/data/announced-prefixes/data.json?resource=AS15169
```

### Restricting Access by IP Address

To allow access only from trusted routers:

```nginx
location / {
    allow 1.2.3.4;
    allow 5.6.7.8;
    deny all;

    proxy_pass http://127.0.0.1:8080;
}
```

### Obtaining a Free TLS Certificate

Install Certbot:

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

Issue a certificate:

```bash
sudo certbot --nginx -d asn-cache.example.com
```

Certbot will automatically configure HTTPS and set up certificate renewal.

### Recommended Production Architecture

```text
Routers
    |
    v
Nginx (80/443)
    |
    v
ASN Cache (FastAPI, 127.0.0.1:8080)
    |
    v
SQLite
```

This architecture provides:

* TLS encryption
* IP-based access control
* Reverse proxy support
* Easier certificate management
* Additional security by keeping FastAPI inaccessible from the public Internet
