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
# Id RÉEL confirmé via le catalogue data-fair le 24/07/2026 :
# "DPE Logements existants (depuis juillet 2021)" — 15 280 141 lignes.
# (L'id de la doc web, "dpe-v2-logements-existants", renvoie 404.)
ADEME_DATASET = "meg-83tjwtg8dyz4vv7h1dqe"
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
# Résolu dynamiquement via le catalogue (le slug exact n'est pas devinable :
# c'est "...-dimmatriculation-..." et non "...-d-immatriculation-...").
RNIC_SLUG = "registre-national-d-immatriculation-des-coproprietes"
RNIC_SLUG_EXPLICIT = None
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


# --------------------------------------------------------------------------
# Mode COMPACT — sortie dense, lisible en 1 ou 2 captures d'écran.
# Aucune supposition : on lit le schéma réel, puis on choisit les champs
# à profiler par correspondance de motifs sur les clés RÉELLES.
# --------------------------------------------------------------------------
INTERESTING = [
    "chauffage", "dpe", "ges", "construction", "latitude", "longitude",
    "surface", "adresse", "postal", "commune", "ban", "departement",
    "département", "type_batiment", "type_bâtiment", "logement",
]


def pick_fields(keys, patterns):
    out = []
    for k in keys:
        kl = k.lower()
        if any(p in kl for p in patterns):
            out.append(k)
    return out


def compact_ademe(dep):
    hr(f"1. ADEME (compact) — dep {dep}")
    try:
        _, meta = http_get_json(ADEME_BASE)
    except Exception as e:
        print("ERREUR meta:", repr(e))
        return
    schema = meta.get("schema", [])
    keys = [f.get("key") for f in schema if f.get("key")]
    print(f"count_total={meta.get('count')}  nb_colonnes={len(keys)}")
    print("\n--- CLÉS RÉELLES ---")
    print(" | ".join(keys))

    # Trouver le champ département RÉEL (on teste, on ne devine pas)
    dep_fields = pick_fields(keys, ["departement", "département"])
    print(f"\n--- CHAMPS 'département' TROUVÉS: {dep_fields} ---")
    working = None
    for f in dep_fields:
        for mode, params in (
            ("param", {"size": 1, f: dep}),
            ("qs", {"size": 1, "qs": f"{f}:{dep}"}),
        ):
            try:
                url = f"{ADEME_BASE}/lines?" + urllib.parse.urlencode(params)
                _, r = http_get_json(url)
                tot = r.get("total")
                print(f"  [{mode}] {f} -> total={tot}")
                if tot and working is None:
                    working = (f, mode)
            except Exception as e:
                print(f"  [{mode}] {f} -> ERR {type(e).__name__}")
    print("FILTRE RETENU:", working)

    # Profil des valeurs sur un échantillon réel du département
    if not working:
        print("Aucun filtre département fonctionnel — voir ci-dessus.")
        return
    f, mode = working
    params = {"size": 200} | ({f: dep} if mode == "param" else {"qs": f'"{f}":{dep}'})
    try:
        url = f"{ADEME_BASE}/lines?" + urllib.parse.urlencode(params)
        _, r = http_get_json(url)
        rows = r.get("results", [])
    except Exception as e:
        print("ERREUR échantillon:", repr(e))
        return
    print(f"\n--- PROFIL SUR {len(rows)} LIGNES RÉELLES (dep {dep}) ---")
    for k in pick_fields(keys, INTERESTING):
        vals = [row.get(k) for row in rows if row.get(k) not in (None, "")]
        if not vals:
            continue
        uniq = {}
        for v in vals:
            uniq[str(v)[:38]] = uniq.get(str(v)[:38], 0) + 1
        top = sorted(uniq.items(), key=lambda x: -x[1])[:6]
        rendu = ", ".join(f"{v}({n})" for v, n in top)
        print(f"  {k[:44]:<44} n={len(vals):<4} {rendu[:110]}")


def resolve_rnic(explicit=None):
    """Retourne le dataset RNIC. Si aucun slug explicite ne marche, on le
    RÉSOUT via le catalogue plutôt que de le deviner."""
    if explicit:
        try:
            _, ds = http_get_json(f"{DATAGOUV_API}/{explicit}/")
            print(f"slug explicite OK: {explicit}")
            return ds
        except Exception as e:
            print(f"slug explicite {explicit!r} -> {e!r} ; on interroge le catalogue")
    url = "https://www.data.gouv.fr/api/1/datasets/?" + urllib.parse.urlencode(
        {"q": "registre national immatriculation copropriétés", "page_size": 5}
    )
    _, res = http_get_json(url)
    for d in res.get("data", []):
        org = (d.get("organization") or {}).get("name", "")
        print(f"candidat: slug={d.get('slug')}  org={org}")
        if "anah" in org.lower() or "habitat" in org.lower() or "agence nationale" in org.lower():
            print(f"-> RETENU (éditeur ANAH): {d.get('slug')}")
            return d
    data = res.get("data", [])
    if data:
        print(f"-> RETENU (1er résultat): {data[0].get('slug')}")
        return data[0]
    raise RuntimeError("aucun jeu RNIC trouvé dans le catalogue")


def compact_rnic():
    hr("2. RNIC (compact)")
    try:
        ds = resolve_rnic(RNIC_SLUG_EXPLICIT)
    except Exception as e:
        print("ERREUR:", repr(e))
        return
    resources = ds.get("resources", [])
    print(f"\n{ds.get('title')}")
    print(f"slug COMPLET: {ds.get('slug')}")
    print(f"{len(resources)} ressources:")
    csv_url = None
    for r in resources:
        fmt = (r.get("format") or "").lower()
        size = r.get("filesize")
        mb = f"{size/1e6:.0f}Mo" if isinstance(size, int) else "?"
        print(f"  [{fmt:<5}] {mb:>7}  {(r.get('title') or '')[:64]}")
        if csv_url is None and fmt in ("csv", "txt"):
            csv_url = r.get("url")
            csv_title = (r.get("title") or "")[:64]
    if not csv_url:
        print("Aucune ressource CSV — voir la liste ci-dessus.")
        return
    print(f"\n>>> CSV analysé: {csv_title}\n    {csv_url}")
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read(65536)
        lines = raw.decode("utf-8", errors="replace").splitlines()
        header = lines[0] if lines else ""
        sep = ";" if header.count(";") >= header.count(",") else ","
        cols = [c.strip() for c in header.split(sep)]
        print(f"\nsep='{sep}'  nb_colonnes={len(cols)}")
        print("--- COLONNES RÉELLES ---")
        print(" | ".join(cols))
        print("\n--- 2 LIGNES ---")
        for ln in lines[1:3]:
            print(" ", ln[:400])
    except Exception as e:
        print("ERREUR CSV:", repr(e))


# --------------------------------------------------------------------------
# Mode DÉCOUVERTE — on interroge les CATALOGUES pour lire les vrais
# identifiants de jeux de données. Aucun slug deviné : c'est la plateforme
# qui nous les donne.
# --------------------------------------------------------------------------
def discover():
    hr("DÉCOUVERTE — catalogue ADEME (data-fair)")
    for q in ["dpe logements existants", "dpe existant", "dpe"]:
        url = "https://data.ademe.fr/data-fair/api/v1/datasets?" + urllib.parse.urlencode(
            {"q": q, "size": 15}
        )
        try:
            _, res = http_get_json(url)
        except Exception as e:
            print(f"  q={q!r} -> ERREUR {e!r}")
            continue
        rows = res.get("results", res.get("data", []))
        print(f"\n  q={q!r} -> {res.get('count', len(rows))} jeux")
        for d in rows:
            did = d.get("id") or d.get("slug")
            cnt = d.get("count")
            print(f"    {str(did):<26} count={str(cnt):<10} {str(d.get('title'))[:52]}")
        if rows:
            break

    hr("DÉCOUVERTE — catalogue data.gouv.fr (RNIC / copropriétés)")
    for q in [
        "registre national immatriculation copropriétés",
        "immatriculation copropriétés",
        "copropriétés",
    ]:
        url = "https://www.data.gouv.fr/api/1/datasets/?" + urllib.parse.urlencode(
            {"q": q, "page_size": 12}
        )
        try:
            _, res = http_get_json(url)
        except Exception as e:
            print(f"  q={q!r} -> ERREUR {e!r}")
            continue
        rows = res.get("data", [])
        print(f"\n  q={q!r} -> {res.get('total')} jeux")
        for d in rows:
            org = (d.get("organization") or {}).get("name", "")
            nres = len(d.get("resources", []))
            print(f"    slug={d.get('slug')}\n         res={nres:<3} org={str(org)[:30]:<30} {str(d.get('title'))[:40]}")
        if rows:
            break
    print("\n>>> Relance ensuite avec les VRAIS ids, ex.:")
    print("    python3 scripts/explore_sources.py --compact --only ademe --dataset <ID>")
    print("    python3 scripts/explore_sources.py --compact --only rnic  --rnic-slug <SLUG>")


def main():
    global ADEME_DATASET, ADEME_BASE, RNIC_SLUG, RNIC_SLUG_EXPLICIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--dep", default="69", help="code département (défaut 69)")
    ap.add_argument("--discover", action="store_true", help="lister les vrais ids via les catalogues")
    ap.add_argument("--dataset", help="id du jeu ADEME (override)")
    ap.add_argument("--rnic-slug", dest="rnic_slug", help="slug data.gouv.fr du RNIC (override)")
    ap.add_argument("--only", choices=["ademe", "rnic", "ban"], help="une seule source")
    ap.add_argument("--compact", action="store_true", help="sortie dense")
    args = ap.parse_args()

    if args.dataset:
        ADEME_DATASET = args.dataset
        ADEME_BASE = f"https://data.ademe.fr/data-fair/api/v1/datasets/{ADEME_DATASET}"
    if args.rnic_slug:
        RNIC_SLUG = args.rnic_slug
        RNIC_SLUG_EXPLICIT = args.rnic_slug

    print(f"CoproScan — sondage des sources | département = {args.dep}")
    if args.discover:
        discover()
        return
    if args.compact:
        if args.only in (None, "ademe"):
            compact_ademe(args.dep)
        if args.only in (None, "rnic"):
            compact_rnic()
        print("\n=== FIN (compact) ===")
        return
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
