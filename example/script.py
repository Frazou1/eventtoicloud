import argparse
import os
import json
import requests
import time
import uuid
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
parser.add_argument("--mqtt_username", type=str, required=True)
parser.add_argument("--mqtt_password", type=str, required=True)
args = parser.parse_args()

# Charger le cache des événements envoyés
CACHE_FILE = "/config/event_cache.json"
ICS_DIR = "/config/file_notifications/"
DAYS_IN_FUTURE = 30  # Nombre de jours dans le futur à considérer

# Vérifier et créer les fichiers de cache et de notifications
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
os.makedirs(ICS_DIR, exist_ok=True)

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
        
        events = []
        max_date = datetime.now(timezone.utc) + timedelta(days=DAYS_IN_FUTURE)

        print("📥 Liste des événements futurs récupérés :")
        
        event_name = None
        start_time = None
        end_time = None
        event_uid = None
        
        for line in response.text.splitlines():
            if line.startswith("SUMMARY:"):
                event_name = line.replace("SUMMARY:", "").strip()
            elif line.startswith("DTSTART:"):
                start_time_str = line.replace("DTSTART:", "").strip()
                if start_time_str.endswith("Z"):
                    start_time = datetime.strptime(start_time_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                else:
                    start_time = datetime.strptime(start_time_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            elif line.startswith("DTEND:"):
                end_time_str = line.replace("DTEND:", "").strip()
                if end_time_str.endswith("Z"):
                    end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                else:
                    end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            elif line.startswith("UID:"):
                event_uid = line.replace("UID:", "").strip()
                
            if event_name and start_time and end_time and event_uid:
                if start_time < datetime.now(timezone.utc) or start_time > max_date:
                    continue  # Ignorer les événements hors plage
                
                print(f"   - {event_name} ({start_time} -> {end_time})")
                
                events.append({
                    "name": event_name,
                    "start_time": start_time.strftime("%Y%m%dT%H%M%SZ"),
                    "end_time": end_time.strftime("%Y%m%dT%H%M%SZ"),
                    "uid": event_uid  # Utiliser l'UID original
                })
                
                event_name = None
                start_time = None
                end_time = None
                event_uid = None
        
        return events
    except Exception as e:
        print(f"❌ Erreur lors du traitement du calendrier iCal : {e}")
        return []

# Fonction pour filtrer les événements contenant le mot-clé
def filter_events(events, keyword):
    return [event for event in events if keyword.lower() in event["name"].lower()]

# Fonction pour créer le fichier ICS
def create_ics(event, event_index):
    try:
        ics_filename = f"event-{event['uid']}.ics"  # Utiliser l'UID pour le nom du fichier
        ics_path = os.path.join(ICS_DIR, ics_filename)

        ics_content = f"""BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Apple Inc.//NONSGML iCal 4.0.5//EN\nBEGIN:VEVENT\nUID:{event['uid']}\nDTSTAMP:{event['start_time']}\nDTSTART:{event['start_time']}\nDTEND:{event['end_time']}\nSUMMARY:{event['name']}\nEND:VEVENT\nEND:VCALENDAR"""
        
        with open(ics_path, "w") as f:
            f.write(ics_content)
        
        print(f"📂 Fichier ICS créé : {ics_filename}\n{ics_content}")
        return ics_path
    except Exception as e:
        print(f"❌ Erreur lors de la création du fichier ICS : {e}")
        return None

import subprocess
import os

def send_to_icloud(event, event_index):
    print(f"📤 Envoi de l'événement '{event['name']}' à iCloud...")

    try:
        print(f"Création du fichier ICS pour l'événement {event['name']}")
        ics_file = create_ics(event, event_index)
        print(f"Chemin du fichier ICS créé : {ics_file}")

        if ics_file is None:
            print("❌ Erreur : Fichier ICS non généré.")
            return

        # Vérifier si le fichier ICS existe et est lisible
        if not os.path.exists(ics_file):
            print(f"❌ Le fichier ICS n'existe pas : {ics_file}")
            return
        if not os.access(ics_file, os.R_OK):
            print(f"❌ Le fichier ICS n'est pas lisible : {ics_file}")
            return

        # Récupérer seulement le nom du fichier ICS (sans le chemin complet)
        ics_filename = os.path.basename(ics_file)

        # Construire l'URL pour iCloud
        icloud_event_url = f"{args.icloud_calendar_url}{ics_filename}"

        # Afficher le contenu du fichier ICS pour vérifier son format
        with open(ics_file, "r") as f:
            print("📄 Contenu du fichier ICS :")
            print(f.read())

        # Exécuter la commande CURL avec subprocess
        command = (
            f'curl -v -X PUT -u "{args.icloud_username}:{args.icloud_password}" '
            f'-H "Content-Type: text/calendar" '
            f'--data-binary @{ics_file} "{icloud_event_url}"'
        )

        print(f"🔧 Commande exécutée : {command}")

        # Exécuter la commande et capturer la sortie
        result = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)

        # Vérifier si la commande s'est bien exécutée
        if result.returncode == 0:
            print(f"✅ Événement '{event['name']}' ajouté avec succès à iCloud !")

            # Supprimer le fichier ICS après un envoi réussi
            try:
                os.remove(ics_file)
                print(f"🗑️ Fichier ICS supprimé : {ics_file}")
            except Exception as e:
                print(f"⚠️ Impossible de supprimer le fichier ICS : {e}")

        else:
            print(f"❌ Échec de l'envoi de l'événement '{event['name']}' à iCloud.")
            print(f"❌ Erreur détaillée : {result.stderr}")

    except Exception as e:
        print(f"❌ Une erreur inattendue s'est produite : {e}")

def delete_event_from_icloud(event):
    try:
        ics_filename = f"event-{event['uid']}.ics"  # Utiliser l'UID pour le nom du fichier
        icloud_event_url = f"{args.icloud_calendar_url}{ics_filename}"

        command = (
            f'curl -v -X DELETE -u "{args.icloud_username}:{args.icloud_password}" '
            f'"{icloud_event_url}"'
        )

        print(f"🗑️ Suppression de l'événement sur iCloud : {event['name']}")
        result = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Événement '{event['name']}' supprimé avec succès de iCloud.")
        else:
            print(f"❌ Échec de la suppression de '{event['name']}'.")
            print(f"❌ Erreur détaillée : {result.stderr}")

    except Exception as e:
        print(f"❌ Erreur lors de la suppression de l'événement : {e}")
        
def publish_to_mqtt(event):
    try:
        client = mqtt.Client()
        client.username_pw_set(args.mqtt_username, args.mqtt_password)  # Authentification
        client.connect(args.mqtt_host, args.mqtt_port, 60)

        # Base du topic MQTT
        topic_base = "homeassistant/sensor/eventtoicloud"

        # Nom du capteur (utilisez l'UID de l'événement pour le rendre unique)
        sensor_name = f"event_{event['uid']}"

        # Payload pour l'état du capteur
        state = event["name"]

        # Attributs du capteur
        attributes = {
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "uid": event["uid"]
        }

        # Configuration du capteur pour MQTT Discovery
        config_topic = f"{topic_base}/{sensor_name}/config"
        state_topic = f"{topic_base}/{sensor_name}/state"
        attr_topic = f"{topic_base}/{sensor_name}/attributes"

        # Payload de configuration pour MQTT Discovery
        config_payload = {
            "name": f"Événement {event['name']}",  # Nom affiché dans Home Assistant
            "state_topic": state_topic,  # Topic pour l'état du capteur
            "json_attributes_topic": attr_topic,  # Topic pour les attributs
            "unique_id": f"eventtoicloud_{event['uid']}",  # ID unique pour le capteur
            "device": {
                "identifiers": ["eventtoicloud_device"],  # Identifiant du dispositif
                "name": "EventToiCloud",  # Nom du dispositif
                "manufacturer": "EventToiCloud Add-on"  # Fabricant
            }
        }

        # Publier la configuration, l'état et les attributs
        client.publish(config_topic, json.dumps(config_payload), retain=True)
        client.publish(state_topic, state, retain=True)
        client.publish(attr_topic, json.dumps(attributes), retain=True)

        client.disconnect()
        print(f"📤 Événement '{event['name']}' publié sur MQTT avec Discovery.")
    except Exception as e:
        print(f"❌ Erreur lors de la publication MQTT : {e}")


# Exécution principale
# Exécution principale
def main():
    print("🔄 Récupération des événements...")
    events = fetch_events()
    filtered_events = filter_events(events, args.keyword)

    new_or_modified_events = []

    for event in filtered_events:
        event_uid = event["uid"]
        event_time = event["start_time"]

        # Vérifier si l'événement est déjà dans le cache
        if event_uid in cache:
            if cache[event_uid] != event_time:
                print(f"🔄 Mise à jour détectée pour '{event['name']}'. Ancienne heure : {cache[event_uid]}, Nouvelle heure : {event_time}")
                new_or_modified_events.append(event)
        else:
            new_or_modified_events.append(event)

    if new_or_modified_events:
        print(f"📅 {len(new_or_modified_events)} événements à envoyer ou mettre à jour.")
        
        for i, event in enumerate(new_or_modified_events):
            # Supprimer l'ancien événement s'il existe déjà dans iCloud
            if event["uid"] in cache:
                delete_event_from_icloud(event)  # Supprime l'ancien événement

            send_to_icloud(event, i + 1)  # Envoie le nouvel événement
            publish_to_mqtt(event)  # Publie l'événement sur MQTT
            cache[event["uid"]] = event["start_time"]  # Mettre à jour le cache
        
        save_cache(cache)
    else:
        print("✅ Aucun événement à mettre à jour ou envoyer.")


if __name__ == "__main__":
    main()
