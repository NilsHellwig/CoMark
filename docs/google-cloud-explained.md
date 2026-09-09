# Google Cloud für CoMark — erklärt für Einsteiger

Diese Datei erklärt **alles**, was für das automatische Deployment bei Google
Cloud eingerichtet wurde: welche Dateien im Projekt dafür sorgen, was bei
Google Cloud aktiviert/angelegt wurde, welche Rechte wer hat, und welche
Befehle dafür gelaufen sind. Kein Google-Cloud-Vorwissen nötig — jeder Begriff
wird erklärt.

Die kurze „mach das"-Anleitung für ein *neues* Setup steht in
[deploy-gcp.md](deploy-gcp.md). Hier geht's ums **Verstehen**.

---

## 1. Das Ziel in einem Satz

Du machst `git push`, ein paar Minuten später läuft die neue Version der App
unter `https://comark-<hash>.<region>.run.app` — ohne dass du selbst einen
Server mietest, einrichtest oder pflegst.

---

## 2. Die Bauteile (mit Analogien)

| Begriff | Was es ist | Analogie |
|---|---|---|
| **Container / Docker-Image** | Ein fertig gepacktes Programm samt allem, was es zum Laufen braucht | Ein versiegelter Umzugskarton mit Möbel + Aufbauanleitung |
| **Cloud Run** | Ein Dienst, der Container startet, sobald jemand die App aufruft, und sie wieder abschaltet, wenn niemand da ist | Ein Hotelzimmer, das nur bezahlt wird, wenn jemand eingecheckt ist |
| **Artifact Registry** | Ein privates Lager für deine Docker-Images | Ein Lagerhaus, in das nur du (und Cloud Run) reindarf |
| **Secret Manager** | Ein Tresor für Passwörter/Schlüssel, die die App braucht | Ein Schließfach — die App bekommt beim Start den Inhalt gezeigt, sonst sieht ihn niemand |
| **Service Account (SA)** | Ein „Benutzerkonto für Programme" (kein Mensch) | Ein Firmenausweis, den ein Roboter statt einer Person trägt |
| **IAM-Rolle** | Eine Berechtigung, die man einem Account gibt | Ein Zugangs-Badge: „darf ins Lagerhaus", „darf den Tresor öffnen" |
| **Workload Identity Federation (WIF)** | Erlaubt GitHub Actions, sich bei Google auszuweisen — **ohne** ein Passwort/Schlüssel-Datei irgendwo zu speichern | Ein Türsteher, der GitHub am Ausweis (nicht am Passwort) erkennt |
| **Neon** | Eine (externe, nicht-Google) verwaltete Postgres-Datenbank | Ein extern gemietetes Aktenarchiv |

---

## 3. Die Architektur — ein Cloud-Run-Dienst mit vier Containern

```
                 https://comark-<hash>.<region>.run.app
                                  │
                     ┌────────────▼────────────┐
                     │   Cloud-Run-Dienst       │
                     │        "comark"          │
                     │                          │
                     │  ┌────────────────────┐  │
                     │  │ caddy (Empfang)    │◄─┼── einziger Container mit
                     │  │  :8080             │  │   Ports nach außen
                     │  └───┬───────────┬────┘  │
                     │      │           │       │
                     │  ┌───▼──────┐ ┌──▼─────┐ │
                     │  │ backend  │ │frontend│ │
                     │  │ FastAPI  │ │Next.js │ │
                     │  │ :8897    │ │ :8896  │ │
                     │  └───┬──────┘ └────────┘ │
                     │      │                   │
                     │  ┌───▼──────┐             │
                     │  │  redis   │  (nur Cache,│
                     │  │  :6379   │   nichts     │
                     │  └──────────┘   Wichtiges) │
                     └──────────┬───────────────┘
                                │ (verschlüsselte Verbindung, TLS)
                     ┌──────────▼──────────┐
                     │   Neon (Postgres)    │  ← extern, nicht Google
                     │  die eigentliche DB   │
                     └───────────────────────┘
```

**Warum vier Container in einem Dienst statt vier einzelne Dienste?** Weil
alle vier zusammen **eine** Web-Adresse (`https://comark-…run.app`) teilen. Das
Backend setzt beim Login ein Cookie — Browser-Cookies funktionieren nur
zuverlässig, wenn Frontend und Backend von *derselben* Adresse kommen. `caddy`
ist der Türsteher, der eingehende Anfragen an Backend oder Frontend
weiterleitet, je nachdem welcher Pfad aufgerufen wird (`/api/v1/...` →
Backend, alles andere → Frontend).

**Warum `min-instances=0` / `max-instances=1`?** Die Live-Zusammenarbeit
(gleichzeitiges Editieren) hält den Zustand aller offenen Dokumente im
Arbeitsspeicher **eines** laufenden Backend-Prozesses. Mit genau einer
Instanz bleibt das immer korrekt. `min=0` heißt: läuft niemand ein
Dokument, wird die Instanz komplett abgeschaltet → kostet nichts. Der erste
Aufruf danach braucht ein paar Sekunden zum Hochfahren ("Cold Start").

---

## 4. Was im Projekt dafür hinzugekommen ist

| Datei | Wofür |
|---|---|
| `infra/cloudrun-service.yaml` | Die komplette Beschreibung des Cloud-Run-Dienstes: welche vier Container, wie viel CPU/RAM jeder bekommt, welche Umgebungsvariablen/Secrets, welche Ports. Das ist die „Bauanleitung", die bei jedem Deploy an Google geschickt wird. |
| `infra/Caddyfile` | Die Konfiguration für den `caddy`-Türsteher-Container: welcher Pfad geht wohin. |
| `infra/caddy.Dockerfile` | Baut das `caddy`-Container-Image (Standard-Caddy + unsere Caddyfile reinkopiert). |
| `infra/bootstrap.sh` | Ein Skript, das **einmalig** alles bei Google Cloud einrichtet (Details unten). Wird nur beim Erst-Setup gebraucht, nicht bei jedem Deploy. |
| `.github/workflows/ci.yml` → Job `deploy` | Läuft bei **jedem Push auf `main`**, nachdem die Tests grün sind. Baut die Images, spielt Datenbank-Änderungen ein, schickt die Bauanleitung an Cloud Run. Details in Abschnitt 6. |
| `backend/app/core/config.py` | Wandelt die Neon-Datenbank-Adresse in das Format um, das unser Code versteht, und erzwingt eine verschlüsselte Verbindung zu ihr. |
| `backend/docker/entrypoint.sh` | Lässt das Backend beim Start in Cloud Run **keine** Datenbank-Migration mehr laufen (das übernimmt jetzt der Deploy-Schritt selbst, kontrollierter). |
| `frontend/.../use-collab-doc.ts` | Die Live-Zusammenarbeits-Verbindung geht in Produktion über dieselbe Adresse wie die Webseite (statt einen extra Port anzunehmen, den es in Cloud Run nicht gibt). |

---

## 5. Was bei Google Cloud eingerichtet wurde

Alles unten passiert im GCP-Projekt **`<PROJEKT-ID>`** (Region
**`europe-west3`**, Frankfurt), Projektnummer **`<PROJEKTNUMMER>`**.

### 5.1 Abrechnung
Ein GCP-Projekt braucht ein verknüpftes Rechnungskonto, auch wenn am Ende
nichts oder fast nichts bezahlt wird (Cloud Run hat ein kostenloses
Kontingent). → dein bestehendes Konto `XXXXXX-XXXXXX-XXXXXX` wurde verknüpft.

### 5.2 Aktivierte „APIs" (= Funktionen freischalten)
Ein frisches GCP-Projekt kann noch nichts — jede Funktion muss einmal
„eingeschaltet" werden:

- `run.googleapis.com` — Cloud Run selbst
- `artifactregistry.googleapis.com` — das Docker-Image-Lager
- `secretmanager.googleapis.com` — der Passwort-Tresor
- `iamcredentials.googleapis.com`, `sts.googleapis.com` — nötig für die
  passwortlose GitHub-Anmeldung (WIF, siehe 5.5)

### 5.3 Artifact Registry — das Image-Lager
Ein Docker-Repository namens **`comark`** wurde angelegt. Dort landen bei
jedem Deploy drei neue Images: `backend`, `frontend`, `caddy` (und einmalig
eine Kopie von `redis`, siehe Kasten unten).

### 5.4 Zwei „Konten für Programme" (Service Accounts)

| Service Account | Rolle im Ablauf | Rechte (IAM-Rollen) |
|---|---|---|
| `comark-deployer@<PROJEKT-ID>.iam.gserviceaccount.com` | **Der Handwerker.** GitHub Actions „ist" dieser Account während des Deployments. Baut Images, lädt sie hoch, sagt Cloud Run „starte diese neue Version". | `run.admin` (Cloud-Run-Dienste anlegen/ändern), `artifactregistry.writer` (Images hochladen), `secretmanager.secretAccessor` (Secrets lesen, für die DB-Migration), `iam.serviceAccountUser` (darf den nächsten Account „benutzen") |
| `<PROJEKTNUMMER>-compute@developer.gserviceaccount.com` | **Der Bewohner.** Das ist der Account, *unter dem der laufende Container selbst* arbeitet (von Google automatisch für jedes Projekt angelegt). | `secretmanager.secretAccessor` — muss die vier Secrets lesen dürfen, um zu starten (`SECRET_KEY`, `DATABASE_URL`, Google-Client-ID/-Secret) |

**Wichtiger Unterschied:** der *Deployer* baut und startet die App, der
*Bewohner* (Compute-Account) führt sie dann aus. Beide brauchen
`secretmanager.secretAccessor`, aber aus verschiedenen Gründen — das hat uns
beim Einrichten tatsächlich eine Weile aufgehalten (siehe Abschnitt 8).

### 5.5 Workload Identity Federation — GitHub ohne Passwort anmelden
Statt eine Passwort-Datei im GitHub-Repo zu hinterlegen (Sicherheitsrisiko,
wenn sie mal geleakt wird), wurde eine **Vertrauensbeziehung** eingerichtet:
„Wenn sich jemand meldet, der beweisen kann, dass er *GitHub Actions im Repo
NilsHellwig/CoMark* ist, dann darf er sich als `comark-deployer` ausgeben."
Dafür wurden angelegt:
- ein **Workload Identity Pool** `github` (die „Vertrauens-Zone")
- ein **Provider** `github` darin, der GitHub als vertrauenswürdige Quelle
  einträgt, eingeschränkt auf `repository_owner == 'NilsHellwig'`
- eine Berechtigung, dass genau das Repo `NilsHellwig/CoMark` den
  `comark-deployer`-Account benutzen darf (`roles/iam.workloadIdentityUser`)

Das steckt in GitHub als Variable `GCP_WIF_PROVIDER`.

### 5.6 Secret Manager — die vier hinterlegten Geheimnisse

| Secret-Name | Inhalt |
|---|---|
| `comark-secret-key` | Zufälliger Schlüssel, mit dem die App z.B. Gäste-Zugangstokens signiert |
| `comark-database-url` | Die Verbindungsadresse zur Neon-Datenbank |
| `comark-google-client-id` | Google-OAuth-Client-ID (für „Continue with Google") |
| `comark-google-client-secret` | das dazugehörige Geheimnis |

Diese vier landen beim Start als Umgebungsvariablen im `backend`-Container —
Cloud Run holt sie aus dem Tresor, ohne dass sie je in einer Datei im Code
oder in GitHub sichtbar sind.

> **Redis-Sonderfall:** Cloud Run kann keine Images direkt von Docker Hub in
> beliebiger Prozessor-Architektur beziehen. Deshalb wird eine Kopie von
> `redis:8-alpine` einmalig (und bei jedem Deploy erneut) in unser eigenes
> Artifact-Registry-Lager kopiert — mit dem richtigen Format für Cloud Run
> (dazu gleich mehr unter „Stolpersteine").

---

## 6. Was bei **jedem** `git push` auf `main` automatisch passiert

Das ist der Job `deploy` in `.github/workflows/ci.yml`, und er startet nur,
wenn die drei Test-Jobs (`backend`, `frontend`, `e2e`) grün waren:

1. **Anmelden bei Google** — über Workload Identity Federation, kein
   Passwort nötig (Abschnitt 5.5).
2. **Drei Docker-Images bauen und hochladen** (`backend`, `frontend`,
   `caddy`) — jedes mit einer eindeutigen Kennung (dem Git-Commit-Hash).
3. **`redis` spiegeln** — Kopie nach Artifact Registry (immer aufs Neue,
   damit sie garantiert zur Cloud-Run-Architektur passt).
4. **Datenbank-Migration** — verbindet sich direkt mit Neon und bringt das
   Datenbank-Schema auf den neuesten Stand (z.B. neue Tabellen/Spalten).
5. **Deploy** — schickt `infra/cloudrun-service.yaml` (mit den frischen
   Image-Namen eingesetzt) an Cloud Run. Google baut daraus eine neue
   „Revision" und schaltet den Traffic um, sobald sie gesund ist
   (Start-Prüfungen bestehen).
6. **Für alle freigeben** — stellt sicher, dass die Seite ohne Login
   erreichbar ist (`roles/run.invoker` für „alle").

Dauer: ca. 3–5 Minuten.

---

## 7. Befehle, die für das Setup einmalig gelaufen sind

Diese Befehle musst du **nicht** wiederholen — sie sind hier dokumentiert,
damit du nachvollziehen kannst, was passiert ist. (Bei einem komplett neuen
Setup stehen sie geordnet in [deploy-gcp.md](deploy-gcp.md).)

```bash
# 1) Rechnungskonto verknüpfen
gcloud billing projects link <PROJEKT-ID> --billing-account=XXXXXX-XXXXXX-XXXXXX

# 2) Alles Automatisierbare auf einmal: APIs, Image-Lager, Redis-Spiegel,
#    Deployer-Konto + Rechte, GitHub-Vertrauensbeziehung, Secrets anlegen
PROJECT_ID=<PROJEKT-ID> REGION=europe-west3 GITHUB_REPO=NilsHellwig/CoMark \
  ./infra/bootstrap.sh

# 3) Der "Bewohner"-Account (der Container selbst) durfte die Secrets noch
#    nicht lesen — das hatte bootstrap.sh nicht mit abgedeckt:
gcloud projects add-iam-policy-binding <PROJEKT-ID> \
  --member="serviceAccount:<PROJEKTNUMMER>-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor

# 4) GitHub mitteilen, welches Projekt/Konto/Provider zu benutzen ist
gh variable set GCP_PROJECT_ID   --body "<PROJEKT-ID>"
gh variable set GCP_REGION       --body "europe-west3"
gh variable set GCP_WIF_PROVIDER --body "projects/<PROJEKTNUMMER>/locations/global/workloadIdentityPools/github/providers/github"
gh variable set GCP_DEPLOYER_SA  --body "comark-deployer@<PROJEKT-ID>.iam.gserviceaccount.com"
gh secret   set NEON_DATABASE_URL --body "<Neon-Connection-String>"

# 5) Nach dem allerersten Deploy: die echte Adresse zurück ins Projekt geben,
#    damit Share-Links und der Google-Login-Rücksprung die richtige URL nutzen
gh variable set PUBLIC_URL --body "https://comark-<hash>.<region>.run.app"
```

Jeder normale Push auf `main` danach braucht **keinen** dieser Befehle mehr —
nur noch `git push`.

---

## 8. Stolpersteine, die unterwegs aufgetreten sind (und warum)

Falls dich diese Fehlermeldungen mal wieder begegnen:

| Fehler | Ursache | Fix |
|---|---|---|
| `Failed to parse … containers[0].dependsOn` | Die Startreihenfolge der vier Container gehört nicht als eigenes Feld an den Container, sondern in eine spezielle Cloud-Run-Annotation. | `run.googleapis.com/container-dependencies: '{"caddy":["backend","frontend"]}'` in `cloudrun-service.yaml` |
| `Invalid value … cpu. Must be … [.08-1] …` | Ein Container hatte `50m` (0,05) CPU zugewiesen — Cloud Run erlaubt minimal `0.08` pro Container. | CPU-Aufteilung neu balanciert, Summe bleibt bei genau 1 vCPU |
| `Permission denied on secret …` | Der **Bewohner**-Account (nicht der Deployer!) durfte die Secrets nicht lesen — den hatte `bootstrap.sh` vergessen. | Siehe Befehl 3 oben |
| `Application exec likely failed` / Container startet nicht | Das gespiegelte `redis`-Image war **arm64** (weil es von einem Apple-Silicon-Mac hochgeladen wurde), Cloud Run läuft aber **amd64**. | Der Deploy-Workflow kopiert `redis` jetzt selbst, auf einem amd64-GitHub-Runner (`docker buildx imagetools create`) |
| `LayoutException` bei lokalen `gcloud secrets …`-Befehlen | Kaputte/doppelte Reste im lokal per Homebrew installierten gcloud-SDK. | `brew reinstall google-cloud-sdk` (betrifft nur lokale Kommandos, nicht das Deployment selbst — das läuft in GitHub Actions mit einem frischen SDK) |

---

## 9. Nachschauen, wenn mal was rot ist

```bash
gh run list --limit 5                 # letzte CI/Deploy-Läufe
gh run view --log-failed              # Log des letzten Fehlschlags
gcloud run services describe comark --region europe-west3   # Status des Diensts
gcloud logging read 'resource.type="cloud_run_revision" resource.labels.service_name="comark"' \
  --project <PROJEKT-ID> --freshness=30m --limit 50        # Live-Logs
```

Oder in der Cloud Console:
- Dienst-Status: <https://console.cloud.google.com/run/detail/europe-west3/comark>
- Logs: <https://console.cloud.google.com/logs/query?project=<PROJEKT-ID>>
- Secrets: <https://console.cloud.google.com/security/secret-manager?project=<PROJEKT-ID>>

---

## 10. Kosten — kurz zusammengefasst

- **Cloud Run**: kostenloses Kontingent deckt ~50 Stunden aktive Zeit/Monat;
  danach ~0,06 €/Stunde. Schaltet sich bei Nichtnutzung komplett ab.
- **Neon**: kostenlose Stufe, reicht für dieses Projekt locker.
- **Artifact Registry**: ein paar Cent Speicherkosten für die Images.
- **Secret Manager**: im kostenlosen Kontingent.

Realistisch: **0–2 € im Monat** bei Hobby-Nutzung.
