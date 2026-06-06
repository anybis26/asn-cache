## Публикация через Nginx

Рекомендуется не открывать FastAPI напрямую в Интернет, а использовать Nginx как reverse proxy.

### HTTP (порт 80)

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

### HTTPS (порт 443)

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

После настройки Nginx роутеры смогут обращаться к сервису по адресу:

```text
https://asn-cache.example.com/data/announced-prefixes/data.json?resource=AS15169
```

### Ограничение доступа по IP

Для ограничения доступа только доверенным роутерам можно использовать:

```nginx
location / {
    allow 1.2.3.4;
    allow 5.6.7.8;
    deny all;

    proxy_pass http://127.0.0.1:8080;
}
```
