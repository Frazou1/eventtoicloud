#!/usr/bin/env bash
set -e  # Arrêter le script en cas d'erreur

OPTIONS_FILE="/data/options.json"

# Lire la configuration depuis options.json
KEYWORD="$(jq -r '.keyword' $OPTIONS_FILE)"
EVENT_SOURCE_URL="$(jq -r '.event_source_url' $OPTIONS_FILE)"
ICLOUD_USERNAME="$(jq -r '.icloud_username' $OPTIONS_FILE)"
ICLOUD_PASSWORD="$(jq -r '.icloud_password' $OPTIONS_FILE)"
ICLOUD_CALENDAR_URL="$(jq -r '.icloud_calendar_url' $OPTIONS_FILE)"
MQTT_HOST="$(jq -r '.mqtt_broker' $OPTIONS_FILE)"
MQTT_PORT="$(jq -r '.mqtt_port' $OPTIONS_FILE)"
MQTT_TOPIC="$(jq -r '.mqtt_topic' $OPTIONS_FILE)"
UPDATE_INTERVAL="$(jq -r '.update_interval' $OPTIONS_FILE)"

echo "[INFO] 📅 Démarrage de l'add-on EventToiCloud"
echo "[INFO] 🔍 Mot-clé = $KEYWORD"
echo "[INFO] 🌐 Source des événements = $EVENT_SOURCE_URL"
echo "[INFO] 📡 MQTT = $MQTT_HOST:$MQTT_PORT"
echo "[INFO] 📆 iCloud Calendar URL = $ICLOUD_CALENDAR_URL"
echo "[INFO] ⏳ Intervalle de mise à jour = $UPDATE_INTERVAL secondes"

while true; do
    echo "[INFO] 🚀 Exécution du script Python..."
    python3 /script.py \
      --keyword "$KEYWORD" \
      --event_source_url "$EVENT_SOURCE_URL" \
      --icloud_username "$ICLOUD_USERNAME" \
      --icloud_password "$ICLOUD_PASSWORD" \
      --icloud_calendar_url "$ICLOUD_CALENDAR_URL" \
      --mqtt_host "$MQTT_HOST" \
      --mqtt_port "$MQTT_PORT" \
      --mqtt_topic "$MQTT_TOPIC"

    echo "[INFO] ⏳ Attente $UPDATE_INTERVAL secondes avant la prochaine mise à jour..."
    sleep "$UPDATE_INTERVAL"
done
