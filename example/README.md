# Event Filter Add-on for Home Assistant

Cet add-on récupère des événements depuis une API, filtre ceux contenant un mot-clé spécifique, les envoie à un calendrier iCloud et met à jour un capteur MQTT dans Home Assistant.

## Installation

1. Ajouter cet add-on à Home Assistant.
2. Configurer les options dans l'interface Home Assistant.
3. Démarrer l'add-on.

## Configuration

- `keyword`: Mot-clé pour filtrer les événements.
- `event_source_url`: URL de l'API récupérant les événements.
- `icloud_username`: Identifiant iCloud.
- `icloud_password`: Mot de passe iCloud.
- `icloud_calendar_url`: URL du calendrier iCloud.
- `mqtt_broker`: Adresse du broker MQTT.
- `mqtt_port`: Port MQTT.
- `mqtt_topic`: Sujet MQTT pour mettre à jour un capteur.

## Fonctionnement

- Récupère les événements.
- Filtre les événements selon le mot-clé.
- Enregistre un fichier `.ics`.
- Envoie l'événement à iCloud via `curl`.
- Met à jour un capteur MQTT.

## Dépendances

- `requests`
- `icalendar`
- `paho-mqtt`
