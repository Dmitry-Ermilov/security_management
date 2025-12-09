# Пилот мониторинга/реагирования (Docker Compose)

## Сервисы
- mosquitto (TLS/ACL) — порты 1883/8883
- suricata — IDS, читает custom.rules
- logstash → elasticsearch → kibana (ES 8.13.4, security off для простоты)
- wazuh-manager — FIM/audit
- fastapi + postgres — API политик/алертов
- thehive + cortex — кейсы/плейбуки (минимум конфигурации)

## Быстрый старт
1. Сгенерируй CA и certs (server/client) для mosquitto, сервисов, и положи в `mosquitto/conf` (ca.crt, server.crt, server.key, password/acl файлы). Пример ACL уже есть.
2. (Опц) поправь `suricata/custom.rules` и `logstash/logstash.conf` под свои адреса/топики.
3. Запусти: `docker compose up -d`.
4. Проверь доступность:
   - Kibana: http://localhost:5601
   - Elasticsearch: http://localhost:9200
   - FastAPI: http://localhost:8000/health
   - TheHive: http://localhost:9000
5. Отправь тестовые MQTT сообщения (TLS) и убедись, что Suricata/Logstash кладут события в ES.

## Тесты
- pcap/replay MQTT/MAVLink → Suricata alert → проверка в ES/Kibana.
- Flood на брокер → алерт DoS, переключение QoS/канала.
- Попытка неподписанной OTA → блокировка (Wazuh FIM + правило).

## Замечания
- ES security отключена для простоты. В прод включить xpack и добавить учётки.
- TheHive/Cortex требуют базовой инициализации пользователей и подключений (см. оф. доку).
- Образы Wazuh/TheHive/Cortex тяжёлые; при нехватке ресурсов запускай частями (ES+LS+Kibana+Mosquitto+Suricata для начала).
