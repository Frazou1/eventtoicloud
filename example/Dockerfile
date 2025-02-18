FROM ghcr.io/home-assistant/amd64-base-python:3.10

# Définition des variables d’environnement
ENV LANG C.UTF-8
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2

# Copier les fichiers nécessaires
COPY run.sh /
COPY script.py /script.py
COPY requirements.txt /requirements.txt

# Installation des dépendances Python
RUN pip install --no-cache-dir -r /requirements.txt

# Donner les permissions nécessaires au script
RUN chmod a+x /run.sh

# Exécution du script via run.sh
CMD [ "/run.sh" ]
