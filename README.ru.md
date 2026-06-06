# ASN Cache

[🇺🇸 English](README.md) | 🇷🇺 Русский

Лёгкий self-hosted сервис для кэширования и агрегации информации о префиксах автономных систем (ASN).

Поддерживаемые источники:

* RIPEstat
* RouteViews
* RADB

Разработан для использования с Bird4Static, BIRD Internet Routing Daemon и другими системами автоматизации маршрутизации.

## Возможности

* Кэширование результатов запросов ASN → Prefixes
* Поддержка нескольких источников данных:

  * RIPEstat
  * RouteViews
  * RADB
* Автоматическое объединение данных из всех источников
* RIPEstat-совместимый API
* Локальное хранение данных в SQLite
* Поддержка Docker
* Низкое потребление ресурсов
* Поддержка тысяч ASN
* Возможность использования в качестве центрального сервиса для нескольких роутеров

## Архитектура

```text
Роутеры
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

Роутеры обращаются только к ASN Cache API.

Сервис самостоятельно получает данные из внешних источников и хранит их локально, уменьшая нагрузку на публичные сервисы и повышая отказоустойчивость инфраструктуры.

## Поддерживаемый API

### Получение префиксов ASN

```http
GET /data/announced-prefixes/data.json?resource=AS15169
```

Пример ответа:

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

### Проверка состояния сервиса

```http
GET /health
```

Ответ:

```json
{
  "status": "ok"
}
```

## Использование с Bird4Static

Bird4Static обычно обращается напрямую к RIPEstat:

```bash
curl https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS15169
```

После развертывания ASN Cache достаточно заменить базовый URL:

```bash
curl https://asn-cache.example.com/data/announced-prefixes/data.json?resource=AS15169
```

Остальная логика существующих скриптов остаётся без изменений.

## Развертывание через Docker

Сборка контейнера:

```bash
docker compose build
```

Запуск:

```bash
docker compose up -d
```

Проверка работы:

```bash
curl http://127.0.0.1:8080/health
```

## Требования

### Docker

* Docker Engine
* Docker Compose Plugin

### Нативная установка

* Python 3.11+
* FastAPI
* Uvicorn
* SQLite

## Безопасность

Рекомендуется ограничить доступ к API по IP-адресам с помощью firewall или reverse proxy.

Пример настройки iptables:

```bash
iptables -A INPUT -p tcp -s <ROUTER_IP_1> --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp -s <ROUTER_IP_2> --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP
```

## Производительность

Типичные размеры базы данных:

| Количество ASN | Размер БД |
| -------------- | --------- |
| 500            | < 5 МБ    |
| 2 000          | 10–20 МБ  |
| 10 000         | 50–100 МБ |

Сервис подходит для VPS с минимальными ресурсами.

## Типовой сценарий использования

* ASN Cache развёрнут на центральном VPS.
* Несколько роутеров используют его как источник ASN → Prefixes.
* Сервис снижает нагрузку на RIPEstat и другие публичные сервисы.
* Кэшированные данные остаются доступными даже при временной недоступности одного из внешних источников.

## Интеграция с Bird4Static

Для использования ASN Cache в Bird4Static необходимо добавить функцию получения префиксов из собственного сервиса.

### Добавьте новую функцию в `func.sh`

```bash
#GET PREFIXES FROM PERSONAL FUNCTION
get_prefixes_personal_func() {
  local cur_as="$1"
  local result

  result="$(
    retry_cmd_func "personal" "$cur_as" \
      curl -fsSk "http://YOUR_DOMAIN_OR_IP/data/announced-prefixes/data.json?resource=$cur_as" |
      jq -r '.data.prefixes[]? | select(.prefix? and (.prefix | contains("."))) | .prefix'
  )"

  log_source_result_func "personal" "$cur_as" "$result"
  printf '%s\n' "$result"
}
```

### Измените функцию `get_as_func()`

Найдите следующий блок:

```bash
result="$(get_prefixes_ripe_func "$cur_as")"
[[ -z "$result" ]] && result="$(get_prefixes_routeviews_func "$cur_as")"
[[ -z "$result" ]] && result="$(get_prefixes_radb_func "$cur_as")"
```

и замените его на:

```bash
result="$(get_prefixes_personal_func "$cur_as")"
[[ -z "$result" ]] && result="$(get_prefixes_ripe_func "$cur_as")"
[[ -z "$result" ]] && result="$(get_prefixes_routeviews_func "$cur_as")"
[[ -z "$result" ]] && result="$(get_prefixes_radb_func "$cur_as")"
```

Теперь Bird4Static сначала будет обращаться к ASN Cache, а при недоступности сервиса автоматически переключится на RIPEstat, RouteViews и RADB.

### Документация

| Документ | Описание |
|-----------|-------------|
| [Настройка Nginx Reverse Proxy](nginx.ru.md) | Публикация ASN Cache через HTTP/HTTPS |

### Использование через HTTPS

Если сервис опубликован через Nginx и TLS:

```bash
curl -fsSk "https://asn-cache.example.com/data/announced-prefixes/data.json?resource=$cur_as"
```


## Дорожная карта

Планируемые возможности:

* Фоновое обновление ASN по расписанию
* Поддержка IPv6
* Хранение информации об источнике каждого префикса
* Метрики и статистика
* Веб-интерфейс для просмотра ASN и префиксов
* Поддержка PostgreSQL
* История изменений префиксов

## Лицензия

MIT License
