# RNIC — schéma réel vérifié (24/07/2026)

Source analysée : `Fichier T3 2025.csv`
`https://static.data.gouv.fr/resources/registre-national-dimmatriculation-des-coproprietes/20260105-104918/fichier-t3-2025.csv`

**Séparateur `,` (virgule, pas `;`) — 72 colonnes — valeurs entre guillemets.**

## 🚨 Écart entre le cahier des charges et la réalité

Le brief annonçait que le RNIC fournirait **type de chauffage** et
**présence d'ascenseur**. **Ces deux colonnes n'existent pas** dans l'export
open data. Vérifié sur les 72 colonnes réelles : aucune n'évoque le
chauffage ni l'ascenseur.

Ces champs figurent bien dans le formulaire de déclaration ANAH, mais ne sont
pas publiés en open data (probablement parce que trop peu renseignés).

**Conséquences directes sur le V1 :**

| Élément du brief | Statut | Solution |
|---|---|---|
| Filtre « type de chauffage » | ❌ absent du RNIC | Doit venir du **DPE ADEME** → dépend du taux de jointure |
| Score « chauffage collectif » | ❌ absent du RNIC | Idem — ne sera calculable que sur les copros jointes au DPE |
| Champ `ascenseur` | ❌ **aucune source identifiée** | À arbitrer : abandonner, ou saisie manuelle dans le CRM |

→ **Décision attendue** (voir plus bas).

## ✅ Ce que le RNIC fournit vraiment, et qui est excellent

### Géolocalisation déjà présente — pas besoin de géocoder cette source
`long` et `lat` sont **déjà dans le fichier** (ex. `4.817259, 45.756287`).
C'est une simplification majeure : la BAN n'est plus nécessaire côté RNIC,
seulement côté DPE (ou pas du tout, selon ce que contient le DPE).

### Filtre département natif
`code_officiel_departement` → périmètre `69` sans géocodage préalable.
Également : `code_officiel_commune`, `nom_officiel_arrondissement_commune`
(les arrondissements lyonnais sortent tout seuls), `code_officiel_epci`.

### Identité et taille
- `numero_d_immatriculation` (ex. `AA0002576`) → clé primaire naturelle
- `nom_d_usage_de_la_copropriete` (ex. « LES JARDINS DE JUSTINE »)
- `nombre_total_de_lots` · `nombre_total_de_lots_a_usage_d_habitation_de_bureaux_ou_de_comm`
  · `nombre_de_lots_a_usage_d_habitation` · `nombre_de_lots_de_stationnement`

⚠️ Exemple réel : total **16**, dont 9 hab/bureaux/commerces, 7 habitation,
0 stationnement. Le critère « 20 à 50 lots » du score **change de sens**
selon la colonne choisie → à trancher.

### Syndic — matière première du CRM, très complète
`raison_sociale_du_representant_legal` (« JOSEPH BAUR IMMOBILIER »),
`siret_du_representant_legal`, `code_ape`,
`type_de_syndic_benevole_professionnel_non_connu` (« professionnel »),
`mandat_en_cours_dans_la_copropriete` (« Mandat en cours »),
`date_de_fin_du_dernier_mandat` (`2026-06-30`).

💡 `date_de_fin_du_dernier_mandat` est un **signal commercial fort** : une
copro dont le mandat expire bientôt est en phase de remise en concurrence.

### Construction
`periode_de_construction` est une **catégorie, pas une année** :
valeur observée `AVANT_19…` (tronquée à l'affichage). Le critère « avant
1975 » du score devra donc travailler sur ces classes, pas sur un entier.
`date_du_reglement_de_copropriete` (ex. `1988-12-08`) donne un repère
supplémentaire mais n'est pas l'année de construction.

### Références cadastrales — piste de jointure sérieuse
`reference_cadastrale_1..3` + `code_insee_commune_1..3` + `prefixe_1..3` +
`section_1..3` + `numero_parcelle_1..3` + `nombre_de_parcelles_cadastrales`.
Une jointure par **parcelle cadastrale** serait bien plus fiable qu'un
rapprochement d'adresses — à confronter au schéma DPE.

### Bonus commercial : zonages d'aides publiques
`copro_dans_acv` (Action Cœur de Ville), `copro_dans_pvd` (Petites Villes de
Demain), `nom_qp_2015` / `nom_qp_2024` (quartiers prioritaires),
`copro_dans_pdp`, `copro_a_idee`.
→ Ces copros sont souvent **éligibles à des subventions** : argument de vente
direct pour tes clients. Non demandé au brief, mais quasi gratuit à intégrer.

### Structure juridique — attention aux doublons
`syndicat_principal_ou_syndicat_secondaire` et
`si_secondaire_n_d_immatriculation_du_principal` : les syndicats secondaires
peuvent désigner le **même ensemble bâti** que leur principal. À dédoublonner
à l'ingestion sous peine de compter deux fois la même cible.

## Ressources disponibles (18) — laquelle ingérer ?

| Ressource | Taille |
|---|---|
| **RNIC – Actualisation quotidienne** | **406 Mo** |
| Fichier T3 2025 (analysé ici) | — |
| Fichier T2 2023 | 312 Mo |
| Fichier T1 2023 | 223 Mo |
| Fichier T4 2022 | 213 Mo |
| Fichier T3 2022 v2 | 182 Mo |
| Fichier T2 2022 | 180 Mo |
| Fiche Descriptive Données Open Data (PDF) | 2 Mo |

→ **Recommandation : « Actualisation quotidienne »** (la plus fraîche). Les
« Fichier Tx » sont des photos trimestrielles historiques.
