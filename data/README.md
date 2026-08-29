# Description des données

Ce dossier contient les données du cas pratique. Deux ensembles :

- **Parc & télémétrie de sécurité de l'entreprise** — le **référentiel des assets** de l'entreprise (~20 assets) et la **télémétrie de sécurité** observée sur ces assets via **deux sources hétérogènes** (SIEM, EDR). Les événements sont horodatés sur une fenêtre de quelques mois.
- **Incidents cyber (externe)** — une base d'incidents observés sur un ensemble d'**autres organisations**, construite sur ~4 ans, avec leur impact financier.

Chaque source a son **schéma propre** ; les conventions (nommage, formats, échelles) peuvent différer d'un fichier à l'autre.

---

## Parc & télémétrie de sécurité de l'entreprise

### `asset_reference.csv`
Référentiel des **assets** de l'entreprise.

| Variable | Description |
|---|---|
| `asset_id` | Identifiant de l'asset |
| `asset_type` | Type d'asset (`server`, `workstation`, `database`, `web_app`) |
| `business_criticality` | Criticité métier, de 1 (faible) à 5 (critique) |
| `environment` | Environnement d'exécution : `prod`, `staging` ou `dev` |

### `feed_siem.csv`
Export d'un **SIEM** — événements de sécurité détectés sur les assets de l'entreprise.

| Variable | Description |
|---|---|
| `event_id` | Identifiant de l'événement |
| `asset_id` | Asset concerné (référence vers `asset_reference.csv`) |
| `mitre_technique` | Technique MITRE ATT&CK |
| `severity` | Sévérité, en classe textuelle |
| `detected_at` | Horodatage de détection |
| `source` | Source de l'événement |

### `feed_edr.csv`
Export d'un **EDR** — événements de sécurité détectés sur les assets de l'entreprise.

| Variable | Description |
|---|---|
| `id` | Identifiant de l'événement |
| `host` | Asset concerné |
| `ttp` | Technique MITRE ATT&CK |
| `risk` | Niveau de sévérité, sur une échelle numérique |
| `timestamp` | Horodatage de l'événement |

---

## Incidents cyber (externe)

### `cyber_incidents.csv`
Base d'**incidents cyber** observés sur un ensemble d'**autres organisations**, sur ~4 ans (~1 600 lignes).

| Variable | Description |
|---|---|
| `incident_id` | Identifiant de l'incident |
| `company_id` | Identifiant de l'organisation touchée (une organisation peut apparaître plusieurs fois) |
| `date` | Date de l'incident |
| `sector` | Secteur d'activité de l'organisation touchée |
| `company_size` | Catégorie de taille (`PME`, `ETI`, `GE`) |
| `employees` | Effectif de l'organisation |
| `attack_type` | Type d'attaque |
| `severity` | Sévérité (échelle propre à cette source) |
| `security_maturity_score` | Score de maturité sécurité (0–100) |
| `records_exposed` | Nombre d'enregistrements exposés |
| `downtime_hours` | Durée d'indisponibilité, en heures |
| `financial_loss_eur` | Perte financière, en euros |
