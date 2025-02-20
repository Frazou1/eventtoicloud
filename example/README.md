# Module complémentaire de filtre d'événements pour Home Assistant

L' Event Filter Add-on pour Home Assistant permet de filtrer les événements provenant d'une source externe (par exemple un fichier ICS ou une API) et de les publier dans un calendrier iCloud via le protocole CalDAV. De plus, il publie des notifications via MQTT pour permettre des automatisations dans Home Assistant.

## Prérequis
-  Home Assistant installé.
-  Courtier MQTT configuré et accessible depuis Home Assistant.
-  Compte iCloud avec accès CalDAV.
-  Source d'événements (URL d'un fichier ICS ou API d'événements compatibles).

## Installation

1. Ajouter au dépôt :
  - Dans Home Assistant, accédez à Supervisor> Add-on Store.
  - Cliquez sur Repositories et ajoutez : https://github.com/Frazou1/eventtoicloud

2. Installer le module complémentaire :
  - Recherchez Event Filter Add-on et cliquez sur Install.

3. Configuration MQTT :
  - Assurez-vous que le courtier MQTT est configuré et que les informations de connexion sont correctes.

## Configuration

-  keyword: "Réunion"
-  event_source_url: "https://api.example.com/events"
-  icloud_username: "ton-email@icloud.com"
-  icloud_password: "ton-mot-de-passe"
-  icloud_calendar_url: "https://caldav.icloud.com/ton-id/calendars/ton-calendrier/"
-  mqtt_host: "homeassistant.local"
-  mqtt_port: 1883
-  mqtt_username: "votre_utilisateur_mqtt"
-  mqtt_password: "votre_mot_de_passe_mqtt"
-  update_interval: 600 secondes

## Exemple d'automation
```
alias: Notification nouvel événement iCloud
description: Notifie lorsqu'un nouvel événement iCloud est détecté via MQTT.
trigger:
  - platform: mqtt
    topic: homeassistant/sensor/eventtoicloud/+/state
action:
  - service: persistent_notification.create
    data:
      title: Nouvel Événement iCloud
      message: >
        📅 **Événement ajouté :** - **Nom :** Cours privé QMDA Rosalie -  -
        **Heure :** {{ trigger.payload }}  en date du {{
        now().strftime('%Y-%m-%d %H:%M:%S') }}
  - service: notify.notify
    data:
      title: Nouvel Événement iCloud
      message: >
        📅 **Événement ajouté :** - **Nom :** Cours privé QMDA Rosalie -  -
        **Heure :** {{ trigger.payload }}  en date du {{
        now().strftime('%Y-%m-%d %H:%M:%S') }}
mode: single

```


## Fonctionnement

-  Filtrage des événements exploités sur un mot-clé.
-  Publication des événements dans un calendrier iCloud.
-  Notification des événements via MQTT pour intégration dans Home Assistant.
-  Configuration flexible via l'interface Home Assistant.

## Dépendances

- requests
- icalendar
- paho-mqtt
- selenium
- webdriver-manager
- beautifulsoup4

## Contributeur
Les contributions sont les bienvenues ! Pour contribuer :

1. Fourcher le dépôt.
2. Créer une branche ( feature/new-feature).
3. Effectuez vos modifications.
4. Envoyez une Pull Request pour examen.

## Licence
Ce projet est sous licence MIT. Voir le fichier LICENSEpour plus d'informations
