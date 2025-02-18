import os
import requests
import json
import time
from icalendar import Calendar, Event
from datetime import datetime
import paho.mqtt.client as mqtt

# Fichiers de stockage
CONFIG_FILE = "/data/options.json"
CACHE_FILE = "/config/event_cache.json"
ICS_FILE = "/config/file_notifications/event.ics"

# Charger la configuration
def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

config = load_config()

# Charger le cache des événements envoyés
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    return {}

# Sauvegarder le cache mis à jour
def save_cache(cache):
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

cache = load_cache()

# Récupération des événements depuis une API
def fetch_events():
    response = requests.get(config["event_source_url"])
    if response.status_code == 200:
        return response.json()
    return []

# Filtrer les événements par mot-clé
def filter_events(events, keyword):
    return [event for event in events if keyword.lower() in event["name"].lower()]

# Vérifier si un événement est déjà envoyé
def is_event_already_sent(event):
    event_id = event["id"]  # Assurez-vous que l'événement a un ID unique
    return event_id in cache

# Ajouter un événement au cache
def mark_event_as_sent(event):
    cache[event["id"]] = event["start_time"]
    save_cache(cache)

# Générer un fichier ICS pour l'événement
def create_ics(event):
    cal = Calendar()
    event_ical = Event()
    event_ical.add("summary", event["name"])
    event_ical.add("dtstart", datetime.strptime(event["start_time"], "%Y-%m-%dT%H:%M:%S"))
    event_ical.add("dtend", datetime.strptime(event["end_time"], "%Y-%m-%dT%H:%M:%S"))
    cal.add_component(event_ical)

    with open(ICS_FILE, "wb") as f:
        f.write(cal.to_ical())

# Envoyer l'événement à iCloud via curl
def send_to_icloud():
    os.system(
        f'curl -v -X PUT -u "{config["icloud_username"]}:{config["icloud_password"]}" '
        f'-H "Content-Type: text/calendar" '
        f'--data-binary @{ICS_FILE} "{config["icloud_calendar_url"]}"'
    )

# Mettre à jour Home Assistant via MQTT
def update_home_assistant_sensor(events):
    client = mqtt.Client()
    client.connect(config["mqtt_broker"], config["mqtt_port"], 60)
    client.publish(config["mqtt_topic"], json.dumps(events))
    client.disconnect()

# Boucle principale avec récupération toutes les 10 minutes
def main():
    while True:
        print("🔄 Récupération des événements...")
        events = fetch_events()
        filtered_events = filter_events(events, config["keyword"])

        new_events = [event for event in filtered_events if not is_event_already_sent(event)]
        
        if new_events:
            print(f"📅 {len(new_events)} nouveaux événements détectés ! Envoi à iCloud...")
            for event in new_events:
                create_ics(event)
                send_to_icloud()
                mark_event_as_sent(event)  # Marquer l'événement comme envoyé
            
            update_home_assistant_sensor(new_events)
        else:
            print("✅ Aucun nouvel événement à envoyer.")

        print("🕒 Attente 10 minutes avant la prochaine récupération...")
        time.sleep(600)  # Attendre 10 minutes avant la prochaine exécution

if __name__ == "__main__":
    main()
