#!/usr/bin/env python3
import argparse
import requests
from datetime import datetime, timedelta, timezone
import re
import unicodedata
# import os
# import json
# import time
# import uuid
# import paho.mqtt.client as mqtt
# import subprocess

# Fonction pour nettoyer l'UID (non utilisée pour la simple liste)
# def clean_uid(uid):
#     """Nettoie l'UID pour qu'il soit conforme aux noms de topics MQTT."""
#     uid = re.sub(r"[^a-zA-Z0-9_]", "_", uid)
#     uid = ''.join(c for c in unicodedata.normalize('NFKD', uid) if unicodedata.category(c) != 'Mn')
#     return uid.lower()

# Lecture des arguments
parser = argparse.ArgumentParser(description="Liste des événements")
parser.add_argument("--keyword", type=str, required=True)
parser.add_argument("--event_source_url", type=str, required=True)
# Les arguments ci-dessous sont commentés car ils ne sont plus utilisés pour la liste
# parser.add_argument("--icloud_username", type=str, required=True)
# parser.add_argument("--icloud_password", type=str, required=True)
# parser.add_argument("--icloud_calendar_url", type=str, required=True)
# parser.add_argument("--mqtt_host", type=str, required=True)
# parser.add_argument("--mqtt_port", type=int, required=True)
# parser.add_argument("--mqtt_username", type=str, required=True)
# parser.add_argument("--mqtt_password", type=str, required=True)
args = parser.parse_args()

# Variables et répertoires liés au cache (non utilisés ici)
# CACHE_FILE = "/config/event_cache.json"
# ICS_DIR = "/config/file_notifications/"
DAYS_IN_FUTURE = 30  # Nombre de jours dans le futur à considérer

# Fonctions pour charger et sauvegarder le cache (non utilisées)
# def load_cache():
#     if os.path.exists(CACHE_FILE):
#         with open(CACHE_FILE, "r") as file:
#             return json.load(file)
#     return {}
#
# def save_cache(cache):
#     with open(CACHE_FILE, "w") as file:
#         json.dump(cache, file)
#
# cache = load_cache()

# Fonction pour récupérer les événements depuis le fichier ICS
def fetch_events():
    try:
        response = requests.get(args.event_source_url)
        
        if response.status_code != 200 or not response.text:
            print("⚠️ Erreur : Impossible de récupérer les événements. Vérifie l'URL.")
            return []
        
        events = []
        max_date = datetime.now(timezone.utc) + timedelta(days=DAYS_IN_FUTURE)
        event_name = ""
        start_time = None
        end_time = None
        event_uid = ""
        
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
                
                # Vérifier que l'événement est dans la plage temporelle souhaitée
                if start_time < datetime.now(timezone.utc) or start_time > max_date:
                    continue
                
                events.append({
                    "name": event_name,
                    "start_time": start_time.strftime("%Y%m%dT%H%M%SZ"),
                    "end_time": end_time.strftime("%Y%m%dT%H%M%SZ"),
                    "uid": event_uid
                })
        
        return events
    except Exception as e:
        print(f"❌ Erreur lors du traitement du calendrier iCal : {e}")
        return []

# Fonction pour filtrer les événements contenant le mot-clé
def filter_events(events, keyword):
    return [event for event in events if keyword.lower() in event["name"].lower()]

# Les fonctions suivantes sont désactivées car elles ne sont pas utilisées pour l'affichage de la liste
# def create_ics(event, event_index):
#     ...
#
# def send_to_icloud(event, event_index):
#     ...
#
# def delete_event_from_icloud(event):
#     ...
#
# def publish_to_mqtt(event):
#     ...

# Fonction principale : liste simplement les événements filtrés
def main():
    print("🔄 Récupération des événements...")
    events = fetch_events()
    filtered_events = filter_events(events, args.keyword)
    
    if filtered_events:
        print("📅 Liste des événements filtrés :")
        for event in filtered_events:
            print(f" - {event['name']} (Début : {event['start_time']}, Fin : {event['end_time']})")
    else:
        print("✅ Aucun événement trouvé.")

if __name__ == "__main__":
    main()
