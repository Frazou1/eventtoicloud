FROM python:3.11-slim

# Mise à jour et installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libgtk2.0-0 \
    libgbm-dev \
    libasound2 \
    jq \
    curl \ 
    && rm -rf /var/lib/apt/lists/*

# Installer les packages Python nécessaires
RUN pip install --no-cache-dir selenium==4.* webdriver-manager==4.* beautifulsoup4 paho-mqtt==1.6.1 requests icalendar pytz

# Copier les fichiers nécessaires dans le conteneur
COPY run.sh /run.sh
COPY script.py /script.py

# Donner les permissions d'exécution au script
RUN chmod a+x /run.sh

# Exécuter le script au démarrage du conteneur
CMD [ "/run.sh" ]
