# 🛡️ Système intelligent d’anonymisation et de classification des données selon le profil utilisateur et le risque RGPD

## 📌 Présentation

Ce projet consiste à développer un système intelligent permettant de **classifier les données selon leur niveau de risque** et d'appliquer automatiquement une **anonymisation adaptée au profil de l'utilisateur et au contexte d'utilisation**.

L'objectif est de protéger les données personnelles tout en **préservant leur utilité pour les besoins métiers, analytiques et statistiques**.

Contrairement à une approche dans laquelle toutes les données seraient anonymisées de la même manière, le système adopte une approche dynamique :

> **Niveau de risque de la donnée + Profil utilisateur + Type de donnée → Niveau d'anonymisation adapté**

Le système repose sur trois composants principaux :

* 🤖 **Classification intelligente des données avec LLM + RAG**
* 🔐 **Proxy d'anonymisation dynamique selon le profil et le niveau de risque**
* 📊 **Dashboard d'administration et de supervision**

---

# 🏗️ Architecture générale

```text
                         ┌──────────────────────────┐
                         │      Base Oracle         │
                         │                          │
                         │ Tables / Colonnes / Data │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │ Classification intelligente     │
                    │                                 │
                    │          LLM + RAG              │
                    │                                 │
                    │ • Métadonnées                   │
                    │ • Échantillons                  │
                    │ • Contexte RGPD                 │
                    │ • Questions d'analyse            │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │ Niveau de risque   │
                         │                    │
                         │ Faible             │
                         │ Moyen              │
                         │ Élevé              │
                         │ Critique           │
                         └──────────┬─────────┘
                                    │
                                    ▼
                  ┌──────────────────────────────────┐
                  │      Proxy d'anonymisation       │
                  │                                  │
                  │ Profil utilisateur                │
                  │ + Niveau de risque                │
                  │ + Type de donnée                  │
                  │ + Règles d'anonymisation         │
                  └────────────────┬─────────────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Données protégées  │
                         │                    │
                         │ Utiles pour        │
                         │ l'analyse          │
                         └────────────────────┘

                                   ▲
                                   │
                    ┌──────────────┴─────────────┐
                    │   Dashboard Administrateur │
                    │                            │
                    │ • Classification           │
                    │ • Correction               │
                    │ • Scan                     │
                    │ • Cache                    │
                    │ • Profils                  │
                    │ • Règles d'accès           │
                    └────────────────────────────┘
```

---

# 🤖 1. Classification intelligente des données — LLM + RAG

La première étape consiste à **identifier et évaluer le niveau de risque des données présentes dans la base de données**.

Le système analyse les colonnes à partir de plusieurs informations :

* Nom de la base de données
* Nom de la table
* Nom de la colonne
* Type de donnée
* Échantillons de valeurs
* Contexte associé à la donnée
* Informations réglementaires récupérées par le RAG
* Réponses à plusieurs questions d'analyse

Ces informations sont transmises à un **LLM** afin de déterminer le niveau de risque associé à chaque colonne.

## 🧠 LLM + RAG

Le LLM ne se base donc pas uniquement sur le nom de la colonne.

Le système utilise une architecture **RAG (Retrieval-Augmented Generation)** permettant de récupérer des informations pertinentes provenant de la documentation réglementaire utilisée par le projet.

Le contexte récupéré est ensuite intégré à l'analyse du LLM afin de fournir une classification plus contextualisée.

Le système utilise également un mécanisme de **questions/réponses** afin d'affiner l'évaluation du risque.

```text
Métadonnées
     │
     ├── Base
     ├── Table
     ├── Colonne
     ├── Type
     └── Échantillons
              │
              ▼
        ┌────────────┐
        │    RAG     │
        │            │
        │ Contexte   │
        │ réglementaire
        └─────┬──────┘
              │
              ▼
        ┌────────────┐
        │    LLM     │
        │            │
        │ Analyse +  │
        │ Questions  │
        └─────┬──────┘
              │
              ▼
      Niveau de risque
```

## 🎯 Niveaux de risque

Les données sont réparties en quatre niveaux :

| Niveau          | Description                                            |
| --------------- | ------------------------------------------------------ |
| 🟢 **Faible**   | Données présentant un faible niveau de risque          |
| 🟡 **Moyen**    | Données nécessitant une protection intermédiaire       |
| 🟠 **Élevé**    | Données présentant un risque important                 |
| 🔴 **Critique** | Données nécessitant un niveau de protection très élevé |

La classification produite par le LLM n'est pas considérée comme définitive.

L'administrateur peut **vérifier, corriger ou remplacer manuellement une classification** depuis le dashboard.

Cette approche permet de combiner :

**Automatisation du LLM + contrôle humain**

---

# 🔐 2. Anonymisation selon le profil, le risque et le type de donnée

Une fois le niveau de risque déterminé, le système utilise cette information pour décider **du niveau d'anonymisation à appliquer**.

L'anonymisation n'est donc pas identique pour tous les utilisateurs.

Le système prend en compte :

* 👤 le **profil utilisateur** ;
* 🔴 le **niveau de risque de la donnée** ;
* 🧩 le **type de donnée** ;
* 🔐 le **niveau d'anonymisation défini pour le profil** ;
* 📊 les besoins d'utilisation de la donnée.

L'objectif est de déterminer le niveau de protection permettant à l'utilisateur d'exploiter les données **sans exposer inutilement les informations sensibles**.

## 🔄 Fonctionnement

```text
                 Donnée demandée
                        │
                        ▼
               Niveau de risque
                        │
                        ▼
                Profil utilisateur
                        │
                        ▼
             Règles d'anonymisation
                        │
                        ▼
              Niveau de protection
                        │
                        ▼
             Technique appropriée
                        │
                        ▼
                Donnée protégée
                        │
                        ▼
                    Utilisateur
```

### Exemple

Une même donnée peut être traitée différemment selon le profil :

```text
                 Donnée sensible
                       │
                       ▼
                Niveau de risque
                       │
              ┌────────┴────────┐
              │                 │
          Profil A           Profil B
              │                 │
       Protection faible   Protection forte
              │                 │
              ▼                 ▼
       Plus d'utilité      Plus de protection
```

Le système cherche ainsi à maintenir un **équilibre entre protection et utilité**.

---

# 🔒 3. Proxy d'anonymisation dynamique

Le **proxy d'anonymisation** constitue la couche intermédiaire entre l'utilisateur et la base de données.

L'utilisateur n'accède pas directement aux données originales.

Lorsqu'une requête est exécutée, le proxy intercepte les données et applique les règles correspondantes.

```text
Utilisateur
     │
     │ Requête
     ▼
┌──────────────────────┐
│ Proxy d'anonymisation│
└──────────┬───────────┘
           │
           ├── Profil utilisateur
           │
           ├── Niveau de risque
           │
           ├── Type de donnée
           │
           └── Règle d'anonymisation
                    │
                    ▼
          Technique appropriée
                    │
                    ▼
             Donnée protégée
                    │
                    ▼
                Utilisateur
```

Cette architecture permet de centraliser les règles de protection et d'éviter que chaque application cliente doive implémenter elle-même les mécanismes d'anonymisation.

---

# 🧩 Techniques d'anonymisation

Selon le type de donnée et le niveau de protection requis, différentes techniques peuvent être utilisées :

* 🔑 **Tokenisation**
* 🎭 **Masquage**
* 🔐 **Format-Preserving Encryption (FPE)**
* 📊 **Ajout de bruit statistique**
* 📅 **Transformation ou réduction de précision des dates**
* 🔢 **Techniques adaptées aux données numériques**

### 📅 Exemple : transformation d'une date

Une date exacte peut être transformée afin de réduire sa précision :

```text
2026-09-16
     │
     ▼
2026
```

ou :

```text
2026-09-16
     │
     ▼
2026-Q3
```

### 📊 Exemple : données numériques

Pour certaines analyses statistiques, un mécanisme de bruit peut être appliqué :

```text
Valeur originale
       │
       ▼
Transformation
       │
       ▼
Valeur protégée
```

L'objectif est de protéger la valeur individuelle tout en conservant, lorsque cela est possible, certaines propriétés statistiques utiles à l'analyse.

---

# 📊 4. Dashboard Administrateur

Le système dispose d'un **dashboard d'administration** permettant de superviser les différentes étapes du processus.

L'administrateur peut notamment :

* consulter les classifications produites par le LLM ;
* vérifier les niveaux de risque ;
* corriger manuellement une classification ;
* lancer un nouveau scan de la base ;
* consulter et gérer le cache ;
* gérer les profils utilisateurs ;
* définir les niveaux d'anonymisation associés aux profils ;
* superviser les règles d'accès aux données.

## 🖥️ Aperçu

> 📸 **Ajouter ici une capture d'écran du dashboard**

```text
┌──────────────────────────────────────────────┐
│              ADMIN DASHBOARD                 │
├──────────────────────────────────────────────┤
│                                              │
│  Classification       Profils utilisateurs  │
│  ─────────────        ────────────────────  │
│                                              │
│  Tables analysées      Règles d'accès        │
│  Colonnes classées     Niveaux d'anonymisation│
│                                              │
│  Cache                 Scan de la base       │
│                                              │
└──────────────────────────────────────────────┘
```

---

# ⚡ 5. Gestion du cache

La classification d'une base contenant un grand nombre de tables et de colonnes peut nécessiter de nombreuses analyses par le LLM.

Un système de **cache de classification** est donc utilisé.

Lorsqu'une colonne a déjà été analysée, son résultat peut être réutilisé plutôt que de lancer une nouvelle analyse.

Cela permet notamment de :

* réduire le nombre d'appels au LLM ;
* améliorer les performances ;
* réduire les traitements inutiles ;
* conserver une classification stable ;
* éviter de recalculer inutilement les mêmes résultats.

Une nouvelle analyse peut être déclenchée lorsque cela est nécessaire, notamment après une modification ou un nouveau scan.

---

# 👥 6. Gestion des profils utilisateurs

Le système permet de définir différents profils utilisateurs et de leur associer des règles d'accès et des niveaux d'anonymisation.

Le principe est le suivant :

```text
                  Profil utilisateur
                         │
                         ▼
                Règles d'accès
                         │
                         ▼
                 Niveau de risque
                         │
                         ▼
            Niveau d'anonymisation
                         │
                         ▼
              Technique appliquée
```

Ainsi, une même donnée peut être retournée sous différentes formes selon le profil qui effectue la requête.

Cette approche permet d'adapter la protection au **contexte d'utilisation**, tout en conservant autant que possible l'utilité nécessaire aux traitements autorisés.

---

# 🛡️ 7. Contrôle humain et sécurité

Le système ne considère pas le LLM comme l'autorité finale.

Le LLM fournit une **proposition de classification**, qui peut ensuite être contrôlée par l'administrateur.

Le processus est donc :

```text
LLM
 │
 │ Proposition
 ▼
Administrateur
 │
 ├── Valider
 ├── Modifier
 └── Relancer l'analyse
```

Cette séparation permet de conserver un **contrôle humain sur les décisions de classification** et de limiter les conséquences d'une classification incorrecte.

---

# 🎯 Objectifs

Le projet vise principalement à :

* 🔒 protéger les données personnelles et sensibles ;
* 🤖 automatiser la classification grâce à un **LLM + RAG** ;
* 👤 adapter l'anonymisation au profil utilisateur ;
* 🔴 adapter le niveau de protection au risque associé aux données ;
* 📊 préserver autant que possible l'utilité des données ;
* ⚡ réduire les traitements inutiles grâce au cache ;
* 👨‍💻 permettre à l'administrateur de contrôler et corriger les classifications ;
* 🔄 appliquer dynamiquement différentes techniques d'anonymisation ;
* 🛡️ intégrer la protection des données directement dans le processus d'accès.

---

# 🛠️ Technologies utilisées

| Technologie                    | Utilisation                                |
| ------------------------------ | ------------------------------------------ |
| **Python**                     | Logique principale du système              |
| **LLM**                        | Classification des données                 |
| **RAG**                        | Recherche de contexte réglementaire        |
| **Oracle Database**            | Stockage des données                       |
| **PL/SQL**                     | Interaction avec la base                   |
| **React**                      | Interface d'administration                 |
| **API**                        | Communication entre les composants         |
| **Proxy**                      | Interception et transformation des données |
| **Techniques d'anonymisation** | Protection des données                     |

---

# 🔄 Vue globale du fonctionnement

```text
                    BASE ORACLE
                        │
                        ▼
              ┌──────────────────┐
              │ Analyse des      │
              │ métadonnées      │
              └────────┬─────────┘
                       │
                       ▼
                 ┌───────────┐
                 │ LLM + RAG │
                 └─────┬─────┘
                       │
                       ▼
               CLASSIFICATION
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Faible        Moyen        Élevé/Critique
          │            │            │
          └────────────┼────────────┘
                       ▼
              PROFIL UTILISATEUR
                       │
                       ▼
          NIVEAU D'ANONYMISATION
                       │
                       ▼
              PROXY DYNAMIQUE
                       │
                       ▼
          TECHNIQUE D'ANONYMISATION
                       │
                       ▼
             DONNÉES PROTÉGÉES
                       │
                       ▼
                  UTILISATEUR
```

---

# 🚀 Vision du projet

Le projet propose une approche **dynamique et contextuelle de la protection des données**.

Plutôt que d'appliquer une anonymisation identique à l'ensemble des données, le système adapte le traitement en fonction de plusieurs paramètres :

```text
       Niveau de risque
              +
      Profil utilisateur
              +
        Type de donnée
              +
      Contexte d'utilisation
              │
              ▼
    Niveau d'anonymisation adapté
```

L'objectif est de rechercher un équilibre entre :

**🔒 Protection des données**
**📋 Respect des principes du RGPD**
**📊 Utilité des données**

tout en maintenant un **contrôle humain sur les classifications et les règles de protection**.

---

## 📌 Points clés du projet

* 🤖 Classification automatisée avec **LLM + RAG**
* 🔐 Proxy d'anonymisation dynamique
* 👥 Gestion des profils utilisateurs
* 🔴 Classification en quatre niveaux de risque
* 🧩 Anonymisation adaptée au type de donnée
* 📊 Préservation de l'utilité analytique
* ⚡ Système de cache
* 👨‍💻 Validation et correction par l'administrateur
* 🗄️ Intégration avec **Oracle Database**
* 🖥️ Dashboard d'administration
