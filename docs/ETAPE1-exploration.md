# CoproScan — Étape 1 : Exploration des sources

**Statut : bloqué sur l'accès réseau, en attente de ta décision.**

## Ce qui a été fait
- Sondage des 3 hôtes depuis le sandbox Claude Code (curl + WebFetch).
- Résultat : **403 (refus de politique egress)** sur les trois. Le sandbox
  n'a pas le droit de sortir vers `*.gouv.fr` / `data.ademe.fr`.
- Je refuse d'inventer les schémas → on doit sonder depuis un réseau ouvert.

| Source | Hôte | Accès depuis le sandbox |
|---|---|---|
| DPE ADEME | `data.ademe.fr` | ❌ 403 |
| RNIC (ANAH) | `www.data.gouv.fr` | ❌ 403 |
| BAN | `api-adresse.data.gouv.fr` | ❌ 403 |

## Endpoints ciblés (documentés, à vérifier sur pièces)
- **ADEME DPE existants** : `https://data.ademe.fr/data-fair/api/v1/datasets/dpe-v2-logements-existants/lines`
  — pagination curseur (`after`/`next`), 10 000 lignes/page, sans clé, licence ODbL.
- **RNIC** : dataset `registre-national-d-immatriculation-des-coproprietes`
  (ressources listées via l'API data.gouv.fr, pas d'URL de fichier devinée).
- **BAN** : `https://api-adresse.data.gouv.fr/search/` (unitaire) et
  `POST /search/csv/` (masse) pour le géocodage/jointure.

## Comment débloquer — lance le sondage sur ton VPS
Le script est **read-only**, **stdlib pure** (aucun `pip`), paramétrable par département.

```bash
# sur le VPS, via terminus
git pull
python3 scripts/explore_sources.py            # dept 69 par défaut
# ou une seule source :
python3 scripts/explore_sources.py --only ademe
```

Puis **colle toute la sortie dans le chat**. À partir des schémas réels on calera :
le mapping des colonnes vers le modèle `copropriete`, le champ de filtre
département, le format RNIC, et la stratégie de jointure BAN — avant d'écrire
la moindre ligne d'ingestion (Étape 2).
