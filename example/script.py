import argparse
import os
import json
import requests
import time
import uuid
import unicodedata
import pytz
from datetime import datetime, timedelta, timezone
import paho.mqtt.client as mqtt
import re  # Ajout de l'import pour utiliser clean_uid

# Définition de clean_uid
def clean_uid(uid):
    """Nettoie l'UID pour qu'il soit conforme aux noms de topics MQTT."""
    # Remplace les espaces et caractères spéciaux par des underscores
    uid = re.sub(r"[^a-zA-Z0-9_]", "_", uid)
    # Normalise les caractères accentués (é -> e, ç -> c, etc.)
    uid = ''.join(c for c in unicodedata.normalize('NFKD', uid) if unicodedata.category(c) != 'Mn')
    # Convertit en minuscules pour standardisation
    return uid.lower()

# Lire les arguments depuis le script bash
parser = argparse.ArgumentParser(description="Event to iCloud Add-on")
parser.add_argument("--keyword", type=str, required=True)
parser.add_argument("--event_source_url", type=str, required=True)
parser.add_argument("--icloud_username", type=str, required=True)
parser.add_argument("--icloud_password", type=str, required=True)
parser.add_argument("--icloud_calendar_url", type=str, required=True)
parser.add_argument("--mqtt_host", type=str, required=True)
parser.add_argument("--mqtt_port", type=int, required=True)
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

import requests
import pytz
from datetime import datetime, timedelta, timezone

def fetch_events():
    try:
        # URL publique du calendrier Google (flux iCal)
        calendar_url = "https://calendar.google.com/calendar/embed?src=qmda.ca_5spdn7s6bd47b794copl2lpbn8%40group.calendar.google.com&ctz=America%2FToronto"
        
        # Charger le flux iCal depuis l'URL
        print("🔄 Récupération du flux iCal depuis Google Calendar...")
        response = requests.get(calendar_url)

        # Vérification de la réponse
        if response.status_code != 200 or not response.text:
            print("⚠️ Erreur : Impossible de récupérer les événements. Vérifie l'URL.")
            return []

        print(f"✅ Flux iCal récupéré avec succès (Code: {response.status_code})")

        events = []
        max_date = datetime.now(timezone.utc) + timedelta(days=DAYS_IN_FUTURE)

        event_name = ""  # Initialisation de la variable event_name pour éviter l'erreur

        # Lecture ligne par ligne du flux iCal
        print("📜 Analyse du contenu du flux iCal...")
        for line in response.text.splitlines():
            if line.startswith("SUMMARY:"):
                # Extraction du nom de l'événement
                event_name = line.replace("SUMMARY:", "").strip()
                print(f"Debug - Event Name extrait : {event_name}")

            elif line.startswith("DTSTART:"):
                start_time_str = line.replace("DTSTART:", "").strip()

                if start_time_str.endswith("Z"):
                    # L'heure est déjà en UTC (avec Z)
                    start_time = datetime.strptime(start_time_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                else:
                    # L'heure est sans fuseau horaire. On peut supposer que l'heure est en heure locale (par exemple, Paris)
                    start_time = datetime.strptime(start_time_str, "%Y%m%dT%H%M%S")
                    local_tz = pytz.timezone("America/Toronto")  # Fuseau horaire Toronto
                    start_time = local_tz.localize(start_time)  # Localiser l'heure sans fuseau horaire
                    start_time = start_time.astimezone(timezone.utc)  # Convertir en UTC

                # Log pour vérifier la conversion des heures
                print(f"Debug - Heure originale (avant conversion) : {start_time_str}")
                print(f"Debug - Heure convertie (en UTC) : {start_time}")

            elif line.startswith("DTEND:"):
                end_time_str = line.replace("DTEND:", "").strip()

                if end_time_str.endswith("Z"):
                    # L'heure est déjà en UTC (avec Z)
                    end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                else:
                    # L'heure est sans fuseau horaire. On peut supposer que l'heure est en heure locale (par exemple, Paris)
                    end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S")
                    local_tz = pytz.timezone("America/Toronto")  # Fuseau horaire Toronto
                    end_time = local_tz.localize(end_time)  # Localiser l'heure sans fuseau horaire
                    end_time = end_time.astimezone(timezone.utc)  # Convertir en UTC

                # Log pour vérifier la conversion des heures
                print(f"Debug - Heure de fin originale (avant conversion) : {end_time_str}")
                print(f"Debug - Heure de fin convertie (en UTC) : {end_time}")

            elif line.startswith("UID:"):
                event_uid = line.replace("UID:", "").strip()

                if start_time < datetime.now(timezone.utc) or start_time > max_date:
                    continue  # Ignorer les événements hors plage

                # Recherche du mot-clé "Rosalie F" dans le nom de l'événement (insensible à la casse)
                if "rosalie f" in event_name.lower():
                    print(f"Debug - Trouvé l'événement avec le mot-clé : {event_name}")
                    events.append({
                        "name": event_name,
                        "start_time": start_time.strftime("%Y%m%dT%H%M%SZ"),
                        "end_time": end_time.strftime("%Y%m%dT%H%M%SZ"),
                        "uid": event_uid   # Générer un UID unique
                    })
                    print(f"✅ Événement {event_name} ajouté : UID = {event_uid}")

        # Afficher le nombre d'événements extraits
        print(f"📅 Nombre d'événements extraits : {len(events)}")

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
        
       # print(f"📂 Fichier ICS créé : {ics_filename}\n{ics_content}")
        print(f"📂 Fichier ICS créé : {ics_filename}")
        return ics_path
    except Exception as e:
        print(f"❌ Erreur lors de la création du fichier ICS : {e}")
        return None

import subprocess
import os

def send_to_icloud(event, event_index):
    print(f"📤 Envoi de l'événement '{event['name']}' à iCloud...")

    try:
        # Log avant d'envoyer l'événement à iCloud
        print(f"Debug - Envoi de l'événement : {event['name']}, Start: {event['start_time']}, End: {event['end_time']}")

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

        ics_filename = os.path.basename(ics_file)

        # Construire l'URL pour iCloud
        icloud_event_url = f"{args.icloud_calendar_url}{ics_filename}"

        command = (
            f'curl -v -X PUT -u "{args.icloud_username}:{args.icloud_password}" '
            f'-H "Content-Type: text/calendar" '
            f'--data-binary @{ics_file} "{icloud_event_url}"'
        )

        print(f"🔧 Commande exécutée : {command}")
        result = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)

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

        # Nettoyer l'UID pour qu'il ne contienne que des caractères autorisés
        cleaned_uid = clean_uid(event["uid"])

        # Base du topic MQTT (utilisez le discovery prefix "homeassistant")
        topic_base = "homeassistant"

        # Nom du capteur (utilisez l'UID nettoyé)
        sensor_name = f"eventtoicloud_{cleaned_uid}"

        # Payload pour l'état du capteur
        state = event["name"]

        # Attributs du capteur
        attributes = {
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "uid": event["uid"]  # Conservez l'UID original dans les attributs
        }

        # Configuration du capteur pour MQTT Discovery
        config_topic = f"{topic_base}/sensor/eventtoicloud/{sensor_name}/config"
        state_topic = f"{topic_base}/sensor/eventtoicloud/{sensor_name}/state"
        attr_topic = f"{topic_base}/sensor/eventtoicloud/{sensor_name}/attributes"

        # Payload de configuration pour MQTT Discovery
        config_payload = {
            "name": f"Événement {event['name']}",  # Nom affiché dans Home Assistant
            "state_topic": state_topic,  # Topic pour l'état du capteur
            "json_attributes_topic": attr_topic,  # Topic pour les attributs
            "unique_id": sensor_name,  # ID unique pour le capteur (utilisez l'UID nettoyé)
            "device": {
                "identifiers": ["eventtoicloud_device"],  # Identifiant du dispositif
                "name": "EventToiCloud",  # Nom du dispositif
                "manufacturer": "EventToiCloud Add-on"  # Fabricant
            }
        }

        # Publier la configuration, l'état et les attributs
        client.publish(config_topic, json.dumps(config_payload), retain=False)
        client.publish(state_topic, state, retain=False)
        client.publish(attr_topic, json.dumps(attributes), retain=False)

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

        if event_uid in cache:
            if cache[event_uid] != event_time:
                print(f"🔄 Mise à jour détectée pour '{event['name']}'. Ancienne heure : {cache[event_uid]}, Nouvelle heure : {event_time}")
                new_or_modified_events.append(event)
        else:
            new_or_modified_events.append(event)

    if new_or_modified_events:
        print(f"📅 {len(new_or_modified_events)} événements à envoyer ou mettre à jour.")
        
        for i, event in enumerate(new_or_modified_events):
            if event["uid"] in cache:
                delete_event_from_icloud(event)  # Supprime l'ancien événement

            send_to_icloud(event, i + 1)  # Envoie le nouvel événement
            publish_to_mqtt(event)  # Publie l'événement sur MQTT
            cache[event["uid"]] = event["start_time"]  # Mettre à jour le cache
            print(f"Debug - Cache mis à jour pour l'événement '{event['name']}' avec l'heure de début : {event['start_time']}")
            time.sleep(3)
        
        save_cache(cache)
    else:
        print("✅ Aucun événement à mettre à jour ou envoyer.")



if __name__ == "__main__":
    main()
