import argparse
import os
import json
import requests
import time
from icalendar import Calendar, Event
from datetime import datetime
import paho.mqtt.client as mqtt

# Lire les arguments depuis le script bash
parser = argparse.ArgumentParser(description="Event to iCloud Add-on")
parser.add_argument("--keyword", type=str, required=True)
parser.add_argument("--event_source_url", type=str, required=True)
parser.add_argument("--icloud_username", type=str, required=True)
parser.add_argument("--icloud_password", type=str, required=True)
parser.add_argument("--icloud_calendar_url", type=str, required=True)
parser.add_argument("--mqtt_host", type=str, required=True)
parser.add_argument("--mqtt_port", type=int, required=True)
parser.add_argument("--mqtt_topic", type=str, required=True)
args = parser.parse_args()

# Charger le cache des événements envoyés
CACHE_FILE = "/config/event_cache.json"
ICS_FILE = "/config/file_notifications/event.ics"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

cache = load_cache()

# Récupérer les événements depuis un fichier .ics
def fetch_events():
    try:
        response = requests.get(args.event_source_url)
        
        if response.status_code != 200 or not response.text:
            print("⚠️ Erreur : Impossible de récupérer les événements. Vérifie l'URL.")
            return []
        
        cal = Calendar.from_ical(response.text)
        events = []

        for component in cal.walk():
            if component.name == "VEVENT":
                event_name = component.get("SUMMARY", "Événement sans titre")
                start_time = component.get("DTSTART").dt
                end_time = component.get("DTEND").dt

                if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                    events.append({
                        "name": event_name,
                        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S")
                    })
        
        return events

    except Exception as e:
        print(f"❌ Erreur lors du traitement du calendrier iCal : {e}")
        return []

# Filtrer les événements par mot-clé
def filter_events(events, keyword):
    return [event for event in events if keyword.lower() in event["name"].lower()]

# Vérifier si un événement est déjà envoyé
def is_event_already_sent(event):
    event_id = event.get("id", event["name"])
    return event_id in cache

# Ajouter un événement au cache
def mark_event_as_sent(event):
    cache[event.get("id", event["name"])] = event["start_time"]
    save_cache(cache)

# Générer un fichier ICS
def create_ics(event):
    cal = Calendar()
    event_ical = Event()
    event_ical.add("summary", event["name"])
    event_ical.add("dtstart", datetime.strptime(event["start_time"], "%Y-%m-%dT%H:%M:%S"))
    event_ical.add("dtend", datetime.strptime(event["end_time"], "%Y-%m-%dT%H:%M:%S"))
    cal.add_component(event_ical)

    with open(ICS_FILE, "wb") as f:
        f.write(cal.to_ical())

# Envoyer à iCloud
def send_to_icloud():
    os.system(
        f'curl -v -X PUT -u "{args.icloud_username}:{args.icloud_password}" '
        f'-H "Content-Type: text/calendar" '
        f'--data-binary @{ICS_FILE} "{args.icloud_calendar_url}"'
    )

# Mettre à jour MQTT
def update_home_assistant_sensor(events):
    client = mqtt.Client()
    client.connect(args.mqtt_host, args.mqtt_port, 60)
    client.publish(args.mqtt_topic, json.dumps(events))
    client.disconnect()

# Exécution principale
def main():
    print("🔄 Récupération des événements...")
    events = fetch_events()
    filtered_events = filter_events(events, args.keyword)

    new_events = [event for event in filtered_events if not is_event_already_sent(event)]
    
    if new_events:
        print(f"📅 {len(new_events)} nouveaux événements détectés ! Envoi à iCloud...")
        for event in new_events:
            create_ics(event)
            send_to_icloud()
            mark_event_as_sent(event)

        update_home_assistant_sensor(new_events)
    else:
        print("✅ Aucun nouvel événement à envoyer.")

if __name__ == "__main__":
    main()
