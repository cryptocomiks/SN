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

## ✅ Identifiants RÉELS (résolus via les catalogues, 24/07/2026)

Les identifiants tirés de la doc web renvoyaient **404**. Résolus via
`--discover` :

| Source | Supposé (faux) | **Réel** |
|---|---|---|
| ADEME DPE existants | `dpe-v2-logements-existants` | **`meg-83tjwtg8dyz4vv7h1dqe`** |
| RNIC | `...-d-immatriculation-...` | `...-**di**mmatriculation-...` (résolu dynamiquement) |

Catalogue ADEME — jeux voisins à ne pas confondre :

| id | lignes | titre |
|---|---|---|
| **`meg-83tjwtg8dyz4vv7h1dqe`** | **15 280 141** | **DPE Logements existants (depuis juillet 2021)** ← V1 |
| `g3cgx7jb3cmys5voxz1mrm22` | 1 404 131 | DPE Logements neufs (depuis juillet 2021) |
| `dpe-france` | 10 728 950 | DPE Logements (avant juillet 2021) — complément possible, hors V1 |
| `ync2epx48x9azbdnggbygqp0` | 3 114 110 | Audits énergétiques logements existants |

⚠️ Les ids ADEME sont **opaques et générés** (`meg-83tj…`) : ils ne sont pas
devinables et peuvent changer si le jeu est republié. Le script les
re-résout via `--discover` plutôt que de les coder en dur aveuglément.

## Endpoints ciblés (documentés, à vérifier sur pièces)
- **ADEME DPE existants** : `https://data.ademe.fr/data-fair/api/v1/datasets/dpe-v2-logements-existants/lines`
  — pagination curseur (`after`/`next`), 10 000 lignes/page, sans clé, licence ODbL.
- **RNIC** : dataset `registre-national-d-immatriculation-des-coproprietes`
  (ressources listées via l'API data.gouv.fr, pas d'URL de fichier devinée).
- **BAN** : `https://api-adresse.data.gouv.fr/search/` (unitaire) et
  `POST /search/csv/` (masse) pour le géocodage/jointure.

## ✅ Source 3 — BAN : VÉRIFIÉE sur le VPS (24/07/2026)

Sortie réelle de `--only ban`, deux requêtes lyonnaises :

- `properties` contient **17 champs** :
  `label, score, id, banId, name, postcode, citycode, x, y, city, district,
  context, type, importance, depcode, street, _type`
- **`banId`** = UUID stable (ex. `0a51ba1a-42bd-4b8a-9287-c215bedf6574`)
  → **c'est notre clé de jointure** entre DPE et RNIC.
- **`id`** = identifiant hiérarchique (ex. `69382_0805`) — utile en secours.
- **`depcode`** = `"69"` → filtre département natif, exactement ce qu'il nous
  faut pour rester paramétrable.
- `citycode` = code INSEE (`69383` = Lyon 3e), `district` = arrondissement.
- `geometry.coordinates` = `[lon, lat]` en WGS84 (ex. `[4.831662, 45.757597]`) ;
  `x`/`y` sont en Lambert-93 — **ne pas confondre**, PostGIS attend le WGS84.

⚠️ **Point de vigilance pour la jointure** : la requête
`"20 avenue de Saxe 69003 Lyon"` a renvoyé `type: "street"` et non
`housenumber`. Un repli au niveau rue fait perdre la précision au numéro et
risque de fusionner plusieurs immeubles distincts. → À l'étape 2, on
**conserve `type` et `score`**, et on ne joint automatiquement que les
`housenumber` avec un score suffisant ; le reste part en file « ambigus »
pour revue, comme demandé.

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
