# Pokémon 30 ans — Comparateur automatique + alertes de réassort

**État à la livraison : kit préparé et tests locaux réussis, mais pas encore déployé.** Les stocks réels ne sont pas fournis au départ : le **premier contrôle** est effectué sur GitHub après la mise en place.

Ce kit surveille **16 références de la série française 30C**, dont **34 fiches marchandes directes** chez Philibert, Playin, UltraJeux, Parkage et Smyths Toys. Les références pour lesquelles aucune fiche directe fiable n'a été identifiée restent visibles avec un lien vers Le Croco Deal.

## Fonctionnement

- Une tâche GitHub Actions vérifie les boutiques **chaque heure**, à environ **xx h 17 UTC**. Les tâches programmées peuvent démarrer avec du retard.
- Le site comparatif affiche les prix réellement détectés, les statuts et des liens directs. Il ne réalise pas d'achat.
- Une notification **ntfy** est envoyée **uniquement** lorsque la vérification identifie une disponibilité en livraison **et** un prix inférieur ou égal au plafond défini pour le produit. La vérification initiale peut déclencher une notification si une offre est déjà disponible.
- Les états « magasin uniquement », « précommande », « rupture », « à venir » et « non vérifiable » ne déclenchent **pas** d'alerte.
- Les prix repères viennent d'un ancien relevé du Croco Deal : **ce ne sont ni des prix officiels ni des offres garanties**.

## Mise en place pas à pas (environ 1 compte GitHub et l'application ntfy)

### 1. Mettre les fichiers sur GitHub

1. Connectez-vous sur **https://github.com/** et créez un dépôt **Public** nommé `pokemon-30-ans` (bouton **New repository**).
2. Décompressez `pokemon30_comparateur_alertes.zip`.
3. Dans le dépôt, choisissez **Add file → Upload files**. Faites glisser **le contenu** du dossier extrait, **y compris le dossier `.github`**. Terminez avec **Commit changes**.
4. Sur Mac, `.github` est un dossier masqué : dans le Finder, appuyez sur **Cmd + Maj + .** pour l'afficher avant de tout glisser dans la page GitHub.
5. Vérifiez sur GitHub que vous voyez bien le fichier **`.github/workflows/surveillance.yml`** ainsi que `index.html`, `surveillance.py`, `produits.json`, `offres.json` et `requirements.txt`.

> Si GitHub refuse l'envoi d'un dossier, glissez le dossier `.github` dans la zone de dépôt plutôt que de sélectionner les fichiers un par un. Il est indispensable que `.github/workflows/surveillance.yml` conserve sa structure.

### 2. Activer la publication gratuite du comparateur

1. Ouvrez le dépôt GitHub → **Settings → Pages**.
2. Dans **Build and deployment → Source**, sélectionnez **GitHub Actions**.
3. Ne choisissez pas « Deploy from a branch » : le kit publie directement le site depuis le workflow.

### 3. Configurer les alertes sur iPhone ou ordinateur

1. Installez **ntfy** sur iPhone depuis l'App Store, ou ouvrez **https://ntfy.sh/app** dans un navigateur.
2. Choisissez un **topic** long et imprévisible (au moins 16 caractères, lettres/chiffres/tirets), par exemple sous la forme `pokemon30_` suivi de **24 caractères aléatoires**. N'utilisez pas un topic court ou public.
3. Abonnez-vous à ce topic dans ntfy et autorisez les notifications.
4. Sur GitHub, ouvrez votre dépôt → **Settings → Secrets and variables → Actions → New repository secret**.
5. Nom du secret : **`NTFY_TOPIC`** ; valeur : **exactement le topic** choisi dans ntfy (sans `https://ntfy.sh/`). Validez.

> Le topic ntfy vaut pratiquement mot de passe pour cette chaîne de notifications : gardez-le secret. Les topics ntfy ordinaires ne bénéficient pas d'un contrôle d'accès individuel ; choisissez un nom impossible à deviner.

### 4. Lancer la première vérification

1. Ouvrez l'onglet **Actions** du dépôt. Si GitHub propose d'activer les workflows, acceptez.
2. Choisissez **« Vérifier les stocks Pokémon 30 ans »** puis **Run workflow → Run workflow**.
3. Laissez l'exécution s'achever ; l'indicateur doit devenir **vert**. En cas d'échec, ouvrez les détails de l'étape signalée : le site n'est pas encore en service.
4. Ouvrez **Settings → Pages** pour voir l'URL publique du comparateur. Elle aura généralement la forme :

   `https://VOTRE_PSEUDO.github.io/pokemon-30-ans/`

Il n'est pas nécessaire de laisser l'ordinateur allumé : GitHub effectue les contrôles et ntfy reçoit les alertes. Si aucun topic n'est configuré, le tableau peut fonctionner **sans notifications**.

## Personnaliser les seuils de prix

Sur GitHub, ouvrez `produits.json` puis l'icône **crayon (Edit)**. Pour chaque référence, modifiez uniquement `max_price`, en euros et avec un point :

```json
"id": "bundle",
"max_price": 39.99
```

Cette valeur définit le prix plafond **des alertes**, et non le prix réel. Une mise à jour du fichier sera prise en compte lors du contrôle suivant.

Pour ajouter une boutique, insérez dans la liste `links` de `produits.json` une fiche produit **avec un URL direct** et un identifiant unique. Vous pouvez copier une ligne existante puis adapter l'URL et la référence (`product_id`). Le produit doit être **en français, édition 30C**, et identique aux autres entrées de son groupe.

## Limites à connaître

- **Un système automatisé ne peut pas garantir les stocks.** Certains vendeurs masquent la disponibilité derrière du JavaScript, une connexion, un CAPTCHA ou une protection antibot : le tableau affichera **« Non vérifiable »**.
- La reconnaissance des sites repose sur leurs indications visibles et données structurées ; **une modification de leur site peut exiger une mise à jour du programme**. Vérifiez manuellement l'offre avant paiement.
- Les prix sont affichés **hors frais de port** et des disponibilités locales peuvent différer. La catégorie « En stock » signifie une **détection probable**, non une réservation ni la confirmation du paiement.
- Par prudence, les alertes ne sont pas déclenchées si le prix n'a pas pu être déterminé, même en présence d'un bouton panier.
- Les vérifications sont approximativement horaires. **GitHub ne garantit pas l'exécution à la minute précise** et peut désactiver les planifications inactives ; vérifiez ponctuellement l'onglet Actions.
- Une ancienne fiche **ETB descellée de Philibert** a volontairement été exclue des comparaisons : elle n'est pas équivalente à une ETB neuve scellée.
- Le comparateur sera **public** si le dépôt GitHub est public, mais la valeur du secret `NTFY_TOPIC` n'apparaît pas dans le code.
- Respectez les conditions d'utilisation des sites marchands. Un seul passage par heure, avec pause entre les pages, est configuré par défaut. Ne multipliez pas les contrôles.

## Vérifier le programme sans internet (facultatif)

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Il y a huit tests sur le comportement des stocks, des pages bloquées et des alertes. Ils ne constituent **pas** une vérification réseau des vendeurs ; le contrôle réel doit être effectué depuis GitHub.

## Sources / documentation

- Guides Pokémon : https://lecrocodeal.com/sports-loisirs/collection/pokemon
- Paramétrage GitHub Pages : https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- Notifications ntfy : https://docs.ntfy.sh/

Ce projet est indépendant et non affilié à Pokémon, Le Croco Deal ou aux boutiques suivies.
