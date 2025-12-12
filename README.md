# Security Management Stack (MQTT + Suricata + Wazuh demo)

## Запуск
```bash
cd /home/dmitry/Документы/project_VC/security_management
sg docker -c "docker compose up -d"
```
Базовые сервисы: mosquitto, telegraf, elasticsearch, kibana, logstash (TheHive/Cortex/Wazuh при необходимости стартуются отдельно).

## Генерация данных MQTT
```bash
source .venv/bin/activate
python simulate_telemetry.py
```
Скрипт шлёт telemetry/command/event в Mosquitto (TLS 8883), Telegraf раскладывает по индексам `telemetry-*`, `command-*`, `mqtt-*`.

## Просмотр в Kibana
Открой `http://localhost:5601`, выбери Dashboard (MQTT ingest) или Discover:
- telemetry / command / mqtt — новые записи видны при таймпикере “Last 15m/1h”.
- suricata — события IDS.
- wazuh — тестовые/агентские события.

## Suricata (pcap)
Положи pcap в `pcap/`, потом:
```bash
sg docker -c "docker run --rm --net=security_management_edge \
  -v security_management_suricata-logs:/var/log/suricata \
  -v $(pwd)/pcap:/pcap jasonish/suricata:7.0.5 \
  suricata -r /pcap/test.pcap -c /etc/suricata/suricata.yaml -l /var/log/suricata"
```
Затем в Kibana → Discover → `suricata` (Last 7/30 days) → Refresh.

## Wazuh (тестовый документ)
Отправить вручную:
```bash
curl -XPOST http://localhost:9200/wazuh-000001/_doc \
  -H 'Content-Type: application/json' \
  -d '{"@timestamp":"'"$(date -Is)"'","rule.description":"manual test","agent.name":"demo"}'
```
Потом Kibana → Discover → data view `wazuh` (Last 24h).
Для реального потока — подключить агент к `wazuh-manager` и оставить сервис запущенным.

## Дашборды в Kibana
- Discover: сохрани saved search по `telemetry`/`command`/`mqtt`/`suricata`/`wazuh` (таймпикер Last 15m–24h).
- Lens-примеры: count по `@timestamp` с Breakdown по `tag.topic` для telemetry/command; таблица с полями `mqtt_consumer.altitude/speed/battery_level/flight_mode` (если отправляются).
- Собрать Dashboard: Dashboard → Create → Add from library → добавь сохранённые визуализации и saved search, выстави таймпикер (например, Last 15m) и сохрани (например, “MQTT ingest”).

## Полезные команды
- Остановить тяжёлые сервисы: `sg docker -c "docker compose stop thehive cortex wazuh-manager"`
- Запустить их снова: `sg docker -c "docker compose start thehive cortex wazuh-manager"`
- Проверить индексы: `curl -s 'http://localhost:9200/_cat/indices?v'`
