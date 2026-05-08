-- =============================================================================
-- SEED : risk_patterns
-- Patterns de risque couvrant les secteurs et stades les plus fréquents
-- C'est la table centrale pour la détection des dangers — elle définit
-- la capacité du modèle à identifier et expliquer les signaux d'alerte
-- =============================================================================

INSERT INTO risk_patterns
    (pattern_name, sector, stage, criticality, category,
     description, simple_explain,
     warning_signals, example_case,
     mitigation, mitigation_simple,
     impact_on_runway, time_to_impact)
VALUES

-- =============================================================================
-- RISQUES UNIVERSELS (sector = NULL = applicable à tous les secteurs)
-- =============================================================================

(
    'Low Product-Market Fit',
    NULL,
    'seed',
    'critical',
    'product',
    'Absence de correspondance forte entre la proposition de valeur du produit et '
    'les besoins réels d''un segment de marché identifié. Caractérisée par une '
    'rétention faible, une croissance essentiellement due à l''acquisition (pas '
    'organique), et un NPS insuffisant (< 30). Le produit est utilisé par '
    'inertie ou par manque d''alternative, non par dépendance.',
    'Tes utilisateurs utilisent ton produit, mais ils ne le recommandent pas et '
    'ne seraient pas vraiment désolés s''il disparaissait demain. C''est le signe '
    'que tu n''as pas encore trouvé quelque chose dont les gens ont vraiment besoin. '
    'Continuer à dépenser de l''argent sans régler ça, c''est remplir un seau percé.',
    'Rétention à 30 jours < 20%. NPS < 20. Croissance exclusivement payée (aucun '
    'référral organique). Peu d''utilisateurs reviennent spontanément sans relance. '
    'Feedbacks vagues et polis ("c''est bien") sans enthousiasme réel. '
    'Score Sean Ellis < 40% (utilisateurs très déçus si le produit disparaît).',
    'Une app de gestion de budget avait 50 000 téléchargements mais seulement '
    '8% d''utilisateurs actifs à 30 jours. Les retours étaient positifs en interview '
    'mais les gens n''ouvraient l''app que 1-2 fois avant d''arrêter. La startup '
    'a continué à dépenser en acquisition pendant 8 mois avant de manquer de fonds.',
    'Suspendre l''acquisition immédiatement. Conduire 20-30 interviews utilisateurs '
    'approfondies. Identifier le job-to-be-done réel. Tester des pivots ciblés '
    'sur le problème ou le segment. Mesurer la rétention comme indicateur principal.',
    'Arrête de dépenser en publicité. Parle avec tes utilisateurs pour comprendre '
    'pourquoi ils partent. Teste des changements significatifs sur le produit. '
    'Ce n''est pas un problème de marketing — c''est un problème de produit.',
    'kills_company',
    '3-6 months'
),

(
    'Premature Scaling',
    NULL,
    'seed',
    'critical',
    'execution',
    'Augmentation prématurée des dépenses opérationnelles, de l''équipe et des '
    'investissements marketing avant validation du product-market fit et des '
    'unit economics. Principale cause de mort de startups bien financées. '
    'Accélère les pertes sur un modèle structurellement non-viable.',
    'C''est dépenser beaucoup d''argent pour grandir vite, alors que tu n''as pas '
    'encore prouvé que ton modèle fonctionne. Comme appuyer sur l''accélérateur '
    'sans avoir de direction — tu vas vite, mais vers le mur.',
    'Recrutement massif avant Product-Market Fit avéré. Budget marketing multiplié '
    'sans amélioration des métriques de rétention. Ouverture de nouveaux marchés '
    'ou régions avant consolidation du marché initial. CAC qui augmente en même '
    'temps que la croissance. Runway qui fond rapidement sans jalons de validation.',
    'Une marketplace B2B a levé 2M$ et recruté 25 personnes en 6 mois. Le produit '
    'n''avait que 15 clients payants. Le burn mensuel est passé de 40K$ à 180K$. '
    'Quand les métriques n''ont pas suivi, la startup a dû licencier 70% de l''équipe '
    'et avait perdu 12 mois de runway en 6 mois.',
    'Fixer des jalons de validation clairs avant tout recrutement ou dépense '
    'marketing significative. Appliquer la règle : PMF d''abord, scale ensuite. '
    'Maintenir une équipe minimale jusqu''à validation des unit economics.',
    'Ne recrute pas et ne dépense pas beaucoup en marketing tant que tu n''as pas '
    'prouvé que ton produit retient ses utilisateurs et que chaque client te '
    'rapporte plus qu''il ne te coûte.',
    'kills_company',
    '1-3 months'
),

(
    'Co-founder Conflict',
    NULL,
    'pre-seed',
    'critical',
    'team',
    'Désaccords irréconciliables entre cofondateurs sur la vision, les rôles, '
    'les décisions stratégiques ou la répartition des parts, conduisant à une '
    'paralysie décisionnelle ou à une rupture. Cause de dissolution dans ~65% '
    'des cas selon les données YCombinator. Particulièrement destructeur en '
    'phase de stress (manque de traction, pression des investisseurs).',
    'Les désaccords entre fondateurs peuvent paralyser ou détruire une startup '
    'plus vite que n''importe quel problème marché. Quand les gens qui doivent '
    'prendre les décisions ne s''accordent plus, tout s''arrête — ou pire, '
    'tout part dans des directions opposées en même temps.',
    'Décisions reportées ou contestées publiquement. Divisions visibles dans '
    'les communications externes. Fondateurs qui contournent les décisions de '
    'l''autre. Recrutements ou dépenses non concertés. Tensions sur la répartition '
    'du travail. Discussions sur le rachat de parts ou la sortie d''un fondateur.',
    'Deux cofondateurs d''une fintech ont levé 500K$ avec une vision alignée. '
    'Après 8 mois sans traction, le CTO voulait pivoter technologiquement, '
    'le CEO voulait scaler l''existant. Après 3 mois de blocage décisionnel, '
    'le CTO est parti. La startup a perdu 6 mois de développement et sa crédibilité '
    'auprès des investisseurs de la prochaine levée.',
    'Etablir dès le départ un founders'' agreement avec vesting, rôles et mécanismes '
    'de résolution de conflits. Sessions régulières de recalibration de la vision. '
    'Faire appel à un médiateur neutre (investisseur, mentor) dès les premiers signes.',
    'Écrivez les règles du jeu dès le premier jour : qui décide quoi, comment '
    'vous gérez les désaccords, et que se passe-t-il si quelqu''un veut partir. '
    'Un conflit non résolu détruit plus de startups que le manque d''argent.',
    'kills_company',
    'immediate'
),

(
    'Vanity Metrics Focus',
    NULL,
    'pre-seed',
    'medium',
    'execution',
    'Orientation stratégique et communicationnelle sur des métriques à fort impact '
    'visuel mais sans corrélation avec la valeur créée ou la viabilité du modèle '
    '(téléchargements, pages vues, inscrits totaux, followers). Masque l''absence '
    'de traction réelle et conduit à de mauvaises décisions de pivot ou d''investissement.',
    'Compter le nombre de téléchargements ou de personnes inscrites, c''est comme '
    'un restaurant qui compterait combien de personnes sont passées devant sa vitrine. '
    'Ce qui compte, c''est combien sont entrées, ont commandé, et sont revenues. '
    'Les métriques de vanité donnent l''impression que ça marche sans le prouver.',
    'Communication centrée sur les inscrits totaux plutôt que les actifs. '
    'Métriques présentées en cumulatif, jamais en taux. Impossibilité de répondre '
    'à "combien d''utilisateurs actifs à 30 jours ?". Absence de données '
    'de rétention ou de conversion. Enthousiasme sur les "records" sans contexte.',
    'Une app de méditation avait 200 000 inscrits et le fondateur parlait de '
    '"200 000 utilisateurs". En réalité : 12% d''actifs à 7 jours (24 000), '
    '4% à 30 jours (8 000). La startup cherchait à lever des fonds sur ces '
    'chiffres "impressionnants". Les investisseurs expérimentés ont immédiatement '
    'demandé les métriques de rétention et passé leur tour.',
    'Définir une liste de métriques actionnables et s''y tenir. Toujours présenter '
    'les métriques en taux (activation, rétention, conversion) pas en cumulatif. '
    'Tester : "Cette métrique peut-elle m''aider à décider quoi faire ?"',
    'Arrête de compter les inscrits. Compte combien reviennent la semaine suivante, '
    'le mois suivant. C''est la seule façon de savoir si tu construis quelque chose '
    'de réel.',
    'significant',
    '3-6 months'
),

(
    'Cash Burn Too High',
    NULL,
    'seed',
    'critical',
    'financial',
    'Taux de consommation des liquidités disproportionné par rapport aux '
    'revenus générés et aux jalons de valeur atteints, réduisant le runway '
    'en dessous du seuil critique (< 6 mois) sans visibilité sur une prochaine '
    'levée ou sur l''atteinte du break-even.',
    'Tu dépenses ton argent plus vite que tu n''en gagnes, et tu vas manquer '
    'de fonds avant d''avoir prouvé que ton modèle fonctionne. À moins de 6 mois '
    'de runway, tu es en zone de danger — parce qu''une levée de fonds prend '
    'généralement 4 à 6 mois à conclure.',
    'Runway < 6 mois sans levée en cours. Net burn > 15% de la trésorerie disponible '
    'par mois. Ratio salaires/revenus > 5x. Dépenses marketing sans amélioration '
    'des métriques clés. Absence de budget prévisionnel à 12 mois.',
    'Une startup edtech avec 18 mois de runway a recruté 8 personnes en 4 mois '
    'pour accélérer le développement. Le burn est passé de 25K$/mois à 90K$/mois. '
    'Avec un MRR de 8K$, le runway est tombé à 7 mois. Trop tard pour lever '
    'dans de bonnes conditions, trop tôt pour être rentable.',
    'Établir un budget mensuel et le respecter. Fixer un niveau de burn maximum '
    'en fonction du runway cible. Déclencher un plan de réduction des coûts '
    'automatiquement à 9 mois de runway. Lever des fonds avec 12 mois de runway.',
    'Garde toujours plus de 9 mois de trésorerie. Commence à chercher des fonds '
    'quand tu en as encore 12. Ne recrute que quand c''est absolument nécessaire '
    'pour atteindre le prochain jalon de valeur.',
    'kills_company',
    '1-3 months'
),

(
    'Founding Team Skill Gap',
    NULL,
    'pre-seed',
    'high',
    'team',
    'Absence au sein de l''équipe fondatrice des compétences techniques, commerciales '
    'ou sectorielles nécessaires pour exécuter la vision initiale. Conduit à une '
    'dépendance coûteuse à des prestataires externes ou à des recrutements prématurés '
    'sans gouvernance ni culture établie.',
    'L''équipe ne réunit pas les compétences dont le projet a besoin. Par exemple, '
    'une startup tech sans CTO technique, ou une startup B2B sans personne ayant '
    'de l''expérience dans la vente. Ces manques se paient très cher en temps '
    'et en argent.',
    'Développement externalisé à 100% sans CTO interne. Aucun membre de l''équipe '
    'n''a vendu le type de produit que la startup construit. Absence totale '
    'd''expertise sectorielle dans un domaine réglementé. Dépendance à un consultant '
    'unique pour une compétence critique.',
    'Une startup healthtech fondée par deux médecins sans profil technique a '
    'externalisé le développement à une agence. 8 mois et 120K€ plus tard, '
    'le produit n''était pas livrable faute de specs techniques solides. '
    'L''agence a surfacturé et les fondateurs ne pouvaient pas évaluer le travail.',
    'Cartographier les compétences critiques dès le départ. Recruter un troisième '
    'co-fondateur technique plutôt que d''externaliser. Utiliser des programmes '
    'd''accélération pour combler les gaps rapidement.',
    'Identifie les 3 compétences sans lesquelles le projet ne peut pas avancer. '
    'Si l''équipe ne les a pas, trouve un co-fondateur ou un advisor qui les a '
    'avant de dépenser quoi que ce soit en développement.',
    'critical',
    '3-6 months'
),

(
    'Pivoting Too Often',
    NULL,
    'seed',
    'high',
    'execution',
    'Changements de stratégie fréquents non basés sur des apprentissages validés, '
    'reflétant une réaction aux opinions externes ou à la pression des investisseurs '
    'plutôt qu''à des données. Détruit la cohésion d''équipe, la crédibilité '
    'externe et la capacité à accumuler des apprentissages.',
    'Changer de direction tous les 2-3 mois sans données solides, c''est '
    'l''équivalent de changer de carte routière à chaque carrefour. Tu épuises '
    'ton équipe, tu perds la confiance de tes parties prenantes, et tu n''apprends '
    'rien — parce que tu ne restes jamais assez longtemps quelque part pour voir '
    'si ça marche.',
    'Plus de 2 pivots en moins de 12 mois sans données qui les justifient. '
    'Pivots décidés suite à des retours d''investisseurs, pas d''utilisateurs. '
    'Équipe qui demande "mais vers quoi on va cette fois ?". Perte de membres '
    'clés de l''équipe. Positionnement externe incohérent.',
    'Une startup B2B SaaS a pivoté 4 fois en 14 mois : CRM pour PME → outil '
    'de reporting → plateforme RH → outil de conformité. Chaque pivot était '
    'motivé par un retour d''un investisseur potentiel ou une conversation avec '
    'un prospect. L''équipe technique a perdu confiance et 2 développeurs clés '
    'sont partis.',
    'Fixer un horizon minimal d''expérimentation (ex: 3 mois) avant d''envisager '
    'un pivot. Documenter l''hypothèse testée et les données collectées. '
    'Distinguer ajustement tactique (itération) et pivot stratégique.',
    'Donne-toi le temps de voir les résultats avant de changer. Un pivot, '
    'c''est une décision importante qui devrait être basée sur des données, '
    'pas sur une conversation lors d''un dîner.',
    'significant',
    '3-6 months'
),

-- =============================================================================
-- RISQUES MARKETPLACE
-- =============================================================================

(
    'Cold Start Problem',
    'marketplace',
    'pre-seed',
    'critical',
    'market',
    'Problème structurel des plateformes bifaces où la valeur pour chaque côté '
    'dépend de la présence de l''autre côté. Sans offre suffisante, la demande '
    'ne vient pas ; sans demande, l''offre ne reste pas. Crée un cercle vicieux '
    'difficile à briser sans une stratégie d''amorçage asymétrique.',
    'Ta plateforme est utile seulement si elle a des acheteurs ET des vendeurs. '
    'Mais les acheteurs ne viennent pas si il n''y a pas de vendeurs, et les '
    'vendeurs ne restent pas si il n''y a pas d''acheteurs. C''est le problème '
    'de l''oeuf et de la poule — et sans stratégie pour le résoudre, '
    'ta marketplace ne décolle jamais.',
    'Ratio offre/demande déséquilibré (ex: 120 vendeurs, 8 transactions). '
    'Taux de conversion visiteur → transaction < 1%. Vendeurs ou acheteurs '
    'qui se plaignent de l''absence de l''autre côté. Acquisition coûteuse des '
    'deux côtés en même temps. Aucune rétention naturelle des deux côtés.',
    'Une marketplace de services à domicile en Afrique subsaharienne avait '
    '120 artisans inscrits après 2 mois mais seulement 8 transactions. '
    'Les artisans attendaient des clients qui n''arrivaient pas. '
    'Faute d''une masse critique d''artisans disponibles et fiables, '
    'les clients ne revenaient pas.',
    'Stratégie d''amorçage asymétrique : recruter manuellement et densément '
    'un seul côté dans une zone géographique restreinte. Créer de la valeur '
    'pour un côté même sans l''autre (ex: outils gratuits pour les vendeurs). '
    'Commencer hyperlocal avant d''élargir.',
    'Ne pas essayer de construire les deux côtés en même temps partout. '
    'Choisis une ville, un quartier, et remplis d''abord un côté à 100%. '
    'Airbnb a commencé par un seul quartier de San Francisco.',
    'kills_company',
    '3-6 months'
),

(
    'Disintermediation Risk',
    'marketplace',
    'seed',
    'high',
    'market',
    'Risque que les utilisateurs d''une marketplace contournent la plateforme '
    'pour traiter directement entre eux après la mise en relation initiale, '
    'privant la plateforme de ses revenus de commission. Particulièrement '
    'fréquent quand la valeur de la plateforme se limite à la première mise '
    'en relation.',
    'Tes utilisateurs se servent de ta plateforme pour se trouver, '
    'puis traitent directement entre eux sans payer ta commission. '
    'C''est comme si un site d''annonces immobilières faisait se rencontrer '
    'acheteur et vendeur, et qu''ils signent le contrat sans passer par l''agence. '
    'Tu as fait le travail, mais pas encaissé.',
    'Transactions qui débutent sur la plateforme et se finalisent hors-ligne. '
    'Utilisateurs qui échangent leurs coordonnées dès le premier contact. '
    'Ratio "mise en relation / transaction plateforme" qui se dégrade. '
    'Feedbacks qui mentionnent la commission comme trop élevée.',
    'Une marketplace de freelances constatait que sur 100 mises en relation, '
    'seulement 30 transactions passaient par la plateforme. Les 70 autres '
    'se faisaient directement par virement bancaire. La plateforme perdait '
    '70% de ses revenus potentiels.',
    'Créer de la valeur continue au-delà de la mise en relation : '
    'paiement sécurisé, assurance, évaluation/réputation, facturation, '
    'SAV. Plus la valeur ajoutée est forte, plus la désintermédiation coûte '
    'cher aux deux parties.',
    'Si les gens contournent ta plateforme, c''est qu''ils ne voient pas '
    'pourquoi te payer au-delà de l''introduction. Donne-leur une vraie raison '
    'de rester : sécurité du paiement, garantie, réputation, simplicité.',
    'critical',
    '3-6 months'
),

-- =============================================================================
-- RISQUES SAAS / ABONNEMENT
-- =============================================================================

(
    'High Churn Rate',
    'saas',
    'seed',
    'critical',
    'product',
    'Taux de désabonnement mensuel supérieur aux benchmarks sains du secteur '
    '(> 3% mensuel pour les SaaS B2C, > 1.5% pour B2B). Indique une absence '
    'de valeur perçue suffisante pour justifier la continuation de l''abonnement. '
    'Rend la croissance structurellement très difficile et le LTV insuffisant '
    'pour couvrir le CAC.',
    'Chaque mois, trop de tes clients partent. Ça veut dire que ton produit '
    'ne leur manque pas assez pour qu''ils continuent à payer. C''est le signal '
    'le plus direct que quelque chose ne va pas — soit dans le produit, '
    'soit dans la promesse que tu as faite pour les acquérir.',
    'Churn mensuel > 5% (B2C) ou > 2% (B2B). Résiliations groupées à la fin '
    'du premier mois ou de la période d''essai. Feedbacks de sortie vagues '
    '("plus besoin", "trop cher"). Rétention à 90 jours < 30%. '
    'Croissance du MRR tirée uniquement par l''acquisition, jamais par la rétention.',
    'Un SaaS B2B de gestion de projet avait 150 clients et un churn de 7% par mois. '
    'Pour maintenir son MRR stable, il devait acquérir 10-11 nouveaux clients '
    'par mois. Son CAC était de 800$. Il dépensait donc 8 000-9 000$/mois '
    'juste pour rester en place, sans pouvoir croître.',
    'Analyser les cohortes de churn pour identifier le moment de décrochage. '
    'Conduire des exit interviews systématiques. Améliorer l''onboarding '
    'pour atteindre le "moment aha" plus vite. Créer des success milestones '
    'dans les 30 premiers jours.',
    'Interroge chaque client qui part. Comprends pourquoi ils ne reviennent pas '
    'avant le deuxième mois. Souvent, c''est un problème d''onboarding — '
    'les gens ne voient pas assez vite ce que ton produit peut faire pour eux.',
    'critical',
    '1-3 months'
),

(
    'Feature vs Product Confusion',
    'saas',
    'pre-seed',
    'medium',
    'product',
    'Construction d''une fonctionnalité ou d''un add-on d''un produit existant '
    'en le positionnant comme un produit autonome, sans valeur standalone '
    'suffisante pour justifier un abonnement ou une adoption indépendante. '
    'Problème de positionnement et de go-to-market fondamental.',
    'Tu construis quelque chose qui serait utile comme option dans un autre '
    'produit, mais pas assez puissant pour que quelqu''un le paye tout seul. '
    'C''est comme vendre uniquement le sel d''un restaurant gastronomique '
    '— c''est bon, mais ça ne tient pas debout seul.',
    'Prospect qui dit systématiquement "c''est sympa mais on a déjà X qui fait ça". '
    'Impossible de définir qui utilise UNIQUEMENT ton produit sans autre outil. '
    'Willingness-to-pay très faible. Concurrents directs = grandes plateformes '
    'avec feature similaire intégrée gratuitement. Cycle de vente très long.',
    'Une startup proposait un outil d''analyse des sentiments de réunions Zoom. '
    'Utile, mais Zoom, Teams et Slack avaient tous des fonctionnalités similaires '
    'en développement. Le produit ne justifiait pas un abonnement de 50$/mois '
    'supplémentaire pour la majorité des acheteurs potentiels.',
    'Tester le willingness-to-pay très tôt (avant de coder). Identifier si le '
    'problème résolu existe en dehors de l''écosystème d''un autre produit. '
    'Considérer une stratégie d''intégration ou de partenariat plutôt que '
    'de produit standalone.',
    'Avant de coder, essaie de vendre. Si personne ne sort son portefeuille '
    'pour ce que tu décris, c''est peut-être parce que quelqu''un le fait '
    'déjà gratuitement.',
    'significant',
    '3-6 months'
),

-- =============================================================================
-- RISQUES FINTECH
-- =============================================================================

(
    'Regulatory Non-Compliance Risk',
    'fintech',
    'pre-seed',
    'critical',
    'regulatory',
    'Exposition à des sanctions réglementaires, suspensions d''activité ou '
    'amendes du fait d''opérations dans des domaines financiers réglementés '
    '(paiement, crédit, épargne, change) sans licences appropriées. '
    'Particulièrement critique dans les marchés émergents où les régulateurs '
    'durcissent les exigences sur les acteurs fintech.',
    'Si tu touches à l''argent des gens — paiements, crédits, épargne — '
    'il y a des règles très strictes à suivre. Sans les bonnes licences, '
    'le régulateur peut te forcer à arrêter du jour au lendemain, '
    'même si ton produit est excellent.',
    'Opérations de paiement ou de crédit sans licence émetteur ou de prestataire '
    'de services de paiement. Collecte de dépôts sans agrément bancaire. '
    'Absence de mécanismes KYC/AML documentés. Expansion géographique sans '
    'analyse de conformité locale. Aucun conseiller juridique spécialisé '
    'fintech dans l''équipe ou le board.',
    'Une fintech de micro-crédit en Afrique de l''Ouest a opéré 14 mois sans '
    'licence de l''autorité de régulation locale. Suite à une plainte d''une '
    'banque concurrente, l''activité a été suspendue pendant 6 mois pour '
    'régularisation. La startup a perdu 40% de ses clients et ses deux '
    'principaux investisseurs ont demandé le remboursement.',
    'Intégrer un avocat spécialisé en droit financier dès la phase de conception. '
    'Cartographier les licences requises dans chaque marché cible. Envisager '
    'une stratégie BaaS (Banking as a Service) pour s''appuyer sur '
    'des licences existantes.',
    'Avant de toucher à l''argent de qui que ce soit, parle à un avocat '
    'spécialisé. Il est moins coûteux de payer des conseils juridiques '
    'en amont que de gérer une suspension réglementaire.',
    'kills_company',
    'immediate'
),

(
    'Negative Unit Economics at Scale',
    'fintech',
    'seed',
    'critical',
    'financial',
    'Modèle économique où les coûts variables (coût de traitement des transactions, '
    'coût du risque de crédit, coûts d''acquisition) croissent proportionnellement '
    'ou plus vite que les revenus, rendant la profitabilité structurellement '
    'impossible sans changement fondamental du modèle.',
    'Plus tu grandis, plus tu perds de l''argent. Chaque nouvelle transaction '
    'ou chaque nouveau client te coûte plus que ce qu''il te rapporte. '
    'Dans la fintech, ce problème est souvent caché par la croissance des volumes — '
    'jusqu''à ce que les pertes deviennent trop grandes pour être ignorées.',
    'Marge par transaction négative ou < 1%. Coût du risque (défauts de crédit) '
    'non intégré dans le pricing. CAC qui augmente avec la scale. '
    'Revenus d''interchange insuffisants pour couvrir les coûts opérationnels. '
    'LTV/CAC < 1 quand le risque de crédit est intégré.',
    'Une fintech de BNPL (Buy Now Pay Later) facturait 0% aux consommateurs '
    'et 2.5% aux marchands. Ses coûts opérationnels (fraude, défauts, '
    'infrastructure) atteignaient 3.8% par transaction. À 10M$ de volume '
    'mensuel, elle perdait 130K$/mois structurellement.',
    'Modéliser les unit economics avec les coûts du risque dès le début. '
    'Tester différents pricing. Trouver des leviers d''amélioration de la marge '
    'avant de scaler (automatisation, réduction du risque par ML).',
    'Calcule ce que tu gagnes et ce que tu coûtes sur chaque transaction — '
    'avec le risque de non-remboursement inclus. Si le chiffre est négatif, '
    'grandis d''abord pour résoudre ce problème.',
    'kills_company',
    '3-6 months'
),

-- =============================================================================
-- RISQUES AGRITECH / MARCHÉS ÉMERGENTS
-- =============================================================================

(
    'Last-Mile Distribution Problem',
    'agritech',
    'seed',
    'high',
    'execution',
    'Incapacité à atteindre le client final (souvent en zone rurale) '
    'de manière économiquement viable, due aux infrastructures insuffisantes, '
    'aux coûts logistiques élevés ou à l''absence de réseau de distribution '
    'fiable. Rend le modèle non-scalable dans les marchés cibles.',
    'Ton produit est excellent, mais tu ne peux pas l''amener là où sont '
    'tes clients à un coût raisonnable. Dans les zones rurales d''Afrique, '
    'd''Asie du Sud ou d''Amérique Latine, "livrer" peut coûter plus cher '
    'que le produit lui-même.',
    'CAC élevé dans les zones rurales vs urbaines (ratio > 3x). '
    'Coût de livraison > 20% du prix du produit. Dépendance à un seul '
    'réseau de distribution. Taux de retours ou de non-livraison > 10%. '
    'Croissance concentrée uniquement dans les grandes villes.',
    'Une startup agritech vendant des intrants agricoles en ligne en Afrique '
    'de l''Ouest avait des coûts de livraison de 8-12$ par commande pour '
    'des paniers moyens de 15-20$. Le modèle était viable en ville '
    'mais structurellement non-rentable pour 80% de sa cible (agriculteurs ruraux).',
    'Partenariats avec réseaux de distribution existants (coopératives, '
    'épiceries locales, agents mobile money). Modèles hub-and-spoke. '
    'Click-and-collect. Former des agents locaux.',
    'Ne construis pas ta propre logistique tout seul. Trouve qui livre '
    'déjà là où sont tes clients — médicaments, produits Unilever, '
    'mobile money — et piggyback sur leurs réseaux.',
    'critical',
    '3-6 months'
),

(
    'Digital Literacy Barrier',
    'agritech',
    'pre-seed',
    'high',
    'market',
    'Décalage entre les hypothèses technologiques du produit (smartphone, '
    'connexion internet, maîtrise des interfaces numériques) et les '
    'capacités réelles du segment cible. Résulte en une adoption très '
    'inférieure aux projections et en des coûts d''accompagnement élevés.',
    'Ton application suppose que tes utilisateurs ont un smartphone récent, '
    'une bonne connexion internet, et savent utiliser des apps. Mais si '
    'ta cible est des agriculteurs ruraux avec un feature phone et '
    'une connexion 2G intermittente, tu t''adresses à une version '
    'idéale de ta cible qui n''existe pas.',
    'Taux d''adoption très inférieur aux projections. Coûts de formation '
    'et d''accompagnement non prévus au budget. Feedback : "trop compliqué". '
    'Utilisation réelle limitée à 1-2 fonctionnalités simples. '
    'Forte dépendance à des agents intermédiaires pour l''usage.',
    'Une startup EdTech pour enseignants ruraux au Kenya avait conçu '
    'une app nécessitant une connexion continue et un smartphone Android 9+. '
    'Sur le terrain, 60% des enseignants ciblés avaient des téléphones '
    'incompatibles et 35% n''avaient pas de connexion fiable en classe. '
    'L''adoption réelle était 8x inférieure aux projections.',
    'Faire des entretiens terrain avant toute décision produit. '
    'Concevoir pour le plus petit dénominateur commun technologique '
    'du segment cible. Envisager des solutions SMS, USSD ou offline-first.',
    'Va passer du temps avec tes vrais utilisateurs dans leur contexte réel '
    'avant d''écrire une ligne de code. Ce que tu imagines de leur vie '
    'technologique et ce qu''elle est vraiment sont souvent très différents.',
    'critical',
    '3-6 months'
),

-- =============================================================================
-- RISQUES CONCURRENTIELS (tous secteurs)
-- =============================================================================

(
    'No Competitive Moat',
    NULL,
    'series-a',
    'high',
    'competition',
    'Absence d''avantage concurrentiel durable — effets de réseau, '
    'données propriétaires, coûts de switching élevés, économies d''échelle '
    'significatives ou propriété intellectuelle — rendant le modèle '
    'facilement réplicable par des acteurs mieux capitalisés.',
    'Ton produit fonctionne, mais n''importe quelle grande entreprise avec '
    'des moyens pourrait le copier en 6 mois. Sans quelque chose qui te '
    'protège — une base de données unique, des clients très difficiles '
    'à débaucher, un réseau d''utilisateurs qui se renforce mutuellement — '
    'un concurrent plus gros peut te détruire.',
    'Aucune donnée propriétaire accumulée. Clients facilement débordables '
    'par une offre légèrement moins chère. Technologie entièrement basée '
    'sur des APIs ou outils tiers disponibles à tous. Pas d''effets de réseau. '
    'Coûts de switching quasi-nuls pour les clients. Concurrents directs '
    'bien financés sur le même segment.',
    'Un SaaS d''analyse de données RH avait 200 clients et 1.2M$ de MRR. '
    'Workday a lancé une feature similaire intégrée à son produit. '
    'En 9 mois, la startup a perdu 35% de ses clients qui utilisaient '
    'déjà Workday. Elle n''avait rien construit qui la différenciait durablement.',
    'Identifier et investir activement dans un ou deux avantages compétitifs '
    'dès le départ. Construire des effets de réseau si possible. '
    'Accumuler des données propriétaires. Augmenter les coûts de switching '
    'via l''intégration profonde dans les workflows clients.',
    'Demande-toi : si Google ou Salesforce décide de faire ce que tu fais, '
    'est-ce que tes clients restent quand même avec toi ? Si la réponse '
    'est non, tu dois construire quelque chose qui les rend fidèles.',
    'critical',
    '3-6 months'
),

(
    'Platform Dependency Risk',
    NULL,
    'seed',
    'high',
    'competition',
    'Dépendance critique à une plateforme tierce (App Store, Google Play, '
    'AWS, Stripe, Facebook Ads, Shopify) pour l''acquisition, la distribution '
    'ou l''infrastructure. Expose la startup à des changements de règles, '
    'des hausses de prix ou des suspensions imprévisibles.',
    'Ton business repose entièrement sur une plateforme que tu ne contrôles pas. '
    'Si Apple change ses règles, si Facebook augmente ses prix publicitaires '
    'de 50%, ou si AWS modifie ses tarifs — ton modèle s''effondre. '
    'Tu as construit sur du terrain que quelqu''un d''autre possède.',
    'Plus de 70% du trafic ou des revenus vient d''une seule plateforme. '
    'CAC entièrement dépendant d''une régie publicitaire. Aucune '
    'stratégie d''acquisition alternative testée. Infrastructure critique '
    'sur un seul cloud provider sans plan de continuité.',
    'Une app mobile de fitness dépendait à 80% des publicités Meta '
    'pour l''acquisition. En 2021, les changements iOS 14 sur le tracking '
    'ont fait doubler son CAC en 3 mois. Sans alternative, elle a vu '
    'son burn exploser et n''a pas réussi à lever sa série A.',
    'Diversifier les canaux d''acquisition (SEO, partnerships, communauté). '
    'Construire une audience owned (newsletter, communauté). '
    'Multi-cloud pour l''infrastructure. Surveiller les changements '
    'de politiques des plateformes clés.',
    'Diversifie tes canaux dès maintenant, même si c''est plus lent. '
    'Si ta croissance dépend entièrement d''une seule plateforme, '
    'tu es à leur merci.',
    'critical',
    '1-3 months'
);
