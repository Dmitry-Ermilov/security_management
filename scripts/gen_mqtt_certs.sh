#!/bin/sh
set -eu

BASE_DIR=$(cd "$(dirname "$0")/.." && pwd)
CONF_DIR="$BASE_DIR/mosquitto/conf"
CERT_DIR="$BASE_DIR/telegraf/certs"

mkdir -p "$CONF_DIR" "$CERT_DIR"

# CA
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -subj "/CN=MQTT-CA" \
  -keyout "$CONF_DIR/ca.key" -out "$CONF_DIR/ca.crt"

# Server cert (broker)
openssl req -newkey rsa:4096 -nodes \
  -subj "/CN=mosquitto" \
  -keyout "$CONF_DIR/server.key" -out "$CONF_DIR/server.csr"

openssl x509 -req -in "$CONF_DIR/server.csr" \
  -CA "$CONF_DIR/ca.crt" -CAkey "$CONF_DIR/ca.key" -CAcreateserial \
  -out "$CONF_DIR/server.crt" -days 3650 -sha256

# Client cert (operator/telegraf)
openssl req -newkey rsa:4096 -nodes \
  -subj "/CN=operator" \
  -keyout "$CERT_DIR/client.key" -out "$CERT_DIR/client.csr"

openssl x509 -req -in "$CERT_DIR/client.csr" \
  -CA "$CONF_DIR/ca.crt" -CAkey "$CONF_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/client.crt" -days 3650 -sha256

# Copy CA to telegraf
cp "$CONF_DIR/ca.crt" "$CERT_DIR/ca.crt"

# Cleanup CSRs and serials
rm -f "$CONF_DIR/server.csr" "$CERT_DIR/client.csr" "$CONF_DIR/ca.srl"

echo "MQTT certs generated in $CONF_DIR and $CERT_DIR"
