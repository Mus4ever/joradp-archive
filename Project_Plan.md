PROJET : Archive bilingue complète du Journal Officiel algérien (JORADP)

═══════════════════════════════════════════════════════════
OBJECTIF FINAL
═══════════════════════════════════════════════════════════
Construire un pipeline Python automatique et reproductible qui indexe,
télécharge et extrait le texte de TOUTES les publications du Journal
Officiel algérien depuis leur origine, dans les deux langues officielles,
SANS traduction — chaque langue doit contenir son propre texte source
natif, jamais une traduction générée depuis l'autre langue.

Source unique : [https://www.joradp.dz](https://www.joradp.dz)

Couverture exacte :
\- Édition française : à partir de 1962 jusqu'à 2026
\- Édition arabe : à partir de 1964 jusqu'à 2026
&#x20; (il n'existe pas d'édition arabe en 1962-1963 ; en 1964 l'arabe s'arrête
&#x20; au n°64 ; de 1964 à 1993 l'arabe est distribué page PDF par page PDF,
&#x20; pas en PDF complet — le programme doit gérer cette différence de format
&#x20; au lieu de supposer une structure uniforme sur toute la période)

INTERDICTION ABSOLUE : aucune traduction automatique, aucune génération
de texte par un modèle de langage pour "compléter" ou "reconstituer" un
texte manquant ou illisible. Si un texte est illisible, il doit être
marqué comme tel (needs\_review), jamais deviné ou reformulé.

═══════════════════════════════════════════════════════════
PHASE 0 — CADRAGE ET SÉCURITÉ AVANT TOUT CODE
═══════════════════════════════════════════════════════════
1\. Vérifie le fichier /robots.txt du site et respecte ses règles.
2\. Prévois un délai minimum de 2 secondes entre chaque requête HTTP,
&#x20;  avec un User-Agent identifiable (pas un User-Agent de navigateur
&#x20;  déguisé), et un système de retry avec backoff exponentiel (3 tentatives
&#x20;  max) pour ne jamais surcharger un serveur gouvernemental.
3\. Crée un environnement Python isolé (venv) et un requirements.txt
&#x20;  versionné dès le départ.
4\. Ne code rien avant d'avoir confirmé, en explorant le site à la main
&#x20;  avec le navigateur (DevTools), où se trouvent réellement : les index
&#x20;  annuels, les PDF complets FR/AR, et les pages arabes historiques
&#x20;  1964-1993. Documente la structure réelle avant d'écrire le moindre
&#x20;  parseur — ne suppose jamais un format sans l'avoir vu.

═══════════════════════════════════════════════════════════
PHASE 1 — CHOIX DES OUTILS DE SCRAPING (à valider, pas à supposer)
═══════════════════════════════════════════════════════════
Le site JORADP est structurellement un vieux site HTML/frameset, a priori
sans rendu JavaScript lourd. Avant de choisir un outil, vérifie cette
hypothèse en inspectant le HTML brut retourné par une requête simple
(pas de navigateur headless) :

1\. Si le contenu utile (liens vers PDF, index annuels) est présent dans
&#x20;  le HTML brut → utilise \`httpx\` ou \`requests\` + \`BeautifulSoup\`/\`lxml\`
&#x20;  pour l'extraction, orchestré par \`Scrapy\` si le volume total (des
&#x20;  dizaines de milliers de PDF sur 64 ans) justifie la gestion native de
&#x20;  la concurrence, des reprises et des files d'attente que Scrapy offre.
2\. Si le contenu dépend de JavaScript pour apparaître → utilise
&#x20;  \`Playwright\` (plus robuste et plus rapide que Selenium aujourd'hui).
3\. Dans tous les cas : stocke l'état de chaque source (année, numéro,
&#x20;  langue, URL, statut, taille, SHA-256) dans SQLite, pas en mémoire —
&#x20;  le pipeline doit être reprenable après interruption sans dupliquer
&#x20;  ni perdre de travail déjà fait.

═══════════════════════════════════════════════════════════
PHASE 2 — DÉCOUVERTE AUTOMATIQUE (pas d'URL codées en dur)
═══════════════════════════════════════════════════════════
1\. Parcours les index annuels du site pour découvrir automatiquement
&#x20;  tous les PDF complets disponibles, français et arabe, de 1962/1964
&#x20;  à 2026.
2\. Pour la période 1964-1993 côté arabe, découvre spécifiquement l'index
&#x20;  des pages historiques (page par page), en gérant le cas où le nombre
&#x20;  de pages varie d'un numéro à l'autre.
3\. Journalise dans SQLite chaque URL découverte avec son année, numéro,
&#x20;  langue et type (pdf\_complet ou page\_historique), avant tout
&#x20;  téléchargement.
4\. Produis un rapport de couverture : combien de numéros attendus vs
&#x20;  combien réellement découverts, par année et par langue, pour repérer
&#x20;  tout de suite les trous.

═══════════════════════════════════════════════════════════
PHASE 3 — TÉLÉCHARGEMENT PAR LOTS
═══════════════════════════════════════════════════════════
1\. Télécharge par lots contrôlés (commence à 50-100 fichiers par lot),
&#x20;  avec le délai de 2 secondes entre requêtes déjà mentionné.
2\. Calcule et stocke le SHA-256 de chaque fichier téléchargé, pour
&#x20;  détecter toute corruption ou modification ultérieure côté source.
3\. Le programme doit pouvoir être interrompu (Ctrl+C, coupure réseau,
&#x20;  redémarrage) et reprendre exactement là où il s'était arrêté, sans
&#x20;  retélécharger ce qui est déjà présent et validé.
4\. Journalise chaque échec avec la raison (timeout, 404, fichier
&#x20;  corrompu) dans une table dédiée, jamais silencieusement ignoré.

═══════════════════════════════════════════════════════════
PHASE 4 — EXTRACTION DE TEXTE NATIF
═══════════════════════════════════════════════════════════
1\. Utilise PyMuPDF (fitz) pour extraire le texte natif de chaque PDF.
2\. Pour chaque PDF, détermine s'il contient du texte natif exploitable
&#x20;  ou s'il s'agit d'un scan (image) nécessitant l'OCR — marque
&#x20;  explicitement \`needs\_ocr\` dans SQLite pour ces derniers, ne force
&#x20;  jamais l'OCR sur un texte déjà natif et propre.
3\. Attention : le texte natif français ET arabe doit être vérifié
&#x20;  séparément — un PDF bilingue mal extrait peut donner un texte français
&#x20;  correct mais un texte arabe dans le désordre même sans passer par
&#x20;  l'OCR, à cause de l'ordre d'extraction des blocs PDF. Vérifie l'ordre
&#x20;  de lecture du texte arabe natif extrait, pas seulement sa présence.

═══════════════════════════════════════════════════════════
PHASE 5 — BANC D'ESSAI OCR MULTI-MOTEURS (GPU d'abord, précision toujours prioritaire)
═══════════════════════════════════════════════════════════
Ne choisis aucun moteur OCR par défaut. Fais un vrai banc d'essai
comparatif AVANT tout traitement de masse, sur un échantillon d'au moins
25-30 pages réparties sur TOUTE la période (legacy 1964-1993, ère PDF
complet 1994-2009, période récente 2010-2026), pour le français et
l'arabe séparément :

Moteurs GPU à tester en priorité (les plus récents et capables) :
1\. \*\*PaddleOCR-VL\*\* (dernière version stable disponible, 1.6 ou plus
&#x20;  récente si sortie) — modèle multilingue par vision-langage, meilleur
&#x20;  que les anciennes versions PaddleOCR 2.x/3.x pour la compréhension de
&#x20;  la mise en page et l'ordre de lecture RTL de l'arabe.
2\. \*\*Surya\*\* — couverture multilingue large, à tester spécifiquement sur
&#x20;  l'ordre de lecture droite-à-gauche.
3\. \*\*DeepSeek-OCR\*\* ou \*\*GOT-OCR 2.0\*\* — modèles vision-langage récents,
&#x20;  à tester en comparaison si les deux précédents ne suffisent pas.

Moteur CPU de référence obligatoire (déjà validé empiriquement comme
solide pour l'arabe) :
4\. \*\*Tesseract\*\* avec le pack \`ara\` — sert de référence indépendante ;
&#x20;  s'il bat tous les modèles GPU sur la précision, GARDE-LE, même sur
&#x20;  CPU. Le critère de choix est la précision du texte, jamais le device.

Méthode de mesure obligatoire (chiffrée, pas à l'œil) :
a. Pour chaque page testée, compte : mots complets correctement
&#x20;  reconnus / mots totaux visibles sur l'image, sur au moins 10 lignes.
b. Vérifie spécifiquement l'ordre de lecture (droite-à-gauche pour
&#x20;  l'arabe) — un mot bien reconnu mais mal placé compte comme faux.
c. Vérifie spécifiquement les chiffres et dates (grégoriennes,
&#x20;  hégiriennes, numéros de décret) séparément du texte général — un
&#x20;  moteur peut être bon sur le texte et mauvais sur les chiffres.
d. Mesure le temps de traitement par page pour chaque moteur, pour
&#x20;  estimer le temps total réaliste sur l'ensemble du corpus.
e. Choisis le moteur gagnant PAR LANGUE (le gagnant français peut être
&#x20;  différent du gagnant arabe), avec un flag de configuration explicite
&#x20;  dans le pipeline (pas de choix codé en dur), pour pouvoir changer de
&#x20;  moteur facilement si un meilleur modèle sort plus tard.

Ne lance JAMAIS l'OCR en masse sur tout le corpus avant que ce banc
d'essai ait donné un gagnant clair et mesuré pour chaque langue.

═══════════════════════════════════════════════════════════
PHASE 6 — VALIDATION AUTOMATIQUE DES DATES ET NUMÉROS (obligatoire, pas optionnelle)
═══════════════════════════════════════════════════════════
Les dates et numéros de référence sont statistiquement plus fragiles que
le texte général, quel que soit le moteur OCR choisi. Implémente un
contrôle automatique qui ne dépend JAMAIS d'une relecture humaine :

1\. Compare toute année grégorienne extraite à l'année du numéro JO déjà
&#x20;  connue (donnée qu'on a sans OCR, via l'index de découverte) — marque
&#x20;  \`ok\` (écart ≤2 ans), \`suspect\` (3-10 ans) ou \`error\` (>10 ans).
2\. Quand une date hégirienne et une date grégorienne apparaissent dans
&#x20;  le même texte, calcule la conversion et vérifie leur cohérence
&#x20;  mutuelle.
3\. Stocke un champ \`date\_confidence\` (ok/suspect/error/non\_extrait) par
&#x20;  donnée extraite, jamais un simple texte brut sans niveau de confiance.
4\. Teste ce contrôle sur un échantillon volontairement difficile
&#x20;  (au moins 5 pages de la période 1964-1993, qui a le format le plus
&#x20;  ancien) pour vérifier qu'il attrape vraiment les erreurs typiques,
&#x20;  pas seulement sur des cas faciles.

═══════════════════════════════════════════════════════════
PHASE 7 — EXTRACTION DES MÉTADONNÉES STRUCTURÉES
═══════════════════════════════════════════════════════════
1\. Extrais, pour chaque texte juridique contenu dans un numéro : nature
&#x20;  (loi, ordonnance, décret exécutif, décret présidentiel, arrêté...),
&#x20;  référence (ex: "n° 08-09"), titre/objet, date de signature, date de
&#x20;  parution, pages de début/fin, langue.
2\. Utilise des règles/regex distinctes pour le français et l'arabe
&#x20;  (les motifs ne sont pas symétriques : "Loi n°" / "قانون رقم",
&#x20;  "Décret exécutif" / "مرسوم تنفيذي", etc.), et prévois plusieurs
&#x20;  variantes de format selon les décennies (le style rédactionnel a
&#x20;  changé entre 1962 et 2026, ne suppose pas un format unique).
3\. Croise chaque métadonnée avec le contrôle de dates de la Phase 6.

═══════════════════════════════════════════════════════════
PHASE 8 — SEGMENTATION EN ARTICLES
═══════════════════════════════════════════════════════════
1\. Segmente chaque texte juridique en articles individuels, en
&#x20;  détectant les marqueurs "Article", "Art." en français et "المادة"
&#x20;  (et ses variantes : المادة الأولى, numérotation en lettres, etc.) en
&#x20;  arabe.
2\. Teste ce découpage sur des documents de plusieurs décennies avant de
&#x20;  généraliser — la mise en forme des articles a pu évoluer.
3\. Conserve toujours un lien vers le PDF source et la page exacte pour
&#x20;  chaque article extrait, pour permettre une vérification manuelle
&#x20;  ciblée si besoin, sans devoir tout revérifier.

═══════════════════════════════════════════════════════════
PHASE 9 — CONTRÔLE QUALITÉ PAR ÉCHANTILLONNAGE
═══════════════════════════════════════════════════════════
1\. Sur un échantillon couvrant plusieurs décennies et les deux langues,
&#x20;  compare manuellement (toi, l'agent, en affichant l'image à côté du
&#x20;  texte) le texte final structuré au PDF source.
2\. Priorise l'échantillon sur les zones à risque déjà identifiées :
&#x20;  pages de couverture (mise en page complexe), période legacy arabe
&#x20;  1964-1993, et tout document marqué \`suspect\` en Phase 6.
3\. Documente un taux d'erreur mesuré par période, pas une impression
&#x20;  générale de qualité.

═══════════════════════════════════════════════════════════
PHASE 10 — ASSOCIATION FRANÇAIS ↔ ARABE
═══════════════════════════════════════════════════════════
1\. N'associe un texte français à son équivalent arabe QUE lorsque la
&#x20;  référence ET le titre confirment qu'il s'agit du même texte juridique
&#x20;  — jamais uniquement sur la base année+numéro, qui peut ne pas
&#x20;  correspondre entre les deux éditions.
2\. Documente explicitement les cas où aucune correspondance fiable n'a
&#x20;  pu être établie, plutôt que de forcer un rapprochement incertain.
3\. Rappel : chaque langue garde son texte source natif à elle. Cette
&#x20;  phase relie deux textes déjà existants, elle n'en traduit ni n'en
&#x20;  génère aucun.

═══════════════════════════════════════════════════════════
PHASE 11 — LIVRAISON FINALE
═══════════════════════════════════════════════════════════
Livre :
\- Base SQLite complète (sources, métadonnées, articles, associations,
&#x20; niveaux de confiance)
\- Export CSV et JSON
\- Rapport de couverture (numéros attendus vs obtenus, par année/langue)
\- Rapport d'erreurs et de documents \`needs\_review\`
\- Rapport du banc d'essai OCR (quel moteur a gagné, pourquoi, chiffres
&#x20; à l'appui)
\- README expliquant comment relancer, étendre ou corriger le pipeline

═══════════════════════════════════════════════════════════
RÈGLES TRANSVERSALES (valables à chaque phase)
═══════════════════════════════════════════════════════════
\- Ne jamais avancer à la phase suivante sans avoir montré un échantillon
&#x20; concret de résultats de la phase en cours, pour validation avant de
&#x20; généraliser à tout le corpus.
\- Ne jamais supposer une structure (mise en page, format de date, ordre
&#x20; de lecture) sans l'avoir vérifiée sur des exemples réels tirés de
&#x20; plusieurs décennies différentes.
\- Toute affirmation de "succès" doit être accompagnée d'un chiffre
&#x20; mesuré sur un échantillon suffisant (15+ éléments), jamais d'une
&#x20; impression sur 1-2 exemples.
\- Aucune génération, traduction ou reconstruction de texte par un
&#x20; modèle de langage à la place d'un texte source manquant ou illisible.