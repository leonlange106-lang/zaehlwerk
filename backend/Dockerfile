# --------------------------------------------------------------------------
# Stufe 1: Frontend bauen (React + Mantine + Vite -> statische Dateien)
# --------------------------------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
# Erst nur die Manifeste kopieren: der npm-ci-Schritt bleibt gecacht, solange
# sich die Abhängigkeiten nicht ändern.
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY webapp/ ./
RUN npm run build          # -> /web/dist

# --------------------------------------------------------------------------
# Stufe 2: Python-Backend
# --------------------------------------------------------------------------
FROM python:3.12-slim
WORKDIR /app

# Kennung der Systemabhaengigkeiten. Wird sie erhoeht, verwirft Docker den
# zwischengespeicherten apt-Schritt und installiert neu. Ohne diesen Griff
# behaelt der Supervisor eine alte Ebene bei, solange sich der Befehl selbst
# nicht aendert - und genau daran scheiterte die Erkennung nach 3.6.0.
ARG DEPS_VERSION=4

# Tesseract samt deutschen Sprachdaten und die von OpenCV benoetigten
# Systembibliotheken. libgl1 und libglib2.0-0 fehlen im slim-Abbild und sind
# auch fuer die headless-Variante erforderlich.
# Die Paketlisten werden im selben Schritt geloescht, damit sie nicht als
# Ebene im Abbild verbleiben.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-deu \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Der Build scheitert hier, wenn die Pakete fehlen. Besser ein Abbruch mit
# klarer Meldung als ein Abbild, das erst im Betrieb die Kamera verweigert.
RUN tesseract --version \
    && tesseract --list-langs | grep -q deu \
    && echo "Tesseract samt deutscher Sprachdaten vorhanden."

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Gegenprobe auf Python-Seite: die Bindung an Tesseract und OpenCV muss
# tatsaechlich ladbar sein, nicht nur das Systempaket vorhanden.
RUN python -c "import cv2, pytesseract, PIL; \
    print('OpenCV', cv2.__version__, '| Tesseract', pytesseract.get_tesseract_version())"

COPY app ./app
# Statisches Frontend aus der Build-Stufe (ersetzt das frühere Vue-Frontend).
COPY --from=web /web/dist ./frontend
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
