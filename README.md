Système intelligent d’anonymisation et de classification des données RGPD
# Système de gestion et d’anonymisation des données RGPD

## 📌 Présentation

Ce projet consiste en la conception d’un système permettant de **classifier les données selon leur niveau de risque** et d’appliquer une **anonymisation adaptée au profil de l’utilisateur et à la sensibilité des données**.

L’application a été développée dans un contexte de gestion de données Oracle à grande échelle. L’architecture de la base étudiée comporte plus de **7 000 tables**, ce qui nécessite des mécanismes automatisés de classification et de protection des données.

Cette partie du projet se concentre principalement sur :

* le **backend Python** ;
* les **API REST** ;
* la connexion à Oracle ;
* la classification des colonnes ;
* le mécanisme RAG + LLM ;
* l’application des règles d’anonymisation ;
* le contrôle d’accès ;
* l’**interface d’administration** permettant de modifier les paramètres du système.

---

# 🏗️ Architecture backend

L’application repose sur une architecture séparant le frontend, le backend et la base de données.

```text
                    ┌──────────────────────────┐
                    │    Interface Admin       │
                    │      React / CSS         │
                    └────────────┬─────────────┘
                                 │
                                 │ API REST / JSON
                                 ▼
                    ┌──────────────────────────┐
                    │       Backend Python     │
                    │          Flask           │
                    ├──────────────────────────┤
                    │ Authentification         │
                    │ Contrôle des rôles       │
                    │ Classification RGPD       │
                    │ Anonymisation             │
                    │ Gestion du cache          │
                    │ Simulation                │
                    └───────┬───────────┬──────┘
                            │           │
                    ┌───────▼───┐   ┌──▼─────────────┐
                    │  Oracle   │   │ RAG + Mistral  │
                    │  Database │   │ FAISS / Ollama │
                    └───────────┘   └────────────────┘
```

Le rapport indique que **Python est utilisé pour le backend et la création des API**, React/CSS pour le frontend et PL/SQL pour la gestion de la base de données.

---

# 🐍 Backend Python

Le backend constitue le cœur fonctionnel de l’application.

Il assure notamment :

* l’authentification des utilisateurs ;
* le contrôle des permissions ;
* la communication avec Oracle ;
* le lancement des scans ;
* la classification des colonnes ;
* la récupération du contexte documentaire ;
* l’appel au modèle Mistral ;
* la gestion des résultats de classification ;
* l’application des degrés d’anonymisation ;
* la simulation de l’anonymisation ;
* la gestion du cache.

Le backend expose ces fonctionnalités sous forme d’**API**, permettant à l’interface React de communiquer avec le serveur.

---

# 🔐 Authentification et contrôle d'accès

Avant d'accéder aux fonctionnalités de l'application, l'utilisateur doit s'authentifier.

Le backend vérifie les identifiants puis détermine le profil de l'utilisateur.

```text
Utilisateur
     │
     ▼
Login
     │
     ▼
Backend Python
     │
     ├── Identifiants invalides → Erreur
     │
     └── Identifiants valides
                  │
                  ▼
             Profil utilisateur
                  │
          ┌───────┴────────┐
          ▼                ▼
      Espace Admin     Espace métier
```

Le système redirige ensuite l'utilisateur vers l'espace correspondant à son profil.

Le contrôle des rôles empêche également un utilisateur d'accéder aux fonctionnalités réservées à un autre profil. Les tests du projet ont notamment vérifié le refus d'accès à l'espace administrateur et l'isolation entre les rôles.

---

# 👨‍💼 Interface d'administration

L’interface administrateur constitue le principal espace de **configuration et de pilotage du système**.

L'administrateur peut agir sur plusieurs paramètres sans devoir modifier directement le code Python.

Les fonctionnalités principales sont :

### 1. 🔎 Lancer un scan de classification

L'administrateur peut lancer un scan de la base afin d'analyser les colonnes et déterminer leur niveau de risque.

```text
Base Oracle
     │
     ▼
Scan
     │
     ▼
Analyse des tables / colonnes
     │
     ▼
Classification
     │
     ├── CRITIQUE
     ├── ÉLEVÉ
     ├── MODÉRÉ
     └── FAIBLE
```

Le lancement du scan fait partie des fonctionnalités prévues pour l'administrateur.

---

# 🏷️ 2. Modifier le niveau de classification

L'administrateur peut modifier le niveau de sensibilité attribué à une donnée classifiée.

Par exemple :

```text
COLONNE              NIVEAU
--------------------------------
NUM_CLIENT           CRITIQUE
EMAIL                ÉLEVÉ
VILLE                MODÉRÉ
CODE_POSTAL          FAIBLE
```

L'interface permet donc de corriger ou d'ajuster une classification lorsque cela est nécessaire.

Cette possibilité est explicitement prévue dans le backlog du projet : l'administrateur peut **modifier les niveaux de sensibilité des données classifiées**.

---

# 🧹 3. Vider le cache de classification

Le backend utilise un mécanisme de cache pour conserver certains résultats de classification.

L'administrateur dispose d'une fonctionnalité permettant de supprimer ces résultats afin de forcer un nouveau calcul.

```text
Classification existante
          │
          ▼
        CACHE
          │
          │ "Vider le cache"
          ▼
      Cache supprimé
          │
          ▼
Nouvelle classification
```

Cette fonctionnalité permet notamment de recalculer la classification d'une colonne lorsque ses paramètres ou les règles utilisées ont changé.

---

# 🛡️ 4. Modifier le degré d'anonymisation

L'administrateur peut également modifier le **degré d'anonymisation appliqué à une colonne**.

L'interface permet donc de sélectionner le niveau de protection souhaité.

```text
Colonne
   │
   ▼
Niveau de risque
   │
   ▼
Profil utilisateur
   │
   ▼
Degré d'anonymisation
   │
   ├── D0
   ├── D1
   ├── D2
   └── D3
```

Le degré appliqué dépend ainsi des règles définies dans le système, du profil de l'utilisateur et du niveau de risque de la donnée.

---

# 🧪 5. Simulation de l'anonymisation

Avant d'appliquer réellement une transformation, l'administrateur peut utiliser la fonctionnalité de simulation.

```text
Donnée originale
       │
       ▼
Configuration du degré
       │
       ▼
     Simulation
       │
       ▼
Donnée transformée
```

Cette fonctionnalité permet de visualiser le résultat attendu de l'anonymisation et de vérifier que le niveau de protection choisi correspond au besoin.

La simulation de l'anonymisation fait partie des fonctionnalités administrateur définies dans le projet.

---

# 🤖 Classification assistée par RAG + LLM

Le backend intègre également un mécanisme de **Retrieval-Augmented Generation (RAG)**.

Le principe est de fournir au modèle de langage un contexte documentaire permettant d'améliorer la classification des données.

```text
Documents RGPD / CNIL
          │
          ▼
      Découpage
          │
          ▼
      Embeddings
          │
          ▼
         FAISS
          │
          ▼
Recherche du contexte
          │
          ▼
       Mistral
          │
          ▼
Classification RGPD
```

Le modèle de langage est exécuté localement avec **Ollama**, ce qui permet au système de fonctionner sans envoyer les données analysées vers un service externe. Le rapport décrit Ollama comme permettant l'exécution locale de modèles LLM.

---

# 🔄 Fonctionnement global du backend

Le traitement d'une donnée peut être résumé ainsi :

```text
1. Connexion utilisateur
          ↓
2. Identification du profil
          ↓
3. Accès autorisé
          ↓
4. Sélection / scan de la base
          ↓
5. Analyse des colonnes
          ↓
6. Classification du risque
          ↓
7. Détermination du niveau d'anonymisation
          ↓
8. Application des règles
          ↓
9. Retour des données protégées
```

L'objectif est d'adapter le traitement de la donnée en fonction de sa sensibilité et des autorisations de l'utilisateur.

---

# 🧩 Technologies Backend

| Technologie         | Utilisation                             |
| ------------------- | --------------------------------------- |
| **Python**          | Développement du backend                |
| **Flask**           | API et serveur backend                  |
| **Oracle Database** | Stockage et accès aux données           |
| **PL/SQL**          | Gestion de la base de données           |
| **Ollama**          | Exécution locale du LLM                 |
| **Mistral**         | Classification assistée par LLM         |
| **FAISS**           | Recherche vectorielle                   |
| **Embeddings**      | Représentation sémantique des documents |
| **RAG**             | Recherche de contexte documentaire      |
| **REST / JSON**     | Communication frontend/backend          |

Le rapport confirme l'utilisation de Python pour le backend/API, React/CSS pour l'interface et PL/SQL pour la base de données.

---

# 🔒 Sécurité du backend

Le système intègre un contrôle d'accès basé sur les profils.

Chaque utilisateur ne peut accéder qu'aux fonctionnalités correspondant à ses autorisations.

Les tests réalisés dans le projet comprennent notamment :

* accès non autorisé à l'espace administrateur ;
* accès direct sans authentification ;
* isolation entre les espaces des différents rôles.

Ces tests ont été validés dans le cadre du projet.

---

# 👨‍💻 Partie technique mise en avant

La partie backend du projet met principalement en œuvre :

```text
Python
 │
 ├── API REST
 │
 ├── Authentification
 │
 ├── RBAC / contrôle d'accès
 │
 ├── Connexion Oracle
 │
 ├── Scan de la base
 │
 ├── Classification RGPD
 │
 ├── RAG
 │     ├── Embeddings
 │     ├── FAISS
 │     └── Recherche de contexte
 │
 ├── Mistral / Ollama
 │
 ├── Gestion du cache
 │
 ├── Anonymisation
 │
 └── Simulation
```

L'interface administrateur permet ensuite de **piloter ces fonctionnalités depuis l'application**, notamment le scan, la modification des classifications, la gestion du cache, le changement du degré d'anonymisation et la simulation.

---

# 📌 Confidentialité

Le projet ayant été réalisé dans un contexte bancaire, les données réelles, informations confidentielles, identifiants de connexion, mots de passe et paramètres sensibles de l'environnement de production ne doivent pas être publiés dans ce repository.

Le repository doit contenir uniquement le code nécessaire à la compréhension de l'architecture et du fonctionnement du projet.

---

# 👨‍💻 Auteur

**Slim Sallem**

Licence en Informatique Appliquée à la Gestion — spécialité Business Intelligence

Projet de fin d'études — 2025/2026

**BIAT Innovation & Technology**
