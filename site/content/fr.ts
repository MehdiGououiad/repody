/** French: the site's default language (Morocco). Every fact here is true of the code today. */
export const fr = {
  lang: "fr",
  languageName: "Français",
  common: {
    skip: "Aller au contenu",
    nav: {
      platform: "Plateforme",
      security: "Sécurité",
      architecture: "Architecture",
      deployment: "Déploiement",
      engineering: "Ingénierie",
      solutions: "Secteurs",
      banks: "Banque",
      insurance: "Assurance",
      telecom: "Télécom",
    },
    demo: "Demander un accès",
    toLight: "Passer en mode clair",
    toDark: "Passer en mode sombre",
    seePlatform: "Voir la plateforme",
    learnMore: "En savoir plus",
    menu: "Menu",
    close: "Fermer",
    language: "Langue",
    footer: {
      tagline:
        "La plateforme d'audit documentaire qui lit vos documents, les contrôle selon vos règles et tourne sur vos serveurs.",
      product: "Produit",
      company: "Entreprise",
      contact: "Contact",
      legal: "Mentions légales",
      privacy: "Confidentialité",
      rights: "Tous droits réservés.",
      madeIn: "Conçu pour les banques, assureurs et opérateurs du Maroc.",
    },
    breadcrumbHome: "Accueil",
    onThisPage: "Sur cette page",
  },

  home: {
    meta: {
      title: "Repody : audit documentaire on-premise et marque blanche",
      description:
        "Repody extrait les données de vos factures, relevés, contrats et dossiers, les contrôle selon vos règles et rend un verdict. Installé sur vos serveurs, sous votre marque.",
    },
    hero: {
      title: "Vos documents lus, contrôlés et tranchés, sur vos serveurs",
      lead: "Repody extrait chaque champ de vos factures, relevés et contrats en un seul passage, applique vos règles métier et vous dit quoi examiner. Vous l'installez chez vous, sous votre marque.",
      note: "Licence perpétuelle · On-premise ou cloud privé · Français et anglais",
    },
    replay: {
      label: "Exécution en direct",
      queue: "En file d'attente",
      gpu: "Démarrage du GPU",
      gpuDone: "GPU démarré",
      gpuHint: "Le modèle se réveille depuis un instantané mémoire.",
      extract: "Extraction · Facture",
      rules: "Contrôle de 2 règles",
      save: "Enregistrement du rapport",
      verdict: "Rejeté",
      verdictFacts: "1 règle sur 2 respectée · 4 champs · 1,9 s",
      fields: [
        { key: "numero_facture", value: "FAC-2026-0412", ok: true },
        { key: "fournisseur", value: "Atlas Logistique SARL", ok: true },
        { key: "montant_ht", value: "48 500,00 MAD", ok: false },
        { key: "total_ttc", value: "58 800,00 MAD", ok: false },
      ],
      note: "Total TTC ≠ HT + TVA 20 %",
      gpuTime: "15 s",
      extractTime: "1,5 s",
    },
    proof: [
      { value: "1", label: "passage de l'image du document aux champs typés" },
      { value: "24", label: "types de champs, des dates aux IBAN et aux tableaux" },
      { value: "40", label: "pages A4 lues en une seule passe" },
      { value: "0", label: "octet de vos documents hors de votre réseau" },
    ],
    video: {
      title: "Repody en deux minutes",
      caption:
        "Un workflow de bout en bout : décrire les documents, écrire les règles, envoyer un fichier, lire le verdict.",
      soon: "Vidéo bientôt disponible",
    },
    how: {
      title: "De la pile de documents au verdict",
      lead: "Un workflow décrit ce que vous recevez et ce qui doit être vrai. Repody fait le reste, document après document.",
      steps: [
        {
          title: "Décrire les documents",
          body: "Nommez chaque document reçu et les champs à y lire : texte exact, montants, dates, IBAN, listes, tableaux.",
        },
        {
          title: "Écrire les règles",
          body: "Comparez des champs, faites des calculs, croisez deux documents. Chaque règle rejette ou signale.",
        },
        {
          title: "Envoyer les fichiers",
          body: "Depuis l'interface pour tester, depuis vos systèmes par l'API avec la clé du workflow.",
        },
        {
          title: "Lire le verdict",
          body: "Conforme, à examiner ou rejeté, avec chaque valeur extraite et la règle qui a échoué à côté.",
        },
      ],
    },
    compare: {
      title: "Un seul passage au lieu de trois",
      lead: "Les chaînes classiques convertissent le document en texte, puis en Markdown, puis demandent à un grand modèle de deviner. Chaque étape perd de l'information et coûte du temps.",
      oldTitle: "Chaîne classique",
      oldSteps: ["OCR", "Markdown", "Grand modèle de langage"],
      oldPoints: [
        "Trois appels à payer pour un document",
        "La mise en page et les cases à cocher se perdent",
        "Le modèle compense les erreurs de l'OCR sans voir la page",
        "Latences qui s'additionnent",
      ],
      newTitle: "Repody",
      newSteps: ["Image de la page", "Repody VLM", "Champs typés"],
      newPoints: [
        "Un modèle spécialisé lit l'image de la page directement",
        "Sortie contrainte par votre schéma : JSON valide et typé",
        "Tableaux, objets imbriqués et listes compris tels quels",
        "Un appel par document, plusieurs documents en parallèle",
      ],
    },
    tour: {
      title: "Ce que vos équipes utilisent chaque jour",
      lead: "Une interface dense et calme, pensée pour des opérateurs qui examinent des centaines de documents.",
      items: [
        {
          title: "Le rapport de chaque exécution",
          body: "Chaque champ sur sa ligne avec sa marque de statut, la règle en échec écrite à côté, la sortie brute du modèle à portée de main.",
          shot: "report",
          page: "platform",
          hash: "reports",
        },
        {
          title: "Un constructeur de workflows sans code",
          body: "Documents, champs et règles se lisent comme des phrases. Les règles sont vérifiées pendant que vous les écrivez.",
          shot: "builder-claim",
          page: "platform",
          hash: "builder",
        },
        {
          title: "Une vue d'ensemble qui commence par ce qui compte",
          body: "Ce qu'il faut examiner d'abord, puis le volume et le taux de réussite de la semaine.",
          shot: "overview",
          page: "platform",
          hash: "overview",
        },
      ],
    },
    brand: {
      title: "Votre marque, pas la nôtre",
      lead: "Nom, logo, couleur de base, couleur d'accent, contraste et rayon des coins : six réglages, et toute l'interface se recompose, en clair comme en sombre. Le contraste du texte est garanti par le moteur, quelle que soit la couleur choisie.",
      pick: "Choisissez une marque",
      darkMode: "Mode sombre",
      presets: ["Repody", "Banque", "Assurance", "Télécom"],
      mock: {
        title: "Dossiers à examiner",
        rows: ["Relevé bancaire · KYC", "Dossier sinistre auto", "Contrat entreprise"],
        status: ["Rejeté", "À examiner", "Conforme"],
        action: "Examiner",
      },
    },
    security: {
      title: "Sécurité et souveraineté, par conception",
      lead: "Repody est conçu pour des environnements régulés : vos documents ne quittent pas votre infrastructure et chaque accès passe par votre fournisseur d'identité.",
      items: [
        {
          title: "Vos données restent chez vous",
          body: "Base de données, stockage et modèle tournent dans votre réseau. Aucune donnée n'est envoyée à un tiers.",
        },
        {
          title: "Votre SSO, vos rôles",
          body: "OpenID Connect avec Keycloak, PKCE, double authentification pour les administrateurs, chaque connexion conservée 90 jours, et quatre rôles aux permissions précises.",
        },
        {
          title: "Clés d'API protégées",
          body: "Une clé par workflow, montrée une seule fois, stockée en empreinte SHA-256 et comparée en temps constant.",
        },
        {
          title: "Conteneurs durcis",
          body: "Utilisateurs non root, systèmes de fichiers en lecture seule, aucune élévation de privilèges, mémoire plafonnée.",
        },
        {
          title: "Images signées et vérifiées",
          body: "SBOM, provenance et signature Sigstore à chaque version ; la signature est vérifiée avant chaque déploiement.",
        },
        {
          title: "Aucun port ouvert",
          body: "Le trafic public passe par un tunnel sortant, l'administration par un réseau privé à identité vérifiée.",
        },
      ],
    },
    deploy: {
      title: "Installé là où vos données doivent rester",
      lead: "Le même produit, trois façons de l'exploiter.",
      options: [
        {
          title: "Un serveur",
          body: "Docker Compose sur une machine Linux : toute la pile avec ses journaux, le suivi des erreurs et des sauvegardes chiffrées chaque nuit, déployée automatiquement après une copie de préproduction.",
        },
        {
          title: "Kubernetes ou OpenShift",
          body: "Un chart Helm avec mise à l'échelle automatique, budgets de disponibilité et politiques réseau.",
        },
        {
          title: "Votre GPU ou un GPU managé",
          body: "Le modèle tourne sur votre carte graphique ou sur un GPU serverless qui s'éteint quand il ne sert pas.",
        },
      ],
    },
    engineering: {
      title: "Construit comme une infrastructure critique",
      lead: "Chaque modification passe par une chaîne de contrôles avant d'atteindre un serveur. Une version n'est déployée que si chacun d'eux est vert.",
      gates: [
        "Lint et formatage",
        "Typage",
        "Contrats d'architecture",
        "Tests sur PostgreSQL",
        "Contrat d'API",
        "Code mort",
        "Build",
        "Pile complète démarrée",
        "Analyse de vulnérabilités",
        "SBOM et provenance",
        "Signature",
        "Préproduction et vraie exécution",
        "Mêmes images promues",
      ],
    },
    industries: {
      title: "Pensé pour les secteurs qui vivent de documents",
      items: [
        {
          title: "Banque",
          body: "Ouverture de compte, crédit, conformité.",
          docs: ["Relevés bancaires", "Justificatifs de revenus", "RIB", "Factures pro forma"],
          page: "banks",
        },
        {
          title: "Assurance",
          body: "Souscription et gestion des sinistres.",
          docs: [
            "Constats amiables",
            "Devis et factures garage",
            "Rapports d'expertise",
            "Attestations",
          ],
          page: "insurance",
        },
        {
          title: "Télécom",
          body: "Souscription entreprise, achats, conformité.",
          docs: [
            "Contrats d'abonnement",
            "Bons de commande",
            "Factures fournisseurs",
            "Pièces justificatives",
          ],
          page: "telecom",
        },
      ],
    },
    faq: {
      title: "Questions fréquentes",
      items: [
        {
          q: "Où sont stockés nos documents ?",
          a: "Sur vos serveurs. Repody s'installe dans votre infrastructure (un serveur ou un cluster Kubernetes) avec sa base PostgreSQL, son stockage objet compatible S3 et son serveur de modèle. Aucun document n'est envoyé à un service tiers.",
        },
        {
          q: "Faut-il un GPU ?",
          a: "Le modèle d'extraction tourne au mieux sur un GPU de 24 Go (NVIDIA L4 ou A10). Vous pouvez utiliser le vôtre, ou un GPU serverless qui ne coûte que pendant les exécutions et démarre en quelques secondes.",
        },
        {
          q: "Quels documents et quelles langues ?",
          a: "PDF, PNG, JPEG et WebP, 20 fichiers par exécution. Un document est lu en une seule passe, jusqu'à une quarantaine de pages A4 ; un document plus long est refusé tout de suite, avec la raison, avant toute facturation. Le modèle lit le français, l'anglais et les principales langues européennes ; l'interface est en français et en anglais.",
        },
        {
          q: "Quelle précision attendre ?",
          a: "Elle dépend de vos documents. Nous la mesurons avec vous pendant un pilote, sur vos propres fichiers et vos propres règles, avant toute décision.",
        },
        {
          q: "Peut-on revendre Repody sous notre marque ?",
          a: "Oui. Le nom, le logo et les couleurs se règlent par déploiement, sans modifier le code. La licence couvre l'usage en marque blanche.",
        },
        {
          q: "Comment l'intégrer à nos systèmes ?",
          a: "Par une API REST : un appel envoie les fichiers et renvoie un identifiant d'exécution, un second lit le résultat. Les exemples cURL, Python et JavaScript sont générés dans l'interface pour chaque workflow.",
        },
        {
          q: "Qui peut voir quoi ?",
          a: "Les accès passent par votre fournisseur d'identité. Quatre rôles (lecteur, opérateur, administrateur, administrateur de la plateforme) donnent des permissions précises sur les workflows et les exécutions.",
        },
        {
          q: "Que se passe-t-il si un serveur tombe pendant une exécution ?",
          a: "L'exécution reprend d'elle-même : un worker qui s'arrête la passe à un autre, un redémarrage de la base est réessayé, et elle n'est facturée qu'une fois. Chaque base et chaque document sont sauvegardés, chiffrés, chaque nuit vers un stockage objet, et la restauration est testée.",
        },
        {
          q: "Peut-on proposer Repody à nos propres clients ?",
          a: "Oui. Une installation sert plusieurs entreprises clientes, chacune ne voyant que son propre travail. Vous invitez leurs utilisateurs, leur accordez des crédits (un par page lue) et suivez leur consommation et le coût GPU depuis l'espace d'administration.",
        },
        {
          q: "Comment se passent les mises à jour ?",
          a: "Chaque version est construite une fois, analysée, signée et lancée sur une copie de préproduction avec un vrai document avant d'arriver en production. Vous choisissez la version à déployer ; sa signature est vérifiée avant l'installation, et revenir en arrière tient en une commande.",
        },
      ],
    },
    cta: {
      title: "Voyez Repody sur vos propres documents",
      lead: "Une démonstration de 30 minutes, puis un pilote sur vos fichiers et vos règles.",
    },
  },

  platform: {
    meta: {
      title: "Plateforme : extraction, règles, rapports et API",
      description:
        "Constructeur de workflows, 24 types de champs, règles sur un ou deux documents, rapports détaillés à côté des pages, API REST avec clés par workflow, salle de contrôle, et entreprises clientes avec leurs utilisateurs et leurs crédits.",
    },
    hero: {
      title: "Toute la plateforme, écran par écran",
      lead: "Repody couvre la chaîne entière : décrire les documents, écrire les règles, exécuter, examiner, intégrer. Chaque capacité ci-dessous existe dans le produit aujourd'hui.",
    },
    sections: [
      {
        id: "builder",
        title: "Constructeur de workflows",
        lead: "Un workflow décrit les documents reçus, les champs à y lire et les règles à vérifier. Il se construit sans code, en trois étapes.",
        shot: "builder-documents",
        points: [
          {
            title: "Documents et champs",
            body: "Chaque document a un nom et sa liste de champs. Les cellules se modifient sur place, comme du texte.",
          },
          {
            title: "24 types de champs",
            body: "Texte exact ou reformulé, nombres, entiers, montants, dates, heures, durées, booléens, IBAN, BIC, adresses e-mail, téléphones, pays, langues, URL, codes d'unité. Chaque type simple existe aussi en liste.",
          },
          {
            title: "Structures",
            body: "Listes de valeurs, choix parmi une liste (enum et multi-enum), objets imbriqués et tableaux de lignes avec leurs colonnes.",
          },
          {
            title: "Instructions au modèle",
            body: "Des consignes propres à chaque document, en plus de la description de chaque champ.",
          },
          {
            title: "Des exemples qui instruisent",
            body: "Jusqu'à cinq exemples par document, une entrée et la réponse attendue, montrent au modèle vos mises en page et vos conventions.",
          },
          {
            title: "Transcription complète",
            body: "Un document sans champs est transcrit en entier en Markdown, tableaux compris, et conservé avec le rapport.",
          },
          {
            title: "Import de modèles JSON",
            body: "Collez un modèle JSON existant : champs, types et structures sont créés d'un coup.",
          },
          {
            title: "Brouillon et publication",
            body: "Le workflow s'enregistre en brouillon ; la publication crée sa clé d'API. Chaque exécution garde la définition utilisée.",
          },
        ],
      },
      {
        id: "rules",
        title: "Règles métier",
        lead: "Une règle dit ce qui doit être vrai. Elle se lit comme une phrase : sur ces documents, respectée si, en cas d'échec.",
        shot: "builder-claim",
        points: [
          {
            title: "Dix opérateurs",
            body: "Égal, différent, supérieur, supérieur ou égal, inférieur, inférieur ou égal, dans une liste, hors d'une liste, présent, vide.",
          },
          {
            title: "Calculs",
            body: "Additionner, soustraire, multiplier ou diviser deux champs numériques avant de comparer : « HT + TVA = TTC ».",
          },
          {
            title: "Agrégats de tableaux",
            body: "Somme des lignes, somme des lignes filtrées, nombre de lignes filtrées : pour rapprocher un total de son détail.",
          },
          {
            title: "Un ou deux documents",
            body: "Une règle contrôle un document, ou compare deux documents d'un même dossier : constat et facture, contrat et bon de commande.",
          },
          {
            title: "Rejeter ou signaler",
            body: "Un échec rejette l'exécution, ou la signale pour examen humain. Une règle de rejet qui ne peut pas être vérifiée, faute de valeur lue, envoie l'exécution en examen.",
          },
          {
            title: "Vérifiées pendant l'écriture",
            body: "Chaque condition affiche le contrôle exact que l'API exécutera, et les erreurs apparaissent avant la publication.",
          },
        ],
      },
      {
        id: "runs",
        title: "Exécutions et suivi en direct",
        lead: "Une exécution traite les fichiers envoyés : extraction, contrôle des règles, rapport. Vous la voyez avancer étape par étape.",
        shot: "builder-publish",
        points: [
          {
            title: "Tests depuis le constructeur",
            body: "Déposez un fichier par document et lancez le workflow tel qu'il est à l'écran, sans le publier.",
          },
          {
            title: "Chronologie en direct",
            body: "File d'attente et position, démarrage du modèle, extraction de chaque document, règles, enregistrement : chaque étape avec sa durée.",
          },
          {
            title: "Démarrage du GPU visible",
            body: "Quand le modèle était en veille, l'étape le dit et indique la durée habituelle, au lieu d'une attente muette.",
          },
          {
            title: "Documents en parallèle",
            body: "Les documents d'une exécution sont extraits en même temps, dans la limite fixée pour le serveur de modèle.",
          },
          {
            title: "Limites claires",
            body: "20 fichiers et 25 Mo par fichier par défaut, le type vérifié d'après le contenu (PDF, PNG, JPEG, WebP), et un document trop long pour le modèle refusé tout de suite, avec la raison, avant toute facturation.",
          },
          {
            title: "Des exécutions qui reprennent",
            body: "Un worker qui s'arrête ou une base qui redémarre en pleine exécution : l'exécution reprend d'elle-même et n'est facturée qu'une fois. Une exécution perdue par la file est mise en échec et ses crédits libérés.",
          },
        ],
      },
      {
        id: "reports",
        title: "Rapports",
        lead: "Le rapport dit ce qui s'est passé en une ligne, puis montre chaque valeur et chaque règle.",
        shot: "report",
        points: [
          {
            title: "Un verdict lisible",
            body: "Conforme, à examiner ou rejeté, avec le nombre de règles respectées, de champs extraits, la durée et la source.",
          },
          {
            title: "Champs en registre",
            body: "Chaque champ sur sa ligne avec sa marque : trouvé, introuvable, en échec. La règle en cause est écrite à côté de la valeur.",
          },
          {
            title: "Règles détaillées",
            body: "Échecs d'abord, avec leur gravité, l'expression évaluée et l'explication.",
          },
          {
            title: "Sortie brute du modèle",
            body: "Le JSON renvoyé par le modèle, en aperçu ou en source, à copier.",
          },
          {
            title: "Impression et export",
            body: "Impression propre en PDF et export CSV de chaque rapport ou de toute une liste filtrée.",
          },
          {
            title: "Pages tronquées signalées",
            body: "Si un document dépasse la limite de pages, le rapport indique combien ont été lues.",
          },
          {
            title: "Les pages à côté des valeurs",
            body: "Les pages de chaque document s'affichent à côté de ses champs, rendues pour l'écran : une valeur se vérifie contre sa page d'un coup d'œil.",
          },
          {
            title: "Où regarder",
            body: "Un champ qu'une règle n'a pas pu vérifier est signalé, et la liste nomme la règle : la personne qui relit sait où regarder.",
          },
        ],
      },
      {
        id: "api",
        title: "API d'intégration",
        lead: "Vos systèmes envoient les documents et lisent les verdicts par une API REST. L'interface génère les exemples pour chaque workflow.",
        shot: null,
        points: [
          {
            title: "Deux appels",
            body: "POST envoie les fichiers et répond 202 avec l'identifiant de l'exécution ; GET lit son état puis son rapport.",
          },
          {
            title: "Une clé par workflow",
            body: "La clé ne donne accès qu'à son workflow et à ses exécutions, rien d'autre.",
          },
          {
            title: "Exemples prêts",
            body: "cURL, Python et JavaScript, avec l'adresse et la clé du workflow, copiables en un clic.",
          },
          {
            title: "Débit maîtrisé",
            body: "Par client, les exécutions par minute et en cours sont plafonnées : les suivantes attendent leur tour et les clients alternent. Au-delà de la profondeur de la file, l'API répond 503 avec Retry-After.",
          },
          {
            title: "Contrat typé",
            body: "Spécification OpenAPI générée depuis le code et vérifiée en intégration continue ; l'interface en dérive ses types.",
          },
          {
            title: "Essai depuis l'interface",
            body: "Lancez une exécution avec la vraie clé, exactement comme un client de l'API.",
          },
          {
            title: "Nouvelles tentatives sans risque",
            body: "Avec l'en-tête Idempotency-Key, une requête renvoyée rend l'exécution déjà lancée : une coupure réseau ne fait jamais traiter ni facturer deux fois un document.",
          },
          {
            title: "Refus explicites",
            body: "402 quand le compte n'a plus de crédits, 413 pour un fichier trop gros, 422 avec la raison pour un fichier ou une demande que le modèle ne peut pas lire.",
          },
        ],
      },
      {
        id: "overview",
        title: "Vue d'ensemble",
        lead: "La page d'accueil commence par ce qui demande une personne.",
        shot: "overview",
        points: [
          {
            title: "À examiner",
            body: "Les exécutions dont des règles ont échoué ou n'ont pas pu être vérifiées, les plus anciennes d'abord.",
          },
          {
            title: "La semaine en chiffres",
            body: "Exécutions, taux de réussite et échecs de règles, comparés à la semaine précédente.",
          },
          { title: "Volume par jour", body: "Chaque jour mène à ses exécutions." },
          {
            title: "État de la file",
            body: "Exécutions en cours et en attente sur toute la plateforme : une attente s'explique d'elle-même.",
          },
        ],
      },
      {
        id: "operations",
        title: "Salle de contrôle",
        lead: "Ce qui tourne, ce qui a échoué et à quelle vitesse : la page que les opérateurs gardent ouverte.",
        shot: null,
        points: [
          {
            title: "Exécutions en cours",
            body: "Chaque exécution en attente ou en cours, avec son étape en direct, ses fichiers et depuis combien de temps elle tourne.",
          },
          {
            title: "Arrêter une exécution",
            body: "Annulez une exécution depuis la liste : sa tâche est arrêtée et elle est soldée comme tout échec.",
          },
          {
            title: "Ce qui a échoué",
            body: "Les échecs des dernières 24 heures, chacun avec sa raison en clair.",
          },
          {
            title: "Débit",
            body: "Exécutions terminées et en échec, heure par heure, sur les dernières 24 heures.",
          },
          {
            title: "Durées",
            body: "Durée médiane et au 95e centile des exécutions, et la part du modèle.",
          },
          {
            title: "Toute la file",
            body: "Exécutions en attente et en cours sur toute la plateforme : une attente s'explique d'elle-même.",
          },
        ],
      },
      {
        id: "admin",
        title: "Clients, utilisateurs et crédits",
        lead: "Une installation sert plusieurs entreprises clientes. Chacune ne voit que son propre travail, et le paie avec les crédits que vous lui accordez.",
        shot: null,
        points: [
          {
            title: "Entreprises clientes",
            body: "Un client est un groupe de votre fournisseur d'identité. Ses utilisateurs ne voient que ses workflows, exécutions et audits ; un utilisateur hors de tout client ne voit rien.",
          },
          {
            title: "Utilisateurs et rôles",
            body: "Invitez par e-mail, choisissez le rôle, réinitialisez un mot de passe, désactivez ou supprimez un compte, depuis l'espace d'administration.",
          },
          {
            title: "Des crédits à la page",
            body: "Un crédit correspond à une page lue par le modèle, plus des frais par exécution. Une exécution réserve son estimation au départ et paie les pages réellement lues.",
          },
          {
            title: "Jamais de facture surprise",
            body: "Une exécution que le compte ne peut pas payer est refusée avant tout envoi, et l'utilisateur peut demander des crédits.",
          },
          {
            title: "Consommation et coûts",
            body: "Crédits, exécutions et pages par client, et une estimation du coût GPU, sur la période voulue.",
          },
          {
            title: "Demandes d'accès",
            body: "Les prospects demandent un compte depuis votre site public, protégé par Turnstile ; vous les rattachez à un client en une étape.",
          },
          {
            title: "Un journal d'audit",
            body: "Chaque action d'administration, qui l'a faite, sur quel client et quand, conservée durablement.",
          },
          {
            title: "Exemples partagés",
            body: "Des workflows d'exemple que chaque client peut lire et dupliquer, sans jamais les modifier.",
          },
        ],
      },
      {
        id: "experience",
        title: "Une interface pour le travail quotidien",
        lead: "Chaque détail sert des opérateurs qui passent leur journée dans l'outil.",
        shot: "workflows",
        points: [
          {
            title: "Palette de commandes",
            body: "⌘K ou / pour aller à n'importe quel workflow, exécution récente ou page, et créer un workflow.",
          },
          {
            title: "Deux langues",
            body: "Français et anglais, dates et nombres au format local, fuseau horaire du lecteur.",
          },
          {
            title: "Clair, sombre ou système",
            body: "Le thème suit votre choix ou celui de votre poste.",
          },
          {
            title: "Pensée pour le clavier",
            body: "Navigation au clavier, focus visible, contrastes vérifiés, mouvements réduits si votre système le demande.",
          },
          { title: "Mobile", body: "Toutes les pages restent utilisables sur un téléphone." },
          {
            title: "Suppression groupée",
            body: "Sélectionnez plusieurs workflows et archivez-les ensemble, avec confirmation.",
          },
        ],
      },
    ],
    typesTitle: "Les 24 types de champs",
    operatorsTitle: "Opérateurs et calculs",
    operatorsLead:
      "Ce qu'une condition peut vérifier, et ce qu'elle peut calculer avant de comparer.",
    operators: [
      { symbol: "==", label: "égal à" },
      { symbol: "!=", label: "différent de" },
      { symbol: ">", label: "supérieur à" },
      { symbol: ">=", label: "supérieur ou égal à" },
      { symbol: "<", label: "inférieur à" },
      { symbol: "<=", label: "inférieur ou égal à" },
      { symbol: "IN", label: "dans la liste" },
      { symbol: "NOT_IN", label: "hors de la liste" },
      { symbol: "EXISTS", label: "présent" },
      { symbol: "IS_EMPTY", label: "vide" },
    ],
    computeTitle: "Calculs",
    compute: [
      { symbol: "+ − × ÷", label: "entre deux champs numériques" },
      { symbol: "sum_rows", label: "somme d'une colonne de tableau" },
      { symbol: "sum_rows_where", label: "somme des lignes qui remplissent une condition" },
      { symbol: "count_rows_where", label: "nombre de lignes qui remplissent une condition" },
    ],
    listNote: "Chaque type simple existe aussi en liste : plusieurs dates, plusieurs montants.",
    apiExample: {
      title: "Deux appels",
      send: "Envoyer les fichiers",
      read: "Lire le verdict",
    },
  },

  security: {
    meta: {
      title: "Sécurité : identité, souveraineté, chaîne logicielle",
      description:
        "OIDC Keycloak avec double authentification pour les administrateurs, rôles et permissions, clés d'API hachées, conteneurs durcis, aucun port ouvert, images signées et vérifiées : la sécurité de Repody en détail.",
    },
    hero: {
      title: "La sécurité n'est pas une option du produit",
      lead: "Repody traite des documents sensibles : relevés, contrats, pièces d'identité. Chaque couche est conçue pour que ces données restent chez vous et ne soient vues que par les bonnes personnes.",
    },
    posture:
      "Repody vous donne les moyens techniques de respecter vos obligations (loi 09-08 et CNDP, exigences de Bank Al-Maghrib, de l'ACAPS ou de l'ANRT) : données hébergées chez vous, accès contrôlés par votre fournisseur d'identité, traçabilité. La conformité de votre traitement reste de votre responsabilité ; Repody n'est pas un produit certifié par ces autorités.",
    groups: [
      {
        id: "identity",
        title: "Identité et accès",
        points: [
          {
            title: "OpenID Connect",
            body: "Connexion par Keycloak (ou votre fournisseur OIDC), flux d'autorisation avec PKCE S256.",
          },
          {
            title: "Double authentification",
            body: "TOTP exigé pour le compte administrateur dès la première connexion, mot de passe à changer immédiatement.",
          },
          {
            title: "Quatre rôles, six permissions",
            body: "Lecteur, opérateur, administrateur et administrateur de la plateforme ; lire, modifier, supprimer les workflows, lire et lancer les exécutions, voir les métriques.",
          },
          {
            title: "Vérification à chaque appel",
            body: "Chaque requête d'API vérifie le jeton (émetteur, audience, signature) et la permission demandée.",
          },
          {
            title: "Sessions renouvelées en sécurité",
            body: "Les jetons sont rafraîchis côté serveur ; des requêtes simultanées partagent un seul rafraîchissement.",
          },
          {
            title: "Console d'administration isolée",
            body: "La console Keycloak est sur son propre nom d'hôte, derrière une authentification Cloudflare Access ; le domaine public n'expose que le royaume de l'application.",
          },
          {
            title: "Connexions tracées",
            body: "Connexions, échecs et modifications d'administration sont conservés 90 jours ; un compte se verrouille après 10 tentatives échouées.",
          },
          {
            title: "Entreprises cloisonnées",
            body: "Chaque entreprise cliente ne voit que son propre travail ; un utilisateur hors de toute entreprise n'a aucun accès.",
          },
        ],
      },
      {
        id: "application",
        title: "Application",
        points: [
          {
            title: "Clés d'API par workflow",
            body: "Affichées une seule fois, stockées en empreinte SHA-256, comparées en temps constant ; elles ne servent qu'à lancer et lire les exécutions de leur workflow.",
          },
          {
            title: "Fichiers contrôlés",
            body: "Nombre, taille et type des fichiers vérifiés à l'entrée, le type lu dans le contenu, jamais dans le nom ; stockage objet privé.",
          },
          {
            title: "Débit et file maîtrisés",
            body: "Par client, les exécutions par minute et en cours sont plafonnées et les suivantes attendent leur tour ; une file plafonnée répond 503 avec Retry-After.",
          },
          {
            title: "Durée de conservation",
            body: "Les exécutions plus anciennes que la durée choisie sont purgées automatiquement, par lots.",
          },
          {
            title: "Journaux sans secrets",
            body: "Journaux structurés en JSON, sans jetons ni mots de passe.",
          },
          {
            title: "Erreurs sans fuite",
            body: "Les erreurs renvoyées aux clients décrivent le problème, jamais l'intérieur du système.",
          },
          {
            title: "Exports sûrs",
            body: "Une cellule CSV qu'un tableur exécuterait comme une formule est neutralisée.",
          },
          {
            title: "Un formulaire public protégé",
            body: "Les demandes d'accès passent un contrôle Cloudflare Turnstile et une limite par réseau ; seule une empreinte à sens unique de l'adresse est conservée.",
          },
        ],
      },
      {
        id: "infrastructure",
        title: "Infrastructure",
        points: [
          {
            title: "Conteneurs durcis",
            body: "Utilisateurs non root, système de fichiers racine en lecture seule, aucune élévation de privilèges, mémoire plafonnée pour chaque service.",
          },
          {
            title: "Aucun port public",
            body: "Le trafic web arrive par un tunnel Cloudflare sortant ; le pare-feu n'accepte que le réseau privé d'administration.",
          },
          {
            title: "Accès d'administration à identité vérifiée",
            body: "SSH par Tailscale : accès accordés par politique, testés automatiquement, sans clé partagée.",
          },
          {
            title: "Déploiement sans secret permanent",
            body: "La chaîne de déploiement s'authentifie par fédération d'identité (OIDC), pas par une clé stockée.",
          },
          {
            title: "Kubernetes",
            body: "Politiques réseau, budgets de disponibilité, secrets externes (External Secrets avec Vault).",
          },
          {
            title: "Mises à jour du système",
            body: "Mises à jour de sécurité automatiques sur le serveur, images de base suivies et mises à jour.",
          },
          {
            title: "Sauvegardes hors du serveur",
            body: "Chaque base et chaque document, chiffrés chaque nuit vers un stockage objet ; la restauration est testée sur les vraies sauvegardes.",
          },
          {
            title: "La préproduction d'abord",
            body: "Chaque changement tourne sur une pile de préproduction séparée, avec un vrai document, avant qu'une version n'arrive en production.",
          },
        ],
      },
      {
        id: "supply-chain",
        title: "Chaîne logicielle",
        points: [
          {
            title: "Analyse de vulnérabilités",
            body: "Trivy analyse le code et chaque image ; une faille haute ou critique bloque la version.",
          },
          {
            title: "SBOM et provenance",
            body: "Chaque image publiée porte sa nomenclature logicielle et son attestation de provenance.",
          },
          {
            title: "Signature Sigstore",
            body: "Les images sont signées sans clé (cosign, identité OIDC) et la signature est vérifiée avant chaque déploiement et chaque promotion.",
          },
          {
            title: "Dépendances épinglées",
            body: "Images par empreinte, actions de CI par commit ; Dependabot propose chaque mise à jour après quelques jours de délai.",
          },
          {
            title: "Analyses hebdomadaires",
            body: "Le code publié est réanalysé chaque semaine ; une alerte acceptée porte sa raison et une date de fin.",
          },
          {
            title: "Versions immuables",
            body: "Une version promeut, par empreinte, les images exactes testées en préproduction ; rien n'est reconstruit.",
          },
        ],
      },
    ],
  },

  architecture: {
    meta: {
      title: "Architecture : composants, modèle, montée en charge",
      description:
        "Next.js, FastAPI, workers Hatchet, PostgreSQL, stockage S3, Keycloak et un serveur de modèle vLLM externe : l'architecture de Repody et sa montée en charge.",
    },
    hero: {
      title: "Une architecture simple, faite pour durer",
      lead: "Des composants standards, chacun à sa place : une interface, une API, des workers, une base, un stockage, un fournisseur d'identité et un serveur de modèle que vous contrôlez.",
    },
    diagram: {
      user: "Opérateurs",
      client: "Vos systèmes",
      web: "Interface web",
      webTech: "Next.js",
      api: "API",
      apiTech: "FastAPI",
      workers: "Workers",
      workersTech: "Hatchet",
      db: "Base de données",
      dbTech: "PostgreSQL",
      storage: "Stockage objet",
      storageTech: "Compatible S3",
      idp: "Identité",
      idpTech: "Keycloak · OIDC",
      model: "Serveur de modèle",
      modelTech: "vLLM · Repody VLM",
      userTech: "Navigateur",
      clientTech: "REST · clé d'API",
    },
    groups: [
      {
        id: "components",
        title: "Composants",
        points: [
          {
            title: "Interface web",
            body: "Next.js rendu côté serveur ; toutes les requêtes passent par un proxy qui ajoute le jeton de l'utilisateur.",
          },
          {
            title: "API",
            body: "FastAPI, typée de bout en bout, couches séparées et vérifiées (API, application, extraction, règles, infrastructure).",
          },
          {
            title: "Workers",
            body: "Hatchet met chaque exécution en file : l'API répond tout de suite, les workers traitent les exécutions en arrière-plan.",
          },
          {
            title: "PostgreSQL",
            body: "Workflows, exécutions, champs et résultats de règles ; migrations Alembic appliquées par un service dédié avant le démarrage.",
          },
          {
            title: "Stockage objet",
            body: "Les fichiers reçus, dans un stockage compatible S3 (SeaweedFS fourni, ou le vôtre).",
          },
          {
            title: "Keycloak",
            body: "Image optimisée, royaume de production intégré, paramètres injectés au démarrage.",
          },
        ],
      },
      {
        id: "model",
        title: "Le modèle d'extraction",
        points: [
          {
            title: "Repody VLM",
            body: "Modèle de vision spécialisé dans l'extraction structurée : il reçoit l'image des pages et un modèle JSON, et renvoie les champs.",
          },
          {
            title: "Servi par vLLM",
            body: "API compatible OpenAI, décodage spéculatif, poids complets ; le serveur de modèle reste hors du produit, sur votre GPU ou un GPU managé.",
          },
          {
            title: "Chaque page assez nette, lue deux fois",
            body: "Chaque page arrive au modèle à la résolution qu'il attend, et les petites pages et les photos à 3 mégapixels au moins. Chaque document est relu une seconde fois à une autre taille : une valeur sur laquelle les deux lectures divergent part en revue au lieu de passer. Un document est lu en une requête, une quarantaine de pages A4 au plus ; un document plus long est refusé, avec la raison, avant de partir.",
          },
          {
            title: "GPU à la demande",
            body: "En mode managé, le GPU s'éteint après dix minutes sans requête et repart d'un instantané mémoire en quelques secondes ; un seul conteneur au plus.",
          },
          {
            title: "Démarrage annoncé",
            body: "Avant d'extraire, le worker vérifie si le modèle est éveillé ; sinon l'exécution affiche « Démarrage du GPU ».",
          },
          {
            title: "Mesuré",
            body: "Sur un GPU de 24 Go : environ 1,5 s pour une facture d'une page, 6 à 10 s pour cinq pages, 30 à 45 s pour vingt ; un démarrage depuis l'instantané mémoire prend environ 15 s.",
          },
        ],
      },
      {
        id: "scale",
        title: "Montée en charge et résilience",
        points: [
          {
            title: "Workers indépendants",
            body: "On ajoute des workers sans toucher à l'API ; sur Kubernetes, l'API et les workers montent en charge automatiquement (HPA).",
          },
          {
            title: "Prise en charge atomique",
            body: "Une exécution n'est traitée qu'une fois, même si plusieurs workers la reçoivent.",
          },
          {
            title: "Reprise sans intervention",
            body: "Un worker qui s'arrête passe son exécution à un autre, qui la reprend ; un redémarrage de la base est réessayé ; une exécution qui dépasse son délai, ou perdue par la file, est mise en échec avec la raison et ses crédits soldés.",
          },
          {
            title: "Admission contrôlée",
            body: "Au-delà de la profondeur de file choisie, l'API refuse proprement (503) au lieu de s'effondrer.",
          },
          {
            title: "Concurrence bornée",
            body: "Les requêtes au modèle et les pages rendues en mémoire sont plafonnées : ni le GPU ni un worker ne sont saturés, et les clients alternent pour qu'un envoi massif n'accapare pas tous les workers.",
          },
          {
            title: "PostgreSQL en haute disponibilité",
            body: "Sur Kubernetes : CloudNativePG avec pooler de connexions et sauvegardes planifiées.",
          },
        ],
      },
      {
        id: "observability",
        title: "Observabilité",
        points: [
          {
            title: "Journaux structurés",
            body: "JSON, chaque ligne avec l'identifiant de l'exécution concernée.",
          },
          {
            title: "Traces",
            body: "OpenTelemetry de l'API aux workers, collectées par un OpenTelemetry Collector.",
          },
          {
            title: "Journaux, erreurs et alertes",
            body: "Journaux consultables dans Grafana (Loki, Alloy), erreurs avec leur pile d'appels dans Bugsink, alertes sur les erreurs et sur une sauvegarde manquée, le tout sur vos serveurs.",
          },
          {
            title: "Statistiques des requêtes",
            body: "Chaque requête à la base est mesurée (pg_stat_statements), et les plus lentes sont journalisées sans leurs valeurs, qui peuvent être des données clientes.",
          },
          {
            title: "Sondes de santé",
            body: "Vivacité et disponibilité distinctes, pour que l'orchestrateur sache quand redémarrer et quand attendre.",
          },
          {
            title: "Vue d'exploitation",
            body: "État de la file en direct dans l'interface ; exécutions, workers et planifications dans le tableau de bord de la file.",
          },
        ],
      },
    ],
    flow: {
      title: "La vie d'une exécution",
      lead: "Du fichier reçu au verdict, ce qui se passe à chaque étape.",
      steps: [
        {
          title: "Réception",
          body: "L'API vérifie la clé ou le jeton, puis le nombre, la taille et le type des fichiers, les range dans le stockage objet et répond 202.",
        },
        {
          title: "File d'attente",
          body: "L'exécution entre dans la file Hatchet. Si la file est pleine, l'API répond 503 avec Retry-After.",
        },
        {
          title: "Prise en charge",
          body: "Un worker la réserve de façon atomique, vérifie que le modèle est éveillé et le démarre si besoin.",
        },
        {
          title: "Extraction",
          body: "Chaque page devient une image à 170 DPI, ou 3 mégapixels pour les petites pages et les photos ; les documents partent en parallèle au modèle avec leur modèle JSON, et chacun est relu une seconde fois à une autre taille.",
        },
        {
          title: "Règles",
          body: "Le moteur évalue chaque règle sur les valeurs extraites, dans un document ou entre deux.",
        },
        {
          title: "Rapport",
          body: "Champs, règles et verdict sont enregistrés dans PostgreSQL ; l'interface et l'API les lisent.",
        },
      ],
    },
    decisions: {
      title: "Des décisions écrites",
      lead: "Chaque choix d'architecture a son document dans le dépôt, avec le contexte et les alternatives écartées.",
      items: [
        {
          adr: "011",
          title: "Exécutions asynchrones avec Hatchet",
          body: "L'API répond tout de suite ; Hatchet confie chaque exécution à un worker et fait respecter ses délais.",
        },
        {
          adr: "004",
          title: "Packaging cloud et Kubernetes",
          body: "Un chart Helm et des manifestes pour les clusters des clients.",
        },
        {
          adr: "005",
          title: "Inférence externe",
          body: "Le serveur de modèle reste hors du chart : votre GPU ou un GPU managé.",
        },
        {
          adr: "009",
          title: "Un backend simple",
          body: "Une définition, une file, un chemin d'envoi des fichiers.",
        },
        {
          adr: "010",
          title: "Cycles de vie explicites",
          body: "Chaque état d'un workflow et d'une exécution, et ses transitions, sont nommés.",
        },
        {
          adr: "012",
          title: "Le service hébergé sur un serveur",
          body: "Docker Compose sur un VPS avec une copie de préproduction à côté et le modèle sur un GPU managé ; Kubernetes reste pour les installations clientes.",
        },
      ],
    },
  },

  deployment: {
    meta: {
      title: "Déploiement on-premise et marque blanche",
      description:
        "Repody s'installe sur un serveur avec Docker Compose ou sur Kubernetes et OpenShift avec Helm, avec votre GPU ou un GPU managé, sous votre marque.",
    },
    hero: {
      title: "Chez vous, à votre nom",
      lead: "Repody est vendu sous licence et installé dans votre infrastructure. Vous gardez les données, les accès, les versions et la marque.",
    },
    options: [
      {
        id: "server",
        title: "Un serveur",
        body: "Pour démarrer vite ou pour un volume modéré.",
        points: [
          "Docker Compose : interface, API, workers, PostgreSQL, Hatchet, stockage, Keycloak, tunnel",
          "Chaque service avec son contrôle de santé et sa limite de mémoire",
          "Migrations appliquées automatiquement avant le démarrage",
          "Déploiement par la chaîne après une copie de préproduction, signature vérifiée, retour arrière en une commande",
          "Journaux, suivi des erreurs et alertes sur le même serveur, derrière votre contrôle d'accès",
          "Sauvegardes chiffrées chaque nuit vers un stockage objet, restauration testée",
        ],
      },
      {
        id: "kubernetes",
        title: "Kubernetes ou OpenShift",
        body: "Pour la haute disponibilité et les gros volumes.",
        points: [
          "Chart Helm : API, interface, workers, tâche de migration, ingress",
          "Mise à l'échelle automatique, budgets de disponibilité, politiques réseau",
          "CloudNativePG avec pooler et sauvegardes planifiées",
          "Secrets externes avec Vault, application Argo CD fournie",
        ],
      },
      {
        id: "gpu",
        title: "Le modèle, où vous voulez",
        body: "Le serveur de modèle est séparé du produit.",
        points: [
          "Votre GPU : vLLM ou tout serveur compatible OpenAI",
          "GPU managé serverless : facturé à la seconde, éteint sans requête",
          "Un seul réglage d'adresse et de clé côté Repody",
          "Le produit fonctionne de la même façon dans les deux cas",
        ],
      },
    ],
    brand: {
      title: "Marque blanche",
      lead: "Six variables par déploiement suffisent. Le moteur de thème calcule toutes les teintes de l'interface à partir de vos couleurs, en clair et en sombre, et vérifie le contraste.",
      vars: [
        { name: "REPODY_BRAND_NAME", body: "Le nom du produit affiché partout" },
        {
          name: "REPODY_BRAND_LOGO_URL",
          body: "Votre logo, dans la barre latérale et la page de connexion",
        },
        { name: "REPODY_BRAND_BASE", body: "La couleur neutre qui teinte surfaces et textes" },
        {
          name: "REPODY_BRAND_ACCENT",
          body: "La couleur des actions, du focus et de la sélection",
        },
        { name: "REPODY_BRAND_CONTRAST", body: "De 30 (doux) à 100 (net)" },
        { name: "REPODY_BRAND_RADIUS", body: "Le rayon des coins, de 0 à 12 px" },
      ],
      guarantee:
        "Le texte reste lisible quelle que soit la couleur : le moteur vise le niveau AA des WCAG et assombrit un accent trop clair plutôt que de rendre un bouton illisible ; c'est testé automatiquement sur des marques très différentes.",
    },
    box: {
      title: "Ce qui est livré",
      items: [
        "Les images de l'interface, de l'API et de Keycloak, signées",
        "Le fichier Docker Compose de production et son modèle de configuration",
        "Le chart Helm et ses exemples de valeurs de production",
        "Les manifestes CloudNativePG, External Secrets et Argo CD",
        "La journalisation, le suivi des erreurs et les règles d'alerte, prêts à l'emploi (Loki, Alloy, Grafana, Bugsink)",
        "L'outil de sauvegarde chiffrée et de restauration (restic)",
        "Le serveur de modèle prêt à déployer",
        "La documentation d'installation, d'exploitation et de dépannage",
        "Les décisions d'architecture et les diagrammes de cycle de vie",
      ],
    },
    steps: {
      title: "Le chemin d'installation",
      items: [
        {
          title: "Préparer le serveur",
          body: "Docker depuis son dépôt officiel, mises à jour automatiques, utilisateur de déploiement.",
        },
        {
          title: "Relier le réseau",
          body: "Réseau privé d'administration, tunnel pour le trafic public, pare-feu fermé.",
        },
        {
          title: "Renseigner les secrets",
          body: "Un fichier .env : mots de passe, adresses, marque. Rien n'est écrit dans le code.",
        },
        {
          title: "Déployer une version",
          body: "La chaîne vérifie la signature, envoie la configuration, démarre et attend que tout soit sain.",
        },
        {
          title: "Première connexion",
          body: "L'administrateur change son mot de passe et active la double authentification.",
        },
      ],
    },
  },

  engineering: {
    meta: {
      title: "Ingénierie et DevSecOps",
      description:
        "Intégration continue complète, analyses de sécurité, SBOM, provenance, signature Sigstore et déploiement vérifié : comment Repody est construit, testé et livré.",
    },
    hero: {
      title: "Comment Repody est construit et livré",
      lead: "Le produit ne vaut que par la façon dont il change. Chaque modification traverse une chaîne de contrôles automatiques ; chaque version est construite, analysée, signée, vérifiée puis déployée.",
    },
    stages: [
      {
        id: "ci",
        title: "Intégration continue",
        lead: "À chaque modification, seules les parties touchées sont vérifiées, mais entièrement.",
        gates: [
          {
            name: "Détection des changements",
            detail: "Les tâches ne tournent que pour le code modifié.",
          },
          { name: "Ruff", detail: "Formatage et lint du backend Python." },
          { name: "Pyright", detail: "Typage statique strict du backend." },
          {
            name: "Contrats d'architecture",
            detail:
              "import-linter vérifie que chaque couche n'importe que ce qu'elle a le droit d'importer.",
          },
          {
            name: "Pytest",
            detail:
              "Tests unitaires et d'intégration sur un vrai PostgreSQL, migrations Alembic comprises.",
          },
          {
            name: "Contrat d'API",
            detail:
              "La spécification OpenAPI est régénérée et comparée ; les types de l'interface aussi.",
          },
          { name: "Biome et ESLint", detail: "Formatage et lint de l'interface." },
          { name: "TypeScript", detail: "Typage strict de l'interface." },
          { name: "Vitest", detail: "Tests de l'interface, dont le contraste du moteur de thème." },
          { name: "knip", detail: "Aucun fichier, export ou dépendance inutilisé." },
          {
            name: "Vérifications de déploiement",
            detail:
              "Chart Helm, kustomize, bake et Compose validés ; documentation et liens vérifiés.",
          },
          {
            name: "Build et démarrage",
            detail: "Les images sont construites et toute la pile démarre en conteneurs.",
          },
        ],
      },
      {
        id: "security",
        title: "Sécurité",
        lead: "Une chaîne dédiée analyse le code et les images.",
        gates: [
          { name: "Trivy, dépôt", detail: "Dépendances, secrets et configurations analysés." },
          { name: "Trivy, images", detail: "Chaque image construite est analysée." },
          {
            name: "Blocage",
            detail: "Une vulnérabilité haute ou critique fait échouer la chaîne.",
          },
          {
            name: "Chaque semaine",
            detail:
              "Les analyses repassent chaque semaine sur le code publié : une nouvelle vulnérabilité est trouvée sans attendre une modification.",
          },
          {
            name: "Exceptions datées",
            detail:
              "Une alerte acceptée porte sa raison et une date de fin ; passée cette date, la chaîne échoue de nouveau.",
          },
        ],
      },
      {
        id: "release",
        title: "Version",
        lead: "Chaque commit de master est construit une fois, signé et lancé en préproduction ; une étiquette de version promeut ces mêmes images en production.",
        gates: [
          {
            name: "Construit une fois",
            detail:
              "Les images ne sont construites et signées que pour un commit de master dont les tests sont passés.",
          },
          { name: "Docker Bake", detail: "Les trois images construites ensemble, avec cache." },
          { name: "SBOM et provenance", detail: "Attestations BuildKit attachées à chaque image." },
          {
            name: "Signature cosign",
            detail: "Signature sans clé, liée à l'identité OIDC de la chaîne.",
          },
          {
            name: "Valeurs Helm",
            detail: "Les empreintes publiées pour les déploiements Kubernetes.",
          },
          {
            name: "Promotion",
            detail:
              "Une étiquette de version vérifie la signature de master et ajoute la version aux mêmes empreintes : rien n'est reconstruit.",
          },
        ],
      },
      {
        id: "deploy",
        title: "Déploiement",
        lead: "Chaque version passe d'abord en préproduction, puis en production, vérifiée à chaque étape.",
        gates: [
          {
            name: "Environnement protégé",
            detail: "Le déploiement de production passe par un environnement GitHub dédié.",
          },
          {
            name: "Vérification des signatures",
            detail: "Les trois images sont vérifiées avant toute action.",
          },
          {
            name: "Réseau privé",
            detail:
              "La chaîne rejoint le réseau d'administration par fédération d'identité, sans clé stockée.",
          },
          {
            name: "Démarrage attendu",
            detail: "Docker Compose attend que chaque service soit sain, dix minutes au plus.",
          },
          {
            name: "Contrôle public",
            detail: "La chaîne vérifie que l'application répond depuis Internet.",
          },
          {
            name: "Sauvegarde d'abord",
            detail: "Chaque base de données est sauvegardée avant tout changement.",
          },
          {
            name: "Une vraie exécution",
            detail:
              "La chaîne fait passer un vrai document par l'extraction sur le GPU et vérifie le rapport, les crédits et le cloisonnement.",
          },
          {
            name: "Retour arrière",
            detail:
              "Redéployer la version précédente est la même commande, répétée en préproduction.",
          },
        ],
      },
    ],
    practices: {
      title: "Au quotidien",
      items: [
        {
          title: "Tout est typé",
          body: "Python et TypeScript stricts ; l'interface dérive ses types de l'API.",
        },
        {
          title: "Dépendances suivies",
          body: "Dependabot sur npm, Python, Docker, Compose et les actions, avec quelques jours de délai avant de proposer une version ; tout est épinglé.",
        },
        {
          title: "Documentation vérifiée",
          body: "Guides, commandes et liens contrôlés à chaque modification.",
        },
        {
          title: "Décisions écrites",
          body: "Les choix d'architecture ont leur document, avec le contexte et les alternatives.",
        },
        {
          title: "Environnement local complet",
          body: "Toute la plateforme démarre en une commande, observabilité comprise.",
        },
        {
          title: "Système de design",
          body: "Jetons, composants et règles d'interface documentés, appliqués partout.",
        },
        {
          title: "Exercices de panne",
          body: "Workers arrêtés net, base et file redémarrées en pleine exécution, retours arrière répétés : en préproduction, avec de vraies exécutions.",
        },
        {
          title: "Mesuré, pas supposé",
          body: "Requêtes chronométrées sur un demi-million d'exécutions ; mémoire et nombre réel de jetons du modèle mesurés sous charge.",
        },
      ],
    },
  },

  solutions: {
    banks: {
      meta: {
        title: "Banque : KYC, crédit et conformité documentaire",
        description:
          "Repody lit relevés bancaires, justificatifs de revenus et pièces de dossier, contrôle leur cohérence et signale ce qui doit être examiné, sur l'infrastructure de la banque.",
      },
      hero: {
        title: "Des dossiers bancaires contrôlés en minutes",
        lead: "Ouverture de compte, crédit, conformité : les mêmes pièces reviennent chaque jour. Repody en extrait les données, vérifie leur cohérence et laisse vos équipes se concentrer sur les cas qui le méritent.",
      },
      docs: [
        "Relevés bancaires",
        "Bulletins de paie et attestations de revenus",
        "RIB",
        "Avis d'imposition",
        "Factures et pro forma",
        "Statuts et registres de commerce",
      ],
      cases: [
        {
          title: "Ouverture de compte",
          body: "Titulaire, IBAN, période et soldes d'un relevé, comparés au formulaire d'ouverture.",
        },
        {
          title: "Instruction de crédit",
          body: "Revenus déclarés, bulletins de paie et relevés rapprochés ; un écart est signalé avant le comité.",
        },
        {
          title: "Contrôles de conformité",
          body: "Pièces manquantes, dates expirées, montants incohérents : chaque dossier passe par les mêmes règles.",
        },
      ],
      rules: [
        "Le relevé date de moins de trois mois",
        "Le titulaire du relevé correspond au client",
        "Le salaire du bulletin correspond aux virements du relevé",
        "L'IBAN est présent et valide",
      ],
      posture:
        "Les données bancaires restent dans le système d'information de la banque : Repody s'installe sur vos serveurs, derrière votre fournisseur d'identité.",
    },
    insurance: {
      meta: {
        title: "Assurance : sinistres et souscription",
        description:
          "Repody lit constats amiables, devis, factures et rapports d'expertise, croise les pièces d'un dossier sinistre et signale les incohérences, sur l'infrastructure de l'assureur.",
      },
      hero: {
        title: "Des dossiers sinistres cohérents avant d'être payés",
        lead: "Un dossier sinistre réunit plusieurs pièces qui doivent raconter la même histoire. Repody les lit toutes et vérifie qu'elles concordent.",
      },
      docs: [
        "Constats amiables",
        "Devis et factures de garage",
        "Rapports d'expertise",
        "Attestations d'assurance",
        "Cartes grises",
        "Factures médicales",
      ],
      cases: [
        {
          title: "Gestion des sinistres",
          body: "Le véhicule du constat est celui de la facture, les dates se suivent, les montants sont cohérents.",
        },
        {
          title: "Souscription",
          body: "Les données des pièces jointes alimentent le dossier sans ressaisie.",
        },
        {
          title: "Lutte contre la fraude",
          body: "Les écarts entre pièces sont signalés systématiquement, pas au hasard d'une relecture.",
        },
      ],
      rules: [
        "Même immatriculation sur le constat et la facture",
        "La facture est postérieure à la date du sinistre",
        "Le montant de la facture ne dépasse pas le devis",
        "L'attestation couvre la date du sinistre",
      ],
      posture:
        "Les dossiers des assurés restent chez l'assureur : Repody s'installe sur vos serveurs, avec vos rôles et votre fournisseur d'identité.",
    },
    telecom: {
      meta: {
        title: "Télécom : contrats, achats et pièces justificatives",
        description:
          "Repody lit contrats d'abonnement, bons de commande et factures fournisseurs, vérifie signatures, montants et identifiants d'entreprise, sur l'infrastructure de l'opérateur.",
      },
      hero: {
        title: "Des contrats et des achats vérifiés à l'échelle",
        lead: "Souscriptions entreprise, achats, dossiers réglementaires : des volumes élevés et des pièces très variées. Repody les traite au rythme de vos flux.",
      },
      docs: [
        "Contrats d'abonnement",
        "Bons de commande",
        "Factures fournisseurs",
        "Pièces justificatives d'entreprise",
        "Procès-verbaux de livraison",
        "Attestations",
      ],
      cases: [
        {
          title: "Souscription entreprise",
          body: "Raison sociale, ICE, offre et mensualité extraites du contrat ; contrat non signé rejeté.",
        },
        {
          title: "Comptes fournisseurs",
          body: "Facture, bon de commande et livraison rapprochés avant paiement.",
        },
        {
          title: "Dossiers réglementaires",
          body: "Pièces complètes et à jour, contrôlées selon les mêmes règles à chaque fois.",
        },
      ],
      rules: [
        "Le contrat porte une signature",
        "L'ICE est présent",
        "Le total de la facture égale celui du bon de commande",
        "La somme des lignes égale le total HT",
      ],
      posture:
        "Les données des abonnés et des fournisseurs restent chez l'opérateur : Repody s'installe sur vos serveurs.",
    },
    labels: {
      docs: "Documents traités",
      cases: "Cas d'usage",
      rules: "Exemples de règles",
      posture: "Vos données",
    },
  },

  contact: {
    meta: {
      title: "Demander un accès",
      description:
        "Un compte Repody avec des crédits pour l'essayer sur vos propres documents, puis un pilote.",
    },
    title: "Voyons Repody sur vos documents",
    lead: "Dites-nous quels documents vous traitez et ce que vous voulez contrôler. Nous revenons vers vous sous deux jours ouvrés.",
    form: {
      name: "Nom",
      email: "E-mail professionnel",
      company: "Entreprise",
      sector: "Secteur",
      sectors: ["Banque", "Assurance", "Télécom", "Autre"],
      message: "Vos documents et vos besoins",
      placeholder:
        "Par exemple : 3 000 relevés bancaires par mois pour l'ouverture de compte, contrôle du titulaire et de la période.",
      submit: "Envoyer la demande",
      note: "Nous répondons sous deux jours ouvrés avec votre compte.",
      subject: "Demande d'accès Repody",
      consent:
        "J'accepte que Repody me contacte au sujet de cette demande. Mes coordonnées ne servent qu'à elle (voir la page confidentialité).",
      sending: "Envoi…",
      sent: "Merci : votre demande est bien reçue. Nous répondons sous deux jours ouvrés.",
      failed: "La demande n'a pas pu être envoyée. Réessayez, ou écrivez-nous :",
      tooMany: "Trop de demandes depuis ce réseau. Réessayez dans une heure, ou écrivez-nous :",
      robot: "Confirmez que vous n'êtes pas un robot, puis renvoyez.",
    },
    next: {
      title: "Ce qui se passe ensuite",
      items: [
        "Un échange de 30 minutes pour comprendre vos documents et vos règles",
        "Une démonstration sur des documents proches des vôtres",
        "Un pilote sur vos fichiers, dans votre environnement ou un environnement isolé",
        "Une proposition de licence et d'accompagnement",
      ],
    },
    direct: "Ou écrivez-nous directement :",
  },

  legal: {
    meta: { title: "Mentions légales", description: "Mentions légales du site repody.com." },
    title: "Mentions légales",
    body: [
      "Le site repody.com présente la plateforme Repody.",
      "Pour toute question relative au site, écrivez à l'adresse indiquée sur la page de contact.",
      "Les noms et marques cités appartiennent à leurs propriétaires respectifs.",
    ],
  },
  privacy: {
    meta: { title: "Confidentialité", description: "Comment repody.com traite vos données." },
    title: "Confidentialité",
    body: [
      "Ce site ne dépose aucun cookie de suivi et n'utilise aucun outil de mesure d'audience tiers.",
      "Le formulaire de demande d'accès envoie vos nom, e-mail professionnel, entreprise, secteur et message aux serveurs de Repody, uniquement après que vous avez coché la case de consentement et envoyé la demande. Nous ne les utilisons que pour traiter la demande et ouvrir votre compte, et ne les cédons jamais.",
      "Pour bloquer les envois automatisés, le formulaire utilise Cloudflare Turnstile (une vérification qui s'exécute dans votre navigateur) et conserve une empreinte à sens unique (SHA-256) de votre adresse réseau, jamais l'adresse elle-même, pour limiter le nombre de demandes par réseau.",
      "Une demande refusée est supprimée au bout de 90 jours. Une demande acceptée reste attachée à votre compte tant que vous utilisez Repody.",
      "Conformément à la loi 09-08, vous pouvez demander l'accès, la rectification ou la suppression de vos données à l'adresse de contact.",
    ],
  },
};

export type Dict = typeof fr;
