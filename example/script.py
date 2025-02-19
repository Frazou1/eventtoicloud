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

# Vérifier et créer les fichiers de cache et de notifications
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
os.makedirs(os.path.dirname(ICS_FILE), exist_ok=True)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

cache = load_cache()

# Fonction pour récupérer les événements depuis le fichier ICS
def fetch_events():
    try:
        response = requests.get(args.event_source_url)
        
        if response.status_code != 200 or not response.text:
            print("⚠️ Erreur : Impossible de récupérer les événements. Vérifie l'URL.")
            return []
        
        cal = Calendar.from_ical(response.text)
        events = []
        max_date = datetime.now(timezone.utc) + timedelta(days=DAYS_IN_FUTURE)

        print("📥 Liste des événements futurs récupérés :")
        
        for component in cal.walk():
            if component.name == "VEVENT":
                event_name = component.get("SUMMARY", "Événement sans titre")
                start_time = component.get("DTSTART")
                end_time = component.get("DTEND")
                
                if not start_time or not end_time:
                    continue  # Ignorer les événements sans dates

                start_time = start_time.dt if hasattr(start_time, 'dt') else None
                end_time = end_time.dt if hasattr(end_time, 'dt') else None

                # Uniformiser les fuseaux horaires en UTC
                if isinstance(start_time, datetime) and start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                if isinstance(end_time, datetime) and end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)

                # Filtrer directement les événements passés
                if start_time < datetime.now(timezone.utc) or start_time > max_date:
                    continue  # Ignorer les événements hors plage
                
                print(f"   - {event_name} ({start_time} -> {end_time})")
                
                events.append({
                    "name": event_name,
                    "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S%z")
                })
        
        return events
    except Exception as e:
        print(f"❌ Erreur lors du traitement du calendrier iCal : {e}")
        return []

# Fonction pour filtrer les événements contenant le mot-clé
def filter_events(events, keyword):
    return [event for event in events if keyword.lower() in event["name"].lower()]

# Fonction pour créer le fichier ICS
def create_ics(event):
    try:
        cal = Calendar()
        event_ics = Event()
        event_ics.add("SUMMARY", event["name"])
        event_ics.add("DTSTART", event["start_time"])
        event_ics.add("DTEND", event["end_time"])
        cal.add_component(event_ics)
        
        with open(ICS_FILE, "wb") as f:
            f.write(cal.to_ical())
        
        print(f"📂 Fichier ICS créé :\n{cal.to_ical().decode()}")
    except Exception as e:
        print(f"❌ Erreur lors de la création du fichier ICS : {e}")

# Fonction pour envoyer un événement à iCloud
def send_to_icloud(event):
    print(f"📤 Envoi de l'événement '{event['name']}' à iCloud...")
    create_ics(event)
    icloud_event_url = f"{args.icloud_calendar_url}event.ics"
    command = (
        f'curl -v -X PUT -u "{args.icloud_username}:{args.icloud_password}" '
        f'-H "Content-Type: text/calendar" '
        f'--data-binary @{ICS_FILE} "{icloud_event_url}"'
    )
    print(f"🔧 Commande exécutée : {command}")
    response = os.system(command)
    
    if response == 0:
        print(f"✅ Événement '{event['name']}' ajouté avec succès à iCloud !")
    else:
        print(f"❌ Échec de l'envoi de l'événement '{event['name']}' à iCloud.")

# Exécution principale
def main():
    print("🔄 Récupération des événements...")
    events = fetch_events()
    filtered_events = filter_events(events, args.keyword)
    
    new_events = [event for event in filtered_events if event["name"] not in cache]
    
    if new_events:
        print(f"📅 {len(new_events)} nouveaux événements détectés !")
        print("📋 Événements trouvés :")
        for event in new_events:
            print(f"   - {event['name']} ({event['start_time']} -> {event['end_time']})")
        
        for event in new_events:
            send_to_icloud(event)
            cache[event["name"]] = event["start_time"]
        
        save_cache(cache)
    else:
        print("✅ Aucun nouvel événement à envoyer.")

if __name__ == "__main__":
    main()
