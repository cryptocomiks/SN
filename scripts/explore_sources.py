#!/usr/bin/env python3
"""
CoproScan — Étape 1 : sondage READ-ONLY des 3 sources de données.

But : NE RIEN DEVINER. Ce script interroge les vraies API et IMPRIME
le schéma réel + un échantillon de lignes, pour validation humaine
avant d'écrire quoi que ce soit d'ingestion.

- Aucune écriture, aucune base, aucune dépendance pip (stdlib uniquement).
- À lancer là où le réseau peut sortir vers *.gouv.fr (ton VPS via terminus).
- Colle la sortie complète dans le chat pour qu'on cale les schémas ensemble.

Usage :
    python3 explore_sources.py            # département 69 par défaut
    python3 explore_sources.py --dep 75   # paramétrable par code département
"""

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request

TIMEOUT = 60
UA = "CoproScan-explore/0.1 (contact: perfectdude046@gmail.com)"


def http_get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()


def http_get_json(url):
    status, body = http_get(url)
    return status, json.loads(body.decode("utf-8"))


def hr(title):
    print("\n" + "=" * 78)
    print("  " + title)
    print("=" * 78)


def show_keys(obj, label="Champs"):
    if isinstance(obj, dict):
        keys = list(obj.keys())
        print(f"{label} ({len(keys)}): {keys}")


# --------------------------------------------------------------------------
# 1) ADEME — DPE logements existants (data-fair)
# --------------------------------------------------------------------------
ADEME_DATASET = "dpe-v2-logements-existants"
ADEME_BASE = f"https://data.ademe.fr/data-fair/api/v1/datasets/{ADEME_DATASET}"


def explore_ademe(dep):
    hr(f"1. ADEME — DPE logements existants  ({ADEME_DATASET})")
    # 1a. Métadonnées + schéma réel
    try:
        _, meta = http_get_json(ADEME_BASE)
        print("Titre       :", meta.get("title"))
        print("Nb lignes   :", meta.get("count"))
        print("Licence     :", (meta.get("license") or {}).get("title"))
        schema = meta.get("schema", [])
        print(f"\n--- SCHÉMA RÉEL ({len(schema)} colonnes) ---")
        for f in schema:
            print(f"  - {f.get('key'):<45} {f.get('type'):<10} {f.get('label','')}")
    except Exception as e:
        print("ERREUR métadonnées ADEME:", repr(e))

    # 1b. Échantillon de 3 lignes (sans filtre, pour VOIR les vraies valeurs)
    try:
        url = f"{ADEME_BASE}/lines?" + urllib.parse.urlencode({"size": 3})
        _, sample = http_get_json(url)
        rows = sample.get("results", [])
        print(f"\n--- ÉCHANTILLON ({len(rows)} lignes brutes) ---")
        for i, row in enumerate(rows):
            print(f"\n[ligne {i}]")
            print(json.dumps(row, ensure_ascii=False, indent=2)[:2500])
    except Exception as e:
        print("ERREUR échantillon ADEME:", repr(e))

    # 1c. Compter pour le département demandé — on teste plusieurs noms de
    #     champ possibles ; on ne SUPPOSE pas lequel existe, on essaie et on
    #     imprime le résultat de chacun.
    print(f"\n--- SONDAGE FILTRE DÉPARTEMENT {dep} (on cherche le bon champ) ---")
    for field in ["N°_département_(BAN)", "Code_INSEE_(BAN)", "Code_postal_(BAN)"]:
        try:
            # qs = requête Lucene ; on préfixe le code postal par dep pour CP
            if field == "Code_postal_(BAN)":
                q = f'{field}:{dep}*'
            else:
                q = f'{field}:{dep}'
            url = f"{ADEME_BASE}/lines?" + urllib.parse.urlencode(
                {"size": 1, "qs": q}
            )
            _, res = http_get_json(url)
            print(f"  {field:<28} -> total={res.get('total')}")
        except Exception as e:
            print(f"  {field:<28} -> ERREUR {e!r}")


# --------------------------------------------------------------------------
# 2) RNIC — Registre National d'Immatriculation des Copropriétés (ANAH)
# --------------------------------------------------------------------------
RNIC_SLUG = "registre-national-d-immatriculation-des-coproprietes"
DATAGOUV_API = "https://www.data.gouv.fr/api/1/datasets"


def explore_rnic():
    hr("2. RNIC — Registre National d'Immatriculation des Copropriétés (ANAH)")
    # 2a. Lister les ressources RÉELLES (on ne devine pas l'URL du fichier)
    try:
        _, ds = http_get_json(f"{DATAGOUV_API}/{RNIC_SLUG}/")
        print("Titre    :", ds.get("title"))
        print("Éditeur  :", (ds.get("organization") or {}).get("name"))
        resources = ds.get("resources", [])
        print(f"\n--- RESSOURCES DISPONIBLES ({len(resources)}) ---")
        csv_url = None
        for r in resources:
            fmt = (r.get("format") or "").lower()
            print(f"  [{fmt:<5}] {r.get('title','')[:60]}")
            print(f"          {r.get('url')}")
            if csv_url is None and fmt in ("csv", "txt"):
                csv_url = r.get("url")
    except Exception as e:
        print("ERREUR listing RNIC:", repr(e))
        return

    # 2b. Sniffer l'en-tête + 3 lignes du premier CSV (streaming, pas de DL complet)
    if not csv_url:
        print("\nAucune ressource CSV détectée automatiquement — inspecter la liste ci-dessus.")
        return
    print(f"\n--- EN-TÊTE + 3 LIGNES de : {csv_url} ---")
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read(65536)  # premiers 64 Ko suffisent pour l'en-tête
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        header = lines[0] if lines else ""
        sep = ";" if header.count(";") >= header.count(",") else ","
        cols = header.split(sep)
        print(f"Séparateur détecté : '{sep}'   |   {len(cols)} colonnes")
        print("\n--- COLONNES RÉELLES ---")
        for c in cols:
            print("  -", c.strip())
        print("\n--- 3 PREMIÈRES LIGNES DE DONNÉES ---")
        for ln in lines[1:4]:
            print(" ", ln[:300])
    except Exception as e:
        print("ERREUR lecture CSV RNIC:", repr(e))


# --------------------------------------------------------------------------
# 3) BAN — Base Adresse Nationale (géocodage, clé de jointure)
# --------------------------------------------------------------------------
BAN_BASE = "https://api-adresse.data.gouv.fr"


def explore_ban():
    hr("3. BAN — Base Adresse Nationale (géocodage)")
    tests = [
        "20 avenue de Saxe 69003 Lyon",
        "place Bellecour Lyon",
    ]
    for q in tests:
        try:
            url = f"{BAN_BASE}/search/?" + urllib.parse.urlencode(
                {"q": q, "limit": 1}
            )
            _, res = http_get_json(url)
            feats = res.get("features", [])
            print(f"\nRequête: {q!r}  -> {len(feats)} résultat(s)")
            if feats:
                f0 = feats[0]
                print("  geometry :", json.dumps(f0.get("geometry"), ensure_ascii=False))
                props = f0.get("properties", {})
                show_keys(props, "  properties")
                print("  valeurs  :", json.dumps(props, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"  ERREUR BAN pour {q!r}:", repr(e))
    print("\nNote: le géocodage en masse se fait via POST /search/csv/ "
          "(multipart, jusqu'à ~50k lignes/fichier) — à câbler à l'étape 2.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dep", default="69", help="code département (défaut 69)")
    ap.add_argument("--only", choices=["ademe", "rnic", "ban"], help="une seule source")
    args = ap.parse_args()

    print(f"CoproScan — sondage des sources | département = {args.dep}")
    if args.only in (None, "ademe"):
        explore_ademe(args.dep)
    if args.only in (None, "rnic"):
        explore_rnic()
    if args.only in (None, "ban"):
        explore_ban()
    print("\n" + "=" * 78)
    print("  FIN. Copie toute cette sortie dans le chat pour validation.")
    print("=" * 78)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
