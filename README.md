## Pré-requis

- **Python** 3.8+
- **Micro fonctionnel** sur votre machine
- **Clé API Gladia**
- **Outil `pip`** (ou équivalent) pour installer les dépendances

## Configuration (`config.py`)

Ajoutez votre clé API Gladia dans le fichier de configuration :

```python
GLADIA_API_KEY = "VOTRE_CLE_API_ICI"
INIT_URL = "https://api.gladia.com/audio/text/..."  # URL spécifique trouvable dans la documentation Gladia
```

## Installation

Clonez ce dépôt ou téléchargez les fichiers (`app.py`, `microphone.py`, `requirements.txt`, etc.).

## Étapes

### 1. Ouvrir un terminal et se placer dans le dossier du projet :

```bash
cd case_gladia
```

### 2. Installer les dépendances :

```bash
pip install -r requirements.txt
```

### 3. Lancer l'application :

```bash
python3 app.py
```

L’application Flask démarre en mode debug sur le port 8000.

Vous devriez voir dans la console un message confirmant le lancement du serveur.
