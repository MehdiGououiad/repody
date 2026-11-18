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
      verdictFacts: "1 règle sur 2 respectée · 4 champs · 2,1 s",
      fields: [
        { key: "numero_facture", value: "FAC-2026-0412", ok: true },
        { key: "fournisseur", value: "Atlas Logistique SARL", ok: true },
        { key: "montant_ht", value: "48 500,00 MAD", ok: false },
        { key: "total_ttc", value: "58 800,00 MAD", ok: false },
      ],
      note: "Total TTC ≠ HT + TVA 20 %",
      gpuTime: "6,8 s",
      extractTime: "0,4 s",
    },
    proof: [
      { value: "1", label: "passage de l'image du document aux champs typés" },
      { value: "24", label: "types de champs, des dates aux IBAN et aux tableaux" },
      { value: "99", label: "pages lues par document" },
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
      newSteps: ["Image de la page", "NuExtract3", "Champs typés"],
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
          body: "OpenID Connect avec Keycloak, PKCE, double authentification pour les administrateurs et quatre rôles aux permissions précises.",
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
          body: "Docker Compose sur une machine Linux. Toute la pile, prête en une commande, déployée automatiquement.",
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
        "Vérification et déploiement",
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
          a: "PDF, PNG, JPEG et WebP, jusqu'à 99 pages par document et 20 fichiers par exécution. Le modèle lit le français, l'anglais et les principales langues européennes ; l'interface est en français et en anglais.",
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
          q: "Comment se passent les mises à jour ?",
          a: "Chaque version est construite, analysée, signée et publiée avec sa nomenclature logicielle. Vous choisissez la version à déployer ; sa signature est vérifiée avant l'installation.",
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
        "Constructeur de workflows, 24 types de champs, règles sur un ou deux documents, rapports détaillés, API REST avec clés par workflow et suivi en direct de chaque exécution.",
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
            title: "Import de modèles NuExtract",
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
            body: "20 fichiers et 25 Mo par fichier par défaut, types vérifiés (PDF, PNG, JPEG, WebP), délai maximal par exécution.",
          },
          {
            title: "Résultats en cache",
            body: "Optionnel : le même fichier avec le même schéma ne repasse pas par le modèle (clé SHA-256 du contenu et du schéma).",
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
            body: "Limite d'exécutions par minute et par client (429), file plafonnée (503), avec l'en-tête Retry-After.",
          },
          {
            title: "Contrat typé",
            body: "Spécification OpenAPI générée depuis le code et vérifiée en intégration continue ; l'interface en dérive ses types.",
          },
          {
            title: "Essai depuis l'interface",
            body: "Lancez une exécution avec la vraie clé, exactement comme un client de l'API.",
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
            body: "Les exécutions dont des règles ont échoué, les plus anciennes d'abord.",
          },
          {
            title: "La semaine en chiffres",
            body: "Exécutions, taux de réussite et échecs de règles, comparés à la semaine précédente.",
          },
          { title: "Volume par jour", body: "Chaque jour mène à ses exécutions." },
          {
            title: "État de la file",
            body: "Exécutions en cours et en attente, alerte si une exécution ne répond plus.",
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
            body: "Nombre, taille et type de fichier vérifiés à l'entrée ; stockage objet privé.",
          },
          {
            title: "Débit et file maîtrisés",
            body: "Limite par client (HTTP 429) et file d'attente plafonnée (HTTP 503), avec Retry-After.",
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
            body: "Images par empreinte, actions de CI par commit ; Dependabot propose chaque mise à jour.",
          },
          {
            title: "Résultats centralisés",
            body: "Les analyses sont publiées dans l'onglet de sécurité du dépôt (SARIF).",
          },
          {
            title: "Versions immuables",
            body: "Une version est une étiquette et un ensemble d'images signées ; on déploie une version, pas une branche.",
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
      modelTech: "vLLM · NuExtract3",
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
            title: "NuExtract3",
            body: "Modèle de vision spécialisé dans l'extraction structurée : il reçoit l'image des pages et un modèle JSON, et renvoie les champs.",
          },
          {
            title: "Servi par vLLM",
            body: "API compatible OpenAI, décodage spéculatif, poids complets ; le serveur de modèle reste hors du produit, sur votre GPU ou un GPU managé.",
          },
          {
            title: "Pages en 170 DPI",
            body: "Chaque page est rendue en image à la résolution attendue par le modèle, jusqu'à 99 pages par document.",
          },
          {
            title: "GPU à la demande",
            body: "En mode managé, le GPU s'éteint après une minute sans requête et repart d'un instantané mémoire en quelques secondes ; un seul conteneur au plus.",
          },
          {
            title: "Démarrage annoncé",
            body: "Avant d'extraire, le worker vérifie si le modèle est éveillé ; sinon l'exécution affiche « Démarrage du GPU ».",
          },
          {
            title: "Mesuré",
            body: "Appel au modèle chaud : environ 0,4 s pour une facture d'une page ; démarrage à froid : environ 7 s.",
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
            title: "Délais et reprise",
            body: "Chaque exécution a un délai maximal ; celle qui le dépasse, ou dont le worker s'arrête, échoue avec sa raison.",
          },
          {
            title: "Admission contrôlée",
            body: "Au-delà de la profondeur de file choisie, l'API refuse proprement (503) au lieu de s'effondrer.",
          },
          {
            title: "Concurrence bornée",
            body: "Le nombre de requêtes simultanées vers le modèle est réglé pour ne jamais saturer le GPU, et les clients passent à tour de rôle : un gros envoi n'occupe pas tous les workers.",
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
            title: "Pile complète fournie",
            body: "Prometheus, Grafana, Loki, Tempo et Alloy, configurés.",
          },
          {
            title: "Suivi des erreurs",
            body: "Erreurs de l'interface et du serveur remontées à un service compatible Sentry, hébergeable chez vous.",
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
          body: "Chaque page devient une image à 170 DPI ; les documents partent en parallèle au modèle avec leur modèle JSON.",
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
          adr: "001",
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
          "Déploiement par la chaîne de CI, signature vérifiée, retour arrière en une commande",
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
        "La configuration d'observabilité (Prometheus, Grafana, Loki, Tempo)",
        "Le serveur de modèle prêt à déployer",
        "La documentation d'installation, d'exploitation et de dépannage",
        "Les décisions d'architecture et le guide de migration",
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
          { name: "Code scanning", detail: "Résultats publiés en SARIF dans le dépôt." },
        ],
      },
      {
        id: "release",
        title: "Version",
        lead: "Une étiquette de version déclenche la publication, seulement si l'intégration continue est verte sur ce commit.",
        gates: [
          {
            name: "Garde",
            detail: "Pas de version sans intégration continue réussie sur le même commit.",
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
            detail: "Une chaîne dédiée vérifie les signatures avant de promouvoir une version.",
          },
        ],
      },
      {
        id: "deploy",
        title: "Déploiement",
        lead: "On déploie une version, sur un environnement protégé, après vérification.",
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
            name: "Retour arrière",
            detail: "Redéployer la version précédente est la même commande.",
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
          body: "Dependabot sur npm, Python, Docker, Compose et les actions ; tout est épinglé.",
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
