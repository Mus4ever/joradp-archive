# Structure du site JORADP — constat validé

Synthèse du constat de structure de [joradp.dz](https://www.joradp.dz),
établie manuellement dans le navigateur puis contrôlée sur le HTML brut
(août 2026). Le journal complet des validations phase par phase se trouve
dans [`docs/journal-phases.md`](docs/journal-phases.md).

## Respect du serveur

- `robots.txt` répond 404 : politique de politesse par défaut appliquée
  (2 s minimum entre requêtes, User-Agent explicite, 3 tentatives avec
  backoff exponentiel).
- Le serveur utilise une négociation TLS ancienne. Le client retenu
  (`httpx` + `truststore.SSLContext`) active uniquement le bit OpenSSL
  `SSL_OP_LEGACY_SERVER_CONNECT` et **conserve** `CERT_REQUIRED` et
  `check_hostname=True`. Jamais de `verify=False` ni `CERT_NONE`.

## Navigation

La racine ouvre `/HAR/Index.htm`, un frameset. Index annuels :

- arabe : `/JRN/ZA{année}.htm` — français : `/JRN/ZF{année}.htm`

Le HTML brut contient les numéros (liens `javascript:MaxWin('001')` ou
formulaire `zFrm2`/`znjo` pour les années récentes) : un client HTTP +
BeautifulSoup suffit, pas de navigateur headless.

## Modèles d'URL des PDF complets

- FR : `/FTP/JO-FRANCAIS/{année}/F{année}{numéro}.pdf`
- AR : `/FTP/jo-arabe/{année}/A{année}{numéro}.pdf`

Le serveur est insensible à la casse des chemins FTP (vérifié FR 1962 et
AR 1983 sur les trois casses) ; ces deux formes ont été choisies par
convention interne, documentée dans le journal (Phase 2, problème 3).

## Pages historiques (vue alternative)

`JVS/Journal.js` décrit une vue page-à-page avec racine `Jo6283`
(1962-1983) puis `Jo8499` (1984-1999) :
`/{Jo6283|Jo8499}/{année}/{numéro}/{langue}_Pag1.htm` et liens
`{langue}p{n}.pdf`. Elle coexiste avec les PDF complets directs au moins
jusqu'en 1999. Décision retenue : le PDF complet est la source primaire ;
la vue historique sert de provenance alternative et de voie de récupération.

## Cas d'encodage particuliers

- Les index AR 2025-2026 sont servis en **UTF-16** : le forçage
  `force_encoding='utf-16'` est appliqué pour `AR and annee >= 2025`,
  avec repli sur l'encodage standard en cas d'échec.
- L'index AR 2026 n'expose pas de liens MaxWin : les numéros sont extraits
  des options du select `znjo` du formulaire `zFrm2`.

## Couverture confirmée

- FR : 65 années (1962-2026), 5 208 numéros.
- AR : 63 années (1964-2026), 5 224 numéros.
- Total : 10 432 sources, toutes téléchargées et vérifiées (SHA-256).
