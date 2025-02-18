import os
import requests
import json
from icalendar import Calendar, Event
from datetime import datetime
import paho.mqtt.client as mqtt

# Charger la configuration depuis Home Assistant
CONFIG_FILE = "/data/options.json"

def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

config = load_config()

# Récupération des événements depuis une API
def fetch_events():
    response = requests.get(config["event_source_url"])
    if response.status_code == 200:
        return response.json()
    return []

# Filtrer les événements par mot-clé
def filter_events(events, keyword):
    return [event for event in events if keyword.lower() in event["name"].lower()]

# Générer un fichier ICS pour l'événement
def create_ics(event):
    cal = Calendar()
    event_ical = Event()
    event_ical.add("summary", event["name"])
    event_ical.add("dtstart", datetime.strptime(event["start_time"], "%Y-%m-%dT%H:%M:%S"))
    event_ical.add("dtend", datetime.strptime(event["end_time"], "%Y-%m-%dT%H:%M:%S"))
    cal.add_component(event_ical)

    with open("/config/file_notifications/event.ics", "wb") as f:
        f.write(cal.to_ical())

# Envoyer l'événement à iCloud via curl
def send_to_icloud():
    os.system(
        f'curl -v -X PUT -u "{config["icloud_username"]}:{config["icloud_password"]}" '
        f'-H "Content-Type: text/calendar" '
        f'--data-binary @/config/file_notifications/event.ics "{config["icloud_calendar_url"]}"'
    )

# Mettre à jour Home Assistant via MQTT
def update_home_assistant_sensor(events):
    client = mqtt.Client()
    client.connect(config["mqtt_broker"], config["mqtt_port"], 60)
    client.publish(config["mqtt_topic"], json.dumps(events))
    client.disconnect()

# Exécution du script
def main():
    events = fetch_events()
    filtered_events = filter_events(events, config["keyword"])

    if filtered_events:
        create_ics(filtered_events[0])
        send_to_icloud()
        update_home_assistant_sensor(filtered_events)
    else:
        print("Aucun événement correspondant.")

if __name__ == "__main__":
    main()
