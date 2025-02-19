import argparse
import os
import json
import requests
import time
from icalendar import Calendar, Event
from datetime import datetime, timedelta, timezone
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
DAYS_IN_FUTURE = 30  # Nombre de jours dans le futur à considérer

# Définir la date actuelle pour filtrer les événements passés
NOW = datetime.now(timezone.utc)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

cache = load_cache()

# Fonction pour envoyer un événement à iCloud
def send_to_icloud(event_name):
    print(f"📤 Envoi de l'événement '{event_name}' à iCloud...")
    
    icloud_event_url = f"{args.icloud_calendar_url}/event.ics"
    command = (
        f'curl -v -X PUT -u "{args.icloud_username}:{args.icloud_password}" '
        f'-H "Content-Type: text/calendar" '
        f'--data-binary @{ICS_FILE} "{icloud_event_url}"'
    )
    print(f"🔧 Commande exécutée : {command}")
    response = os.system(command)
    
    if response == 0:
        print(f"✅ Événement '{event_name}' ajouté avec succès à iCloud !")
    else:
        print(f"❌ Échec de l'envoi de l'événement '{event_name}' à iCloud.")

# Exécution principale
def main():
    print("🔄 Récupération des événements...")
    events = fetch_events()
    filtered_events = filter_events(events, args.keyword)
    
    new_events = [event for event in filtered_events if not is_event_already_sent(event)]
    
    if new_events:
        print(f"📅 {len(new_events)} nouveaux événements détectés !")
        print("📋 Événements trouvés :")
        for event in new_events:
            print(f"   - {event['name']} ({event['start_time']} -> {event['end_time']})")
        
        for event in new_events:
            create_ics(event)
            send_to_icloud(event['name'])
            mark_event_as_sent(event)
        
        update_home_assistant_sensor(new_events)
    else:
        print("✅ Aucun nouvel événement à envoyer.")

if __name__ == "__main__":
    main()
