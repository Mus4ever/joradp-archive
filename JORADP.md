CONTEXTE : Projet d'archive bilingue JORADP (Journal Officiel algérien), pipeline en 12 phases 
(voir Project_Plan.md). Un banc d'essai OCR (Phase 5) vient de produire des résultats non fiables 
à cause de bugs de mesure identifiés. Avant d'autoriser le passage à la Phase 6, je veux : 
(A) corriger tous les bugs de mesure Phase 5, (B) re-générer un classement OCR fiable, 
(C) auditer les phases 0-4 avec des tests concrets, (D) documenter des critères de sortie explicites.

Ne suppose rien, ne "résous" rien à l'œil — chaque correction doit être vérifiée par un test 
reproductible sur des données réelles, avec un chiffre à l'appui (règle transversale du Project_Plan).

═══════════════════════════════════════════════════════════
PARTIE A — CORRIGER LES 4 BUGS DE MESURE DE tools/phase5_ocr_benchmark.py
═══════════════════════════════════════════════════════════

Applique les 4 correctifs suivants, DANS CET ORDRE, en testant après chaque étape :

A1. [Impact le plus fort probable] BUG DE FRAGMENTATION LIGNE-PAR-LIGNE dans 
    evaluate_ground_truth_matching() (lignes 71-92).
    
    Problème : la fonction compare chaque ligne du ground truth (une phrase complète, ~10-15 mots) 
    à la MEILLEURE ligne OCR individuelle. Or EasyOCR et PaddleOCR renvoient une ligne par boîte 
    de détection, pas par phrase — une phrase correctement reconnue mais éclatée en 3-4 boîtes 
    obtient un WER catastrophique même si tous les mots sont exacts.
    
    Preuve à reproduire toi-même avant de corriger : prends une ligne du ground truth, simule un 
    texte OCR "parfait" en 1 seul bloc vs le même texte coupé en 4 fragments, calcule WER/CER dans 
    les deux cas avec la fonction actuelle, montre-moi l'écart.
    
    Fix : remplace la comparaison ligne-à-ligne par un alignement en fenêtre glissante sur le texte 
    OCR concaténé. Pour chaque ligne de référence de N mots :
      1. Concatène TOUTES les lignes OCR de la page en un seul flux de mots (dans l'ordre de sortie 
         du moteur)
      2. Fais glisser une fenêtre de N, N-1, N+1, N+2 mots sur ce flux
      3. Calcule le WER entre la ligne de référence et chaque fenêtre
      4. Garde la meilleure fenêtre (WER minimal)
    Implémente ça, teste sur le même cas simulé qu'à l'étape précédente, prouve que le WER redevient 
    ~0% pour un texte fragmenté mais parfaitement reconnu.

A2. NORMALISATION UNICODE ARABE (lignes 46, 54-55) — fix déjà spécifié dans 
    RAPPORT_DIAGNOSTIC_ANOMALIES_PHASE5.md, section Anomalie 1 :
    - NFC systématique avant toute comparaison
    - Unification des variantes de Alef (إأآٱ → ا)
    - Suppression des harakat/diacritiques (\u064B-\u065F, \u0670)
    - Séparation de la ponctuation arabe collée (، ؛ ؟) par des espaces avant split()
    Applique la fonction normalize_for_wer() du rapport, appelle-la dans line_wer() ET line_cer() 
    (actuellement seul line_wer/line_cer utilisent .split() brut — vérifie qu'aucun autre point 
    d'entrée du scoring n'a été oublié).
    Teste sur AR-01 : le WER sur la ligne avec "أكتوبر" vs "اكتوبر" doit tomber à 0%.

A3. PADDLEOCR — CLASSIFIEUR D'ANGLE INCOMPATIBLE ARABE (ligne 185) — fix du rapport, 
    section Anomalie 2 :
    - use_angle_cls=False spécifiquement pour lang='ar' (garder True pour français)
    - rec_image_inverse=True explicite pour l'arabe
    Avant/après : mesure la précision AR sur les 15 pages arabes avec l'ancienne config (0.1% 
    attendu) puis la nouvelle, montre le delta chiffré.

A4. EASYOCR — CPU FORCÉ + RECHARGEMENT ×30 (lignes 151, 154) — fix du rapport, 
    section Anomalie 3 :
    - os.environ.pop('CUDA_VISIBLE_DEVICES', None) avant torch.cuda.is_available()
    - Passe en mode batch : un seul subprocess par langue (15 pages AR, 15 pages FR), 
      Reader() instancié UNE fois, boucle sur les images à l'intérieur du même processus
    - Log explicite du device réellement utilisé (torch.cuda.get_device_name(0) si dispo)
    Vérifie avec nvidia-smi pendant l'exécution que le GPU est bien sollicité, capture une preuve 
    (screenshot ou log d'utilisation GPU >0%).

Après A1-A4 : montre-moi le diff complet du fichier tools/phase5_ocr_benchmark.py corrigé.

═══════════════════════════════════════════════════════════
PARTIE B — RE-GÉNÉRER UN CLASSEMENT OCR FIABLE
═══════════════════════════════════════════════════════════

1. Relance le banc d'essai complet (30 pages, Tesseract + EasyOCR + PaddleOCR — Surya déjà exclu) 
   avec le script corrigé.
2. Produis le nouveau tableau comparatif (même format que RAPPORT_BENCHMARK_OCR_PHASE_5.md).
3. Compare AVANT/APRÈS pour les 3 moteurs : la précision doit maintenant être dans un ordre de 
   grandeur crédible pour de l'OCR sur scans dégradés (typiquement 40-90% selon l'époque, pas 
   0.1-12%). Si un moteur reste sous 20% de précision après tous les fixes, n'accepte pas le 
   résultat tel quel — investigue pourquoi au lieu de le reporter comme "faible mais correct".
4. Vérification manuelle anti-hallucination (obligatoire, pas optionnelle) : choisis 3 pages 
   (1 Legacy AR, 1 Transition FR, 1 Moderne AR ou FR), affiche l'image scannée à côté du texte 
   OCR corrigé ET du ground truth, et confirme visuellement que le score reflète la réalité — 
   pas seulement que le calcul tourne sans erreur.
5. Recommande un moteur gagnant par langue avec les nouveaux chiffres, pas les anciens.

═══════════════════════════════════════════════════════════
PARTIE C — AUDIT DES PHASES 0-4 AVANT D'AUTORISER LA PHASE 6
═══════════════════════════════════════════════════════════

Le pipeline (http_client.py, rate_limiter.py, database.py, discover.py, download_optimized.py, 
phase4_extractor.py) a été revu au niveau du code et semble structurellement solide, mais n'a pas 
été vérifié avec des tests d'exécution réels sur données. Avant la Phase 6, exécute ces contrôles :

C1. Phase 2 (découverte) : relance discover_annual_index() sur 3 années témoins bien distinctes 
    (ex: 1965, 1994, 2020) pour FR et AR. Compare le nombre de numéros découverts au nombre réel 
    connu (à vérifier manuellement sur le site ou via une source externe fiable) pour détecter 
    tout trou de couverture silencieux.

C2. Phase 3 (téléchargement) : prends un échantillon de 20 PDF déjà téléchargés, revalide-les 
    (validate_pdf()), confirme qu'aucun n'est corrompu silencieusement. Teste la reprise après 
    interruption : lance un lot, interromps-le (Ctrl+C) au milieu, relance, vérifie qu'aucun 
    fichier n'est ni dupliqué ni perdu.

C3. Phase 4 (extraction native) — PRIORITAIRE, car c'est la logique la plus fragile du pipeline : 
    la fonction extract_arabic_rtl_reordered() est une heuristique géométrique (détection de 
    colonnes par position X/Y) qui n'a jamais été validée contre une vraie vérité terrain ligne 
    par ligne, seulement contre la présence de texte. Prends 5 pages arabes réparties sur 
    1965/1980/2000/2012/2023 (le layout a changé sur 64 ans), extrais-les avec 
    extract_arabic_rtl_reordered(), affiche le texte extrait à côté de l'image scannée, et confirme 
    manuellement que l'ordre de lecture est correct — pas seulement que le texte est présent. 
    Fais la même chose pour extract_french_native() sur 3 pages françaises legacy/moderne.
    Consulte et consolide aussi ce qui existe déjà dans extraction_diagnosis/extraction_diagnosis_report.md, 
    extraction_diagnosis/final_diagnosis_report.md et rtl_validation/final_rtl_report.md — je ne les 
    ai pas encore audités en détail, vérifie s'ils couvrent déjà ce point ou s'ils datent d'une 
    version antérieure du code.

═══════════════════════════════════════════════════════════
PARTIE D — CRITÈRES DE SORTIE EXPLICITES AVANT PHASE 6 (pas de passage automatique)
═══════════════════════════════════════════════════════════

Ne me propose de passer à la Phase 6 QUE si TOUS les points suivants sont vrais et démontrés par 
un chiffre ou un exemple concret, jamais par une impression :

☐ Le script de scoring Phase 5 corrigé produit des précisions crédibles (pas de moteur sous ~20% 
  sans investigation supplémentaire)
☐ Le classement gagnant par langue (AR / FR) est confirmé par vérification visuelle sur au moins 
  3 pages, pas seulement par le score automatique
☐ La couverture de découverte (Phase 2) sur les 3 années témoins correspond aux volumes réels 
  attendus, écarts documentés si il y en a
☐ La reprise après interruption (Phase 3) fonctionne sans duplication ni perte, testée et pas 
  supposée
☐ L'ordre de lecture RTL de l'extraction native (Phase 4) est confirmé correct sur au moins 5 
  pages arabes couvrant différentes décennies
☐ Un rapport de synthèse final récapitule chaque point ci-dessus avec les chiffres à l'appui, 
  prêt à être présenté avant le lancement de la Phase 6

Donne-moi ce rapport de synthèse final avant toute action Phase 6, avec un GO/NO-GO explicite 
et justifié pour chaque phase.