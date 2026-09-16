🛡️ Système intelligent d’anonymisation et de classification des données selon le profil et le niveau de risque RGPD
📌 Description du projet
Ce projet consiste à développer un système intelligent d’anonymisation et de classification des données permettant de faciliter la protection des données personnelles et le respect du Règlement général sur la protection des données (RGPD), tout en préservant au maximum l’utilité des données pour les différents besoins métiers.

L’objectif est de mettre en place une approche dynamique dans laquelle le niveau d’anonymisation appliqué à une donnée dépend à la fois :

du niveau de risque associé à la donnée ;
du profil de l’utilisateur ;
du contexte d’utilisation de la donnée ;
et des besoins d’analyse.
Le système est organisé autour de trois composants principaux :

🤖 Classification intelligente des données
🔐 Proxy d’anonymisation dynamique
📊 Dashboard d’administration
🏗️ Architecture générale
                    ┌──────────────────────────┐
                    │       Base de données    │
                    │                          │
                    │ Tables / Colonnes / Data │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Classification intelligente│
                    │                          │
                    │       LLM + RAG          │
                    │                          │
                    │ Analyse + Questions      │
                    │ + Contexte RGPD         │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Niveau de risque         │
                    │                          │
                    │ Faible / Moyen / Élevé  │
                    │ / Critique               │
                    └────────────┬─────────────┘
                                 │
                                 ▼
              ┌────────────────────────────────────┐
              │       Proxy d'anonymisation        │
              │                                    │
              │ Profil utilisateur + Niveau risque │
              │                                    │
              │ Application dynamique des         │
              │ techniques d'anonymisation         │
              └────────────────┬───────────────────┘
                               │
                               ▼
                    ┌──────────────────────────┐
                    │ Données anonymisées      │
                    │                          │
                    │ Utiles pour l'analyse    │
                    └──────────────────────────┘

                               ▲
                               │
                    ┌──────────┴───────────────┐
                    │   Dashboard Administrateur│
                    │                           │
                    │ Classification            │
                    │ Correction                │
                    │ Scan                      │
                    │ Cache                     │
                    │ Profils & accès           │
                    └──────────────────────────┘
🤖 1. Classification intelligente des données
La première partie du système consiste à identifier et classifier les données présentes dans la base de données.

Pour cela, le système utilise un modèle LLM associé à une architecture RAG (Retrieval-Augmented Generation).

Le système fournit au modèle plusieurs informations permettant d’améliorer la classification :

Nom de la base de données
Nom de la table
Nom de la colonne
Valeurs échantillons synthétiques
Contexte RGPD récupéré grâce au RAG
Réponses à plusieurs questions permettant d’affiner l’évaluation du risque
Le modèle analyse ces informations afin de déterminer le niveau de risque associé à la colonne.

🎯 Niveaux de classification
Les données sont réparties en quatre niveaux :

Niveau

Description

🟢 Faible

Données présentant un faible niveau de risque

🟡 Moyen

Données nécessitant une protection intermédiaire

🟠 Élevé

Données présentant un risque important

🔴 Critique

Données nécessitant un niveau de protection très élevé

Le résultat de la classification est ensuite utilisé par le proxy d’anonymisation afin de déterminer le niveau de protection nécessaire.

🧠 Rôle du LLM + RAG
Le LLM ne se base pas uniquement sur le nom de la colonne. Il prend également en compte le contexte fourni par le système et les informations récupérées par le RAG afin de produire une classification plus pertinente.

Un mécanisme de questions/réponses est également utilisé pour compléter l’analyse et aider à déterminer le niveau de risque.

⚠️ La classification proposée par le LLM reste contrôlable par l’administrateur. Celui-ci conserve la possibilité de vérifier et de modifier les résultats.

🔐 2. Proxy d’anonymisation dynamique
La deuxième partie du projet est un proxy d’anonymisation placé entre l’utilisateur et les données.

Lorsqu’un utilisateur demande l’accès à des données, le proxy analyse :

le profil de l’utilisateur ;
le niveau de classification de la donnée ;
le niveau d’anonymisation requis pour ce profil ;
le type de donnée.
Le proxy applique ensuite automatiquement la technique d’anonymisation appropriée.

🔄 Fonctionnement
Utilisateur
     │
     ▼
Requête vers les données
     │
     ▼
┌─────────────────────┐
│ Proxy d'anonymisation│
└──────────┬──────────┘
           │
           ├── Profil utilisateur
           │
           ├── Classification de la donnée
           │
           └── Niveau d'anonymisation
                    │
                    ▼
          Technique appropriée
                    │
                    ▼
           Donnée anonymisée
                    │
                    ▼
                Utilisateur
🧩 Techniques d’anonymisation
Le proxy peut utiliser différentes techniques selon le type de donnée et le niveau de protection nécessaire.

Par exemple :

Tokenisation
Masquage
Format-Preserving Encryption (FPE)
Ajout de bruit statistique
Transformation des dates
Techniques adaptées aux données numériques
Pour les données numériques, différents mécanismes de bruit peuvent être utilisés afin de protéger les valeurs tout en conservant leur utilité pour certaines analyses.

Pour les dates, il est par exemple possible de réduire la précision :

Date exacte
2026-09-16
      ↓
Année
2026
ou :

2026-09-16
      ↓
2026-Q3
L’objectif n’est donc pas simplement de supprimer ou de rendre inutilisables les données, mais de trouver un équilibre entre protection et utilité.

Par exemple, pour une analyse statistique des prix, un niveau de bruit adapté peut permettre de protéger les valeurs individuelles tout en conservant des tendances globales exploitables.

📊 3. Dashboard Administrateur
La troisième partie du projet est un dashboard destiné à l’administrateur.

Le dashboard permet de superviser et de contrôler l’ensemble du processus de classification et d’anonymisation.

👨‍💻 Fonctionnalités principales
L’administrateur peut notamment :

consulter les résultats de classification du LLM ;
vérifier les niveaux attribués aux différentes colonnes ;
corriger manuellement une classification lorsqu’elle est incorrecte ;
lancer un nouveau scan de la base de données ;
consulter et gérer le cache de classification ;
gérer les profils utilisateurs ;
définir ou modifier les niveaux d’anonymisation associés aux profils ;
superviser les règles d’accès aux données.
⚡ Système de cache
La classification d’une base de données peut nécessiter l’analyse d’un grand nombre de tables et de colonnes.

Afin d’éviter de solliciter inutilement le LLM pour des données déjà analysées, un mécanisme de cache a été mis en place.

Lorsqu’une colonne a déjà été classifiée, le système peut réutiliser son résultat au lieu de refaire une nouvelle analyse.

Cela permet notamment :

de réduire le nombre d’appels au LLM ;
d’améliorer les performances ;
de réduire les coûts liés à l’utilisation du modèle ;
de conserver une classification stable jusqu’à sa modification par l’administrateur ou un nouveau scan.
🖥️ Aperçu du Dashboard
📸 Insérer ici une capture d’écran du dashboard administrateur

[ IMAGE DU DASHBOARD ADMINISTRATEUR ]
👥 Gestion des profils
Le niveau d’anonymisation n’est pas nécessairement identique pour tous les utilisateurs.

Le système permet donc d’associer différents niveaux d’accès et d’anonymisation aux profils.

Par exemple :

                    Donnée classifiée
                          │
                          ▼
                 Niveau de risque
                          │
              ┌───────────┴───────────┐
              │                       │
         Profil A                  Profil B
              │                       │
       Anonymisation faible     Anonymisation forte
              │                       │
              ▼                       ▼
       Données plus utiles       Données plus protégées
Cette approche permet d’adapter la protection au contexte d’utilisation tout en conservant autant que possible la valeur analytique des données.

🎯 Objectifs du projet
Les principaux objectifs du système sont :

🔒 Protéger les données sensibles et personnelles
🤖 Automatiser la classification des données grâce à un LLM + RAG
👤 Adapter l’anonymisation au profil de l’utilisateur
🛡️ Faciliter la mise en œuvre des principes de protection des données
📊 Préserver l’utilité des données pour les analyses
⚡ Réduire les traitements inutiles grâce au système de cache
👨‍💻 Permettre à l’administrateur de contrôler et corriger les décisions du système
🔄 Appliquer dynamiquement différentes techniques d’anonymisation
🛠️ Technologies
Le projet repose notamment sur :

Python
LLM
RAG (Retrieval-Augmented Generation)
React
Base de données Oracle
PL/SQL
Algorithmes et techniques d’anonymisation
API / Proxy d’accès aux données
🔒 Principe de sécurité
Un principe important du projet est que le LLM ne constitue pas l’autorité finale.

Le modèle fournit une proposition de classification, tandis que l’administrateur peut :

vérifier le résultat ;
modifier la classification ;
conserver la classification proposée ;
relancer une analyse si nécessaire.
Le système combine ainsi automatisation intelligente et contrôle humain.

🚀 Vision du projet
Ce projet propose une approche permettant d’intégrer la protection des données directement dans le processus d’accès aux données.

Au lieu d’appliquer une anonymisation identique à toutes les données et à tous les utilisateurs, le système cherche à adapter dynamiquement la protection en fonction du niveau de risque, du profil utilisateur et du contexte d’utilisation.

L’objectif final est de trouver un équilibre entre :

Protection des données 🔒 + Conformité RGPD 📋 + Utilité des données 📊

tout en donnant à l’administrateur un contrôle complet sur les décisions de classification et les règles d’anonymisation.
