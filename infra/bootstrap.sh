#!/usr/bin/env bash
# Einmaliges GCP-Setup für den Cloud-Run-Deploy von CoMark.
# Idempotent = kann mehrfach laufen, ohne beim zweiten Mal Fehler zu werfen
# (jeder Schritt prüft erst "gibt's das schon?", bevor er etwas anlegt).
#
#   PROJECT_ID=<PROJEKT-ID> REGION=europe-west3 GITHUB_REPO=NilsHellwig/CoMark \
#     ./infra/bootstrap.sh
#
# Voraussetzungen: gcloud ist installiert & eingeloggt, du hast eine
# Neon-Postgres-Connection-String parat (wird weiter unten abgefragt).

# set -e  → Script bricht sofort ab, sobald IRGENDEIN Befehl fehlschlägt
#           (Exit-Code ≠ 0). Ohne das würde bash einfach mit der nächsten
#           Zeile weitermachen, auch wenn z.B. das Projekt gar nicht existiert.
# set -u  → Zugriff auf eine nicht gesetzte Variable ist ein Fehler (bricht ab),
#           statt sie stillschweigend als leeren String zu behandeln — schützt
#           vor Tippfehlern in Variablennamen.
# set -o pipefail → bei "befehl1 | befehl2" zählt auch ein Fehler in befehl1
#           als Fehler der ganzen Pipe (normal bash schaut nur auf befehl2).
set -euo pipefail

# --- Eingabe-Parameter einlesen ---------------------------------------------
# "${VAR:?nachricht}"  → lies VAR aus der Umgebung (siehe Aufruf oben, z.B.
#                        `PROJECT_ID=<PROJEKT-ID> ./bootstrap.sh`). Ist VAR
#                        NICHT gesetzt → Script bricht sofort mit "nachricht" ab.
# "${VAR:-standard}"   → wie oben, aber statt abzubrechen wird "standard"
#                        genommen, wenn VAR fehlt.
PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
GITHUB_REPO="${GITHUB_REPO:-NilsHellwig/CoMark}"
# "${GITHUB_REPO%%/*}" = Text-Zuschnitt: "lösche vom Ende des längsten Treffers
# von '/*' " → aus "NilsHellwig/CoMark" wird "NilsHellwig" (nur der Besitzer,
# ohne Repo-Namen). Brauchen wir gleich für die WIF-Regel (Zeile ~70).
REPO_OWNER="${GITHUB_REPO%%/*}"
AR_REPO="comark"                                   # Name des Docker-Image-Lagers
SA_NAME="comark-deployer"                          # Name des "Roboter-Kontos" fürs Deployen
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"  # so heißt jeder Service Account: name@projekt.iam.gserviceaccount.com
POOL="github"                                      # Name der "Vertrauens-Zone" für GitHub (siehe unten)
PROVIDER="github"                                  # Name der Regel innerhalb dieser Zone

# Ab jetzt zielen alle `gcloud`-Befehle (ohne extra --project-Flag) auf dieses
# Projekt. >/dev/null unterdrückt nur die Erfolgsmeldung, kein Fehler wird verschluckt.
gcloud config set project "$PROJECT_ID" >/dev/null

# Jedes Projekt hat neben der von dir gewählten PROJECT_ID auch eine von Google
# automatisch vergebene, rein numerische PROJECT_NUMBER (ändert sich nie).
# Wir brauchen sie gleich, weil der Cloud-Run-"Bewohner"-Account (der Account,
# unter dem der Container tatsächlich läuft) nach diesem Schema benannt ist:
#   <PROJECT_NUMBER>-compute@developer.gserviceaccount.com
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

# --- 1) APIs freischalten ----------------------------------------------------
# Ein frisches GCP-Projekt hat fast alle "Services" (= einzelne Google-Cloud-
# Funktionen) deaktiviert. Jede muss einmal pro Projekt explizit angeschaltet
# werden, bevor man sie benutzen kann.
echo "› Enabling APIs"
gcloud services enable \
  run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com iamcredentials.googleapis.com \
  sts.googleapis.com
#   run.googleapis.com            → Cloud Run selbst (unseren Dienst deployen)
#   artifactregistry.googleapis.com → das Docker-Image-Lager
#   secretmanager.googleapis.com  → der Passwort-/Schlüssel-Tresor
#   iamcredentials.googleapis.com → "kurzlebige Ausweise für einen anderen
#                                    Account ausstellen" — Grundbaustein für
#                                    die passwortlose GitHub-Anmeldung (WIF)
#   sts.googleapis.com            → der eigentliche Token-Tausch-Dienst, den
#                                    WIF benutzt (GitHub-Token → Google-Token)

# --- 2) Docker-Image-Lager (Artifact Registry) anlegen -----------------------
# Muster "erst nachschauen, ob's existiert; wenn nicht, anlegen" (idempotent):
#   `describe` prüft nur, ob es das Repo gibt (Exit-Code 0 = ja, ≠0 = nein).
#   `>/dev/null 2>&1` unterdrückt jede Ausgabe (Erfolg wie Fehler) — uns
#   interessiert nur der Exit-Code.
#   `||` = "ODER": der Teil danach läuft nur, wenn `describe` fehlgeschlagen ist.
echo "› Artifact Registry repo ($AR_REPO, $REGION)"
gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$AR_REPO" --repository-format=docker --location="$REGION"

# --- 3) redis-Image ins eigene Lager spiegeln --------------------------------
echo "› Mirroring redis:8-alpine into Artifact Registry"
# Der Deploy-Workflow spiegelt das bei jedem Lauf ohnehin neu (auf einem
# amd64-GitHub-Runner) — hier zusätzlich, damit ein erster manueller Deploy
# schon funktioniert, ohne vorher einen Workflow-Lauf abzuwarten.
#
# WICHTIG: `redis:8-alpine` auf Docker Hub ist eigentlich ein "Multi-Arch"-
# Image — enthält mehrere Varianten (amd64, arm64, ...) in einem Manifest.
# Ein normales `docker pull` holt sich davon NUR die zu DEINEM Rechner
# passende Variante (auf einem Apple-Silicon-Mac: arm64!). Würde man die dann
# mit `docker tag` + `docker push` hochladen, läge im Lager nur die arm64-
# Version — Cloud Run läuft aber auf amd64 und könnte sie gar nicht starten
# ("exec format error", genau der Fehler, den wir hatten).
# `docker buildx imagetools create` umgeht das: es kopiert das komplette
# Multi-Arch-Manifest 1:1 weiter, ohne es je selbst herunterzuladen.
REDIS_DST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/redis:8-alpine"
# Sagt deinem lokalen `docker`-Kommando: "wenn du zu diesem Registry-Host
# etwas pushst, benutze dafür meine gcloud-Anmeldung als Passwort-Ersatz."
# Trägt dazu einen Eintrag in ~/.docker/config.json ein.
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
# --tag "$REDIS_DST"  = "und veröffentliche das Ergebnis unter diesem Namen"
# (Quelle: `redis:8-alpine` von Docker Hub → Ziel: unser eigenes Lager)
docker buildx imagetools create --tag "$REDIS_DST" redis:8-alpine

# --- 4) Service Account für den Deploy-Vorgang ("der Handwerker") -----------
# Ein Service Account ist ein "Benutzerkonto für ein Programm" statt für einen
# Menschen. GitHub Actions "wird" gleich dieser Account, wenn es Images baut,
# hochlädt und Cloud Run sagt "starte diese neue Version".
echo "› Service account $SA_EMAIL"
gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$SA_NAME" --display-name="CoMark deployer"

# Jetzt bekommt dieser Account die nötigen Rechte (IAM-Rollen). Eine IAM-Rolle
# ist wie ein Zugangs-Badge: "darf Cloud-Run-Dienste anlegen/ändern", "darf
# Images hochladen", usw. Die Schleife hängt einfach 4 solcher Badges an
# denselben Account, indem sie `add-iam-policy-binding` viermal aufruft.
#
# Die Bestandteile dieses einen Aufrufs im Detail:
#   gcloud projects add-iam-policy-binding "$PROJECT_ID"
#       Unterbefehl: "füge dem Projekt $PROJECT_ID eine neue Berechtigungs-
#       Zeile hinzu". Jedes Projekt hat eine Liste "wer darf was" (die
#       IAM-Policy) — der Befehl ergänzt dort eine Zeile.
#   --member="serviceAccount:${SA_EMAIL}"
#       WER die Berechtigung bekommt. Das Präfix "serviceAccount:" sagt
#       Google "das ist ein Programm-Konto" (Gegenstück zu "user:" für einen
#       Menschen oder "principalSet://..." wie bei der WIF-Bindung weiter
#       unten). Danach die E-Mail-Adresse des Kontos.
#   --role="$role"
#       WELCHE Berechtigung. $role ist die Schleifenvariable — der Befehl
#       läuft also einmal pro Eintrag in der Liste oben (4x insgesamt).
#   --condition=None
#       IAM-Bindungen können optional an eine Bedingung geknüpft sein (z.B.
#       "nur bis Datum X"). --condition=None heißt explizit "keine Bedingung,
#       gilt uneingeschränkt" — ohne dieses Flag würde gcloud interaktiv
#       nachfragen, was ein Script wie dieses hier blockieren würde.
#   >/dev/null
#       unterdrückt die Ausgabe (sonst druckt gcloud die komplette,
#       aktualisierte Policy als YAML aus — hier nicht gebraucht).
for role in roles/run.admin roles/artifactregistry.writer \
            roles/secretmanager.secretAccessor roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" --role="$role" --condition=None >/dev/null
done
#   roles/run.admin                    → Cloud-Run-Dienste anlegen/ändern/löschen
#   roles/artifactregistry.writer      → Docker-Images ins Lager hochladen
#   roles/secretmanager.secretAccessor → Secrets lesen dürfen (braucht der
#                                         Deploy-Job für die DB-Migration)
#   roles/iam.serviceAccountUser       → darf sich "als" einen anderen Service
#                                         Account ausgeben bzw. ihn benutzen lassen

# Cloud Run führt den Container am Ende NICHT als "comark-deployer" aus,
# sondern als den automatisch angelegten "Compute default"-Account (den
# "Bewohner", siehe PROJECT_NUMBER oben). Damit der Deployer diesen Bewohner-
# Account beim Deploy "benutzen" (technisch: actAs) darf, braucht er extra
# diese eine Berechtigung GENAU auf diesen einen Account:
#   `|| true` am Ende = "falls dieser Befehl fehlschlägt (z.B. weil die
#   Bindung schon existiert), brich das ganze Script trotzdem NICHT ab"
#   (normalerweise würde `set -e` das tun).
echo "› Cloud Run runtime SA darf sich vom Deployer 'benutzen' lassen"
gcloud iam service-accounts add-iam-policy-binding \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --member="serviceAccount:${SA_EMAIL}" --role=roles/iam.serviceAccountUser >/dev/null || true

# --- 5) Workload Identity Federation — GitHub darf sich ohne Passwort anmelden
# Statt eine Schlüssel-Datei (= dauerhaftes Passwort) als GitHub-Secret zu
# hinterlegen, wird hier eine reine VERTRAUENSREGEL eingerichtet: "wenn sich
# jemand mit einem echten, von GitHub signierten Ausweis meldet, der zu
# unserem Repo gehört, dann behandle ihn wie den comark-deployer-Account."
echo "› Workload Identity Federation for github.com/${GITHUB_REPO}"

# Ein "Pool" ist die grobe Vertrauens-Zone — hier: "GitHub Actions allgemein".
gcloud iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub Actions"

# Ein "Provider" innerhalb des Pools ist die konkrete Regel: WIE erkennt man
# einen echten GitHub-Ausweis, und WELCHE Bedingung muss er erfüllen.
#
# WICHTIG (bash): innerhalb eines mit "\" fortgesetzten Befehls dürfen KEINE
# "#"-Kommentarzeilen dazwischenstehen — eine Kommentarzeile hat kein "\" am
# Ende, beendet also die Fortsetzung vorzeitig, und alles danach würde als
# neuer, eigenständiger (kaputter) Befehl ausgeführt. Deshalb stehen die
# Erklärungen zu den einzelnen Flags hier VOR dem Befehl, nicht dazwischen:
#
#   --issuer-uri=...          Ausweise sind nur echt, wenn sie von GENAU
#                             diesem GitHub-eigenen Server signiert wurden
#                             (kryptografisch überprüfbar).
#   --attribute-mapping=...   Aus dem GitHub-Ausweis interessieren uns diese
#                             drei Felder, gib sie unter diesen Namen weiter
#                             (u.a. WER hat den Workflow ausgelöst, WESSEN
#                             Repo es ist).
#   --attribute-condition=... Die eigentliche Prüfung: "akzeptiere nur
#                             Ausweise, bei denen repository_owner genau
#                             'NilsHellwig' ist." ACHTUNG: das prüft nur den
#                             BESITZER, nicht den genauen Repo-Namen — der
#                             wird erst gleich unten (Schritt 6) verlangt.
gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location=global --workload-identity-pool="$POOL" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
    --location=global --workload-identity-pool="$POOL" --display-name="GitHub" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == '${REPO_OWNER}'"

# --- 6) Genau festlegen: welches Repo darf sich als comark-deployer ausgeben -
POOL_NAME="$(gcloud iam workload-identity-pools describe "$POOL" --location=global --format='value(name)')"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}" >/dev/null
# Das ist die zweite, ENGERE Prüfung (zusätzlich zu Schritt 5): hier wird
# nicht nur der Besitzer, sondern das komplette "Besitzer/Repo-Name"-Paar
# verlangt (z.B. "NilsHellwig/CoMark"). Erst wenn BEIDE Prüfungen (Schritt 5
# UND 6) durchgehen, bekommt der GitHub-Workflow ein Token, das wirkt, als
# wäre er "comark-deployer". Würde das Repo umbenannt, müsste diese Zeile
# hier neu gesetzt werden (Schritt 5 würde weiterhin durchgehen, Schritt 6 nicht).

# --- 7) Secrets anlegen (der "Tresor") ---------------------------------------
echo "› Secrets"
# Kleine Hilfsfunktion: legt ein Secret nur an, wenn es noch nicht existiert
# (idempotent) — sonst nur ein Hinweis, wie man es manuell aktualisiert.
create_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    echo "  $name — exists (keep). Update: gcloud secrets versions add $name --data-file=-"
  else
    # `printf '%s' "$value" | gcloud secrets create ... --data-file=-`
    # bedeutet: "lies den Inhalt nicht aus einer Datei, sondern aus dem, was
    # gerade über die Pipe (stdin) reinkommt" — hier: der Wert selbst.
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic
    echo "  $name — created"
  fi
}
# read -rsp "..." VAR   → fragt interaktiv ab; -s = "silent" (Eingabe wird
#                         NICHT am Bildschirm angezeigt, wie bei einem
#                         Passwort-Feld), -p = zeigt den Text als Prompt.
# read -rp  "..." VAR   → wie oben, aber sichtbar (für die Client-ID, die
#                         kein Geheimnis ist).
# das `; echo` danach erzwingt nur einen Zeilenumbruch nach der (unsichtbaren)
# Eingabe, damit die nächste Zeile nicht mittendrin anfängt.
read -rsp "  Neon DATABASE_URL (postgres://…): " NEON_URL; echo
read -rp  "  Google OAuth client id  (blank = Google login off): " G_ID
read -rsp "  Google OAuth client secret (blank = off): " G_SECRET; echo
create_secret comark-secret-key         "$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
create_secret comark-database-url       "$NEON_URL"
# "${G_ID:-unset}" → falls leer gelassen (kein Google-Login gewünscht), wird
# stattdessen der Platzhalter-Text "unset" gespeichert (ein Secret darf nicht
# leer sein). Der Backend-Code erkennt "unset" später selbst als "kein
# echter Google-Client" und lässt den Google-Login-Button einfach weg.
create_secret comark-google-client-id   "${G_ID:-unset}"
create_secret comark-google-client-secret "${G_SECRET:-unset}"

# --- 8) Dem LAUFENDEN Container erlauben, die Secrets zu lesen --------------
# Wichtig: das ist ein ANDERER Account als der Deployer aus Schritt 4!
#   - comark-deployer          = baut & startet den Deploy (der "Handwerker")
#   - <NUMMER>-compute@...     = der Account, unter dem der Container läuft,
#                                 NACHDEM er gestartet ist (der "Bewohner")
# Beide brauchen secretAccessor, aber aus verschiedenen Gründen. Diesen
# zweiten Schritt hatte die erste Version dieses Scripts vergessen — führte
# zu "Permission denied on secret ..." beim allerersten Deploy-Versuch.
echo "› Granting the Cloud Run runtime SA read access to Secret Manager"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role=roles/secretmanager.secretAccessor --condition=None >/dev/null
# (Projekt-weite Berechtigung statt einzeln pro Secret — einfacher, und
# umgeht einen kaputten lokalen `gcloud secrets add-iam-policy-binding`-Befehl
# auf manchen Homebrew-Installationen, siehe docs/google-cloud-explained.md.)

# Die vollständige Adresse des Providers aus Schritt 5 — das ist genau der
# String, den GitHub Actions als `GCP_WIF_PROVIDER` braucht (Zeiger 1 aus der
# WIF-Erklärung: "wohin soll sich GitHub überhaupt ausweisen gehen").
PROVIDER_NAME="$(gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location=global --workload-identity-pool="$POOL" --format='value(name)')"

# Abschluss: alle Werte ausgeben, die man jetzt von Hand bei GitHub als
# Repository Variables/Secrets eintragen muss (Settings → Secrets and
# variables → Actions). Danach übernimmt der `deploy`-Job in ci.yml alles
# Weitere automatisch bei jedem Push auf main.
cat <<EOF

────────────────────────────────────────────────────────────────────────
Done. Set these on the GitHub repo (Settings → Secrets and variables → Actions):

  Variables
    GCP_PROJECT_ID     ${PROJECT_ID}
    GCP_REGION         ${REGION}
    GCP_WIF_PROVIDER   ${PROVIDER_NAME}
    GCP_DEPLOYER_SA    ${SA_EMAIL}
    GOOGLE_ENABLED     $([ -n "${G_ID}" ] && echo true || echo false)
    PUBLIC_URL         (leave unset for the first deploy; the workflow prints it)

  Secrets
    NEON_DATABASE_URL  <the same Neon connection string>

Then push to main (or run the CI workflow) to deploy.
────────────────────────────────────────────────────────────────────────
EOF
