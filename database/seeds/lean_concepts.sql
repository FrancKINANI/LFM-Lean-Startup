-- =============================================================================
-- SEED : lean_concepts
-- Concepts fondamentaux du Lean Startup avec double niveau d'explication
-- Objectif : permettre au modèle de rendre accessible ce que les
-- whitepapers rendent opaque
-- =============================================================================

INSERT INTO lean_concepts
    (concept_name, category, aliases, technical_def, simple_def, analogy,
     example, how_to_apply, common_mistakes, related_concepts,
     related_risks, source_whitepaper)
VALUES

-- ---------------------------------------------------------------------------
-- FRAMEWORKS FONDAMENTAUX
-- ---------------------------------------------------------------------------

(
    'Build-Measure-Learn',
    'framework',
    ARRAY['BML', 'Boucle BML', 'Lean Loop'],
    'Cycle itératif central de la méthodologie Lean Startup dans lequel une équipe '
    'construit un artefact minimal (MVP), mesure son impact à travers des métriques '
    'actionnables, et en tire des apprentissages validés pour décider de persévérer '
    'ou de pivoter. Le cycle doit être parcouru le plus rapidement possible.',
    'C''est une boucle d''apprentissage : tu construis quelque chose de petit, tu '
    'regardes ce que les gens en font vraiment, et tu décides quoi faire ensuite. '
    'L''objectif est de faire cette boucle le plus vite possible pour ne pas gaspiller '
    'du temps sur de mauvaises hypothèses.',
    'C''est comme cuisiner pour la première fois : tu fais goûter un plat simple à '
    'quelqu''un, tu observes sa réaction, et tu ajustes la recette. Tu ne prépares '
    'pas un banquet de 12 plats avant d''avoir eu un seul retour.',
    'Dropbox a commencé par une simple vidéo de démonstration (Build) pour mesurer '
    'l''intérêt (Measure) avant d''écrire une seule ligne de code, ce qui a validé '
    'la demande (Learn) avec un minimum d''investissement.',
    'Identifier d''abord l''hypothèse la plus risquée de votre modèle. Concevoir '
    'l''expérience la plus simple possible pour la tester. Définir à l''avance ce '
    'qui constitue un résultat positif ou négatif.',
    'Confondre "construire" avec "finir un produit". Le MVP doit être aussi petit '
    'que possible. Mesurer des métriques de vanité au lieu de métriques actionnables. '
    'Sauter l''étape "Learn" et enchaîner les builds sans tirer de conclusions.',
    ARRAY['MVP', 'Pivot', 'Validated Learning', 'Innovation Accounting'],
    'Premature Scaling, Vanity Metrics, Low Product-Market Fit',
    'The Lean Startup — Eric Ries (2011)'
),

(
    'MVP',
    'tool',
    ARRAY['Minimum Viable Product', 'Produit Minimum Viable'],
    'Version d''un nouveau produit qui permet à une équipe de collecter le maximum '
    'd''apprentissages validés sur les clients avec le minimum d''effort. Un MVP '
    'n''est pas nécessairement un produit fonctionnel — c''est l''expérience la plus '
    'légère possible pour tester une hypothèse spécifique.',
    'C''est la version la plus simple de ton produit qui te permet de vérifier si '
    'ton idée fonctionne vraiment. Ce n''est pas une version "réduite" de ce que tu '
    'veux construire — c''est une expérience pour apprendre quelque chose de précis.',
    'Si tu veux savoir si les gens achèteraient une voiture volante, tu ne construis '
    'pas une voiture volante. Tu fais une affiche, tu la montres dans la rue, et tu '
    'vois combien de personnes sortent leur carnet de chèques.',
    'Zappos (chaussures en ligne) a commencé par un site web simple avec des photos '
    'de chaussures prises dans des magasins locaux. Quand quelqu''un commandait, le '
    'fondateur allait acheter la paire et l''expédiait. Pas de stock, pas de logistique '
    '— juste un test pour valider que les gens achèteraient des chaussures en ligne.',
    'Définir une seule hypothèse à tester par MVP. Fixer un critère de succès avant '
    'de lancer. Choisir le format le plus rapide : page de pré-vente, vidéo, prototype '
    'Wizard of Oz, concierge MVP.',
    'Construire trop. Un MVP qui prend 6 mois n''est pas un MVP. Utiliser le MVP '
    'comme excuse pour livrer un produit de mauvaise qualité. Ne pas définir '
    'l''hypothèse avant de construire.',
    ARRAY['Build-Measure-Learn', 'Validated Learning', 'Pivot'],
    'Premature Scaling, Feature vs Product Confusion, Low Product-Market Fit',
    'The Lean Startup — Eric Ries (2011)'
),

(
    'Product-Market Fit',
    'metric',
    ARRAY['PMF', 'Adéquation Produit-Marché'],
    'État dans lequel un produit satisfait une forte demande d''un marché spécifique, '
    'caractérisé par une rétention élevée, une croissance organique et un engagement '
    'utilisateur profond. Souvent mesuré par le score de Sean Ellis (>40% d''utilisateurs '
    'très déçus si le produit disparaissait) ou un NPS > 50.',
    'C''est le moment où ton produit répond si bien à un vrai besoin que les gens '
    'le recommandent spontanément, y reviennent sans qu''on les y pousse, et seraient '
    'vraiment embêtés s''il disparaissait. C''est la différence entre un produit que '
    'les gens "utilisent" et un produit dont ils "ne peuvent pas se passer".',
    'C''est comme trouver la bonne clé pour une serrure. Tant que tu n''as pas le '
    'bon fit, tu forces la porte. Quand tu l''as trouvé, ça s''ouvre tout seul.',
    'Slack n''était pas conçu comme un outil de messagerie d''entreprise — c''était '
    'un outil interne pour une équipe de jeu vidéo. Quand ils l''ont partagé avec '
    'd''autres équipes et vu que tout le monde l''adoptait immédiatement et ne voulait '
    'plus s''en passer, ils ont reconnu le PMF.',
    'Mesurer le taux de rétention à 30 et 90 jours. Surveiller la croissance organique '
    '(referral). Utiliser le test Sean Ellis. Écouter si les utilisateurs expriment '
    'une dépendance émotionnelle au produit.',
    'Confondre adoption initiale (curiosité) avec PMF. Croire que beaucoup '
    'd''utilisateurs = PMF sans regarder la rétention. Scaler avant d''avoir le PMF.',
    ARRAY['Build-Measure-Learn', 'Pivot', 'Innovation Accounting', 'Churn'],
    'Low Product-Market Fit, Premature Scaling, High Churn Rate',
    'The Lean Startup — Eric Ries (2011)'
),

(
    'Pivot',
    'strategy',
    ARRAY['Pivotement', 'Changement de cap'],
    'Changement structurel et délibéré de stratégie, conçu pour tester une nouvelle '
    'hypothèse fondamentale sur le produit, le modèle économique ou le moteur de '
    'croissance, tout en maintenant les apprentissages acquis. Distinct d''un simple '
    'ajustement (optimisation) ou d''un abandon complet.',
    'Un pivot, ce n''est pas "tout recommencer". C''est changer une chose importante '
    'de ta stratégie parce que tu as appris quelque chose de fondamental sur ce qui '
    'ne fonctionne pas — en gardant tout ce que tu as appris jusqu''ici.',
    'C''est comme un GPS qui recalcule l''itinéraire quand il y a un embouteillage. '
    'La destination reste la même (construire une entreprise viable), mais le chemin '
    'change.',
    'Instagram était au départ Burbn, une app de check-in géolocalisé. En analysant '
    'les données, les fondateurs ont vu que les utilisateurs n''utilisaient qu''une '
    'fonctionnalité : le partage de photos. Ils ont pivoté en supprimant tout sauf ça.',
    'Analyser les données du cycle BML avant de décider. Identifier précisément '
    'quelle hypothèse a été invalidée. Choisir le type de pivot le plus conservateur '
    'possible (changer le moins de choses possible).',
    'Pivoter par peur plutôt que par apprentissage. Pivoter trop souvent sans laisser '
    'le temps à une stratégie de se révéler. Pivoter trop tard après avoir épuisé '
    'les ressources.',
    ARRAY['Build-Measure-Learn', 'Product-Market Fit', 'Validated Learning'],
    'Pivoting Too Often, Premature Scaling',
    'The Lean Startup — Eric Ries (2011)'
),

(
    'Validated Learning',
    'principle',
    ARRAY['Apprentissage Validé'],
    'Unité de progression dans une startup Lean, consistant en des connaissances '
    'empiriquement démontrées sur les clients, les marchés et le modèle économique, '
    'obtenues par des expériences rigoureuses. S''oppose à l''apprentissage par '
    'conviction ou par analogie.',
    'C''est la différence entre savoir quelque chose parce que tu l''as testé avec '
    'de vraies personnes et de vraies données, et le croire parce que ça "semble '
    'logique". Une startup progresse quand elle accumule des apprentissages validés, '
    'pas seulement des lignes de code ou des features.',
    'C''est la différence entre un médecin qui prescrit un médicament parce qu''il '
    'a été testé cliniquement, et un qui le prescrit parce qu''il "pense que ça devrait '
    'marcher".',
    'Une startup EdTech pensait que les enseignants voulaient plus de contenu. Après '
    'avoir interviewé 50 enseignants et testé une fonctionnalité de curation, ils ont '
    'appris que le vrai problème était le temps de préparation — pas le manque de '
    'contenu. Cet apprentissage validé a réorienté tout le produit.',
    'Formuler chaque initiative comme une hypothèse testable. Définir les métriques '
    'de validation avant l''expérience. Documenter les apprentissages même (surtout) '
    'quand ils invalident l''hypothèse.',
    'Confondre "les utilisateurs ont aimé la démo" avec un apprentissage validé. '
    'Ignorer les données qui contredisent les convictions. Ne pas documenter '
    'les apprentissages négatifs.',
    ARRAY['Build-Measure-Learn', 'Innovation Accounting', 'MVP'],
    'Vanity Metrics, Low Product-Market Fit',
    'The Lean Startup — Eric Ries (2011)'
),

(
    'Innovation Accounting',
    'framework',
    ARRAY['Comptabilité de l''Innovation'],
    'Système alternatif de mesure de la progression d''une startup qui remplace '
    'les indicateurs comptables traditionnels par des métriques actionnables '
    'permettant d''évaluer si les apprentissages progressent réellement. '
    'Repose sur trois étapes : établir une baseline, optimiser vers l''idéal, '
    'décider de persévérer ou pivoter.',
    'C''est une façon de mesurer si tu apprends vraiment et si tu te rapproches '
    'd''un modèle qui fonctionne — pas juste si tu "es occupé" ou si tu dépenses '
    'de l''argent. Ça répond à la question : est-ce que mes actions d''aujourd''hui '
    'me rapprochent d''une entreprise viable ?',
    'C''est comme évaluer un élève non pas sur combien d''heures il a étudié, '
    'mais sur ce qu''il a vraiment appris et retenu.',
    'Au lieu de mesurer "nombre de features livrées", une startup SaaS mesure '
    'son taux d''activation (% d''inscrits qui complètent l''onboarding), son taux '
    'de rétention à 30 jours et son NPS. Ces trois métriques ensemble montrent '
    'si le produit crée vraiment de la valeur.',
    'Choisir 3-5 métriques actionnables maximum. Définir ce que signifie "amélioration '
    'suffisante" pour continuer. Revoir les métriques à chaque cycle BML.',
    'Mesurer ce qui est facile à mesurer plutôt que ce qui est important. '
    'Trop de métriques qui se noient les unes les autres. Ne pas comparer '
    'les métriques dans le temps.',
    ARRAY['Build-Measure-Learn', 'Validated Learning', 'Vanity Metrics'],
    'Vanity Metrics, Low Product-Market Fit',
    'The Lean Startup — Eric Ries (2011)'
),

-- ---------------------------------------------------------------------------
-- MÉTRIQUES CLÉS
-- ---------------------------------------------------------------------------

(
    'Customer Acquisition Cost',
    'metric',
    ARRAY['CAC', 'Coût d''Acquisition Client'],
    'Coût total moyen engagé pour acquérir un nouveau client payant, calculé en '
    'divisant la totalité des dépenses sales & marketing sur une période par le '
    'nombre de nouveaux clients acquis sur cette même période.',
    'C''est combien tu dépenses en moyenne pour convaincre une personne de devenir '
    'ton client. Si tu dépenses 1000$ en publicité et que tu obtiens 10 clients, '
    'ton CAC est de 100$. Le problème : si chaque client ne te rapporte que 50$, '
    'tu perds de l''argent à chaque vente.',
    'C''est le coût de "remplir ton restaurant". Si tu dépenses 500$ en flyers '
    'pour attirer 10 clients pour un dîner, chaque client t''a coûté 50$ à acquérir '
    'avant même qu''il commande.',
    'Une fintech africaine dépensait 15$ par téléchargement en publicité Facebook '
    'mais convertissait 5% des téléchargements en comptes actifs. Son CAC réel '
    'était donc de 300$ par client actif. Avec un LTV moyen de 80$, le modèle '
    'était structurellement non viable.',
    'Calculer le CAC par canal d''acquisition séparément. Inclure tous les coûts '
    '(salaires commerciaux, outils, publicité). Mettre à jour le calcul chaque mois.',
    'Oublier d''inclure les salaires de l''équipe commerciale dans le calcul. '
    'Calculer le CAC sur les inscriptions plutôt que sur les clients actifs. '
    'Ne pas segmenter le CAC par canal.',
    ARRAY['LTV', 'LTV/CAC Ratio', 'Churn', 'Unit Economics'],
    'CAC Too High, Negative Unit Economics, Cash Burn Too High',
    'Venture Hacks / David Skok — SaaS Metrics'
),

(
    'Lifetime Value',
    'metric',
    ARRAY['LTV', 'LCV', 'Valeur Vie Client', 'Customer Lifetime Value', 'CLV'],
    'Revenus nets totaux attendus d''un client sur toute la durée de sa relation '
    'avec l''entreprise, actualisés à la valeur présente. Calculé simplement comme '
    'ARPU × Marge brute / Taux de churn.',
    'C''est combien d''argent un client va te rapporter en tout, du premier jour '
    'jusqu''à ce qu''il arrête d''utiliser ton produit. Si un client paye 20$/mois '
    'et reste en moyenne 12 mois, son LTV est de 240$.',
    'C''est la valeur totale d''un abonné à un magazine. Si l''abonnement coûte '
    '10€/mois et que les gens restent abonnés 2 ans en moyenne, chaque abonné '
    'vaut 240€.',
    'Un SaaS B2B facture 200$/mois. Son churn mensuel est de 3%, ce qui donne '
    'une durée de vie moyenne de 33 mois. Sa marge brute est de 75%. '
    'LTV = 200 × 0.75 / 0.03 = 5 000$.',
    'Calculer le LTV par segment de clients. Intégrer la marge brute, pas le '
    'revenu brut. Mettre à jour régulièrement en fonction de l''évolution du churn.',
    'Utiliser le revenu brut au lieu de la marge nette. Ne pas segmenter par '
    'cohorte ou par plan. Surestimer le LTV en utilisant un churn trop optimiste.',
    ARRAY['CAC', 'LTV/CAC Ratio', 'Churn', 'MRR'],
    'Negative Unit Economics, High Churn Rate',
    'Venture Hacks / David Skok — SaaS Metrics'
),

(
    'Churn',
    'metric',
    ARRAY['Taux d''attrition', 'Churn Rate', 'Attrition'],
    'Pourcentage de clients ou de revenus récurrents perdus sur une période donnée. '
    'Le revenue churn mesure la perte de MRR ; le customer churn mesure la perte '
    'd''utilisateurs actifs. Un churn net négatif (expansion > attrition) est l''indicateur '
    'SaaS le plus puissant de product-market fit.',
    'C''est le pourcentage de tes clients qui arrêtent d''utiliser ton produit chaque '
    'mois. Si tu as 100 clients en janvier et que 5 partent, ton churn est de 5%. '
    'Plus ton churn est élevé, plus tu dois courir vite pour remplir le seau qui fuit.',
    'C''est un seau percé. Tu peux verser autant d''eau (nouveaux clients) que tu '
    'veux — si le trou est trop grand, le seau ne se remplit jamais. Il faut d''abord '
    'boucher les trous.',
    'Une app de fitness a 10 000 abonnés à 9,99$/mois. Son churn est de 8% par mois. '
    'Cela signifie qu''elle perd 800 abonnés chaque mois. Pour croître, elle doit '
    'acquérir plus de 800 nouveaux abonnés par mois, ce qui est très coûteux. '
    'En réduisant le churn à 3%, le besoin d''acquisition diminue de 62%.',
    'Mesurer le churn par cohorte (pas globalement). Distinguer churn volontaire '
    'et involontaire (échecs de paiement). Interviewer les clients qui partent.',
    'Mesurer le churn sur la base des inscrits totaux plutôt que des actifs. '
    'Masquer un churn élevé avec une croissance rapide. Ne pas interroger '
    'les clients qui partent.',
    ARRAY['LTV', 'MRR', 'Product-Market Fit', 'Retention'],
    'High Churn Rate, Low Product-Market Fit, Negative Unit Economics',
    'SaaS Metrics 2.0 — David Skok'
),

(
    'MRR',
    'metric',
    ARRAY['Monthly Recurring Revenue', 'Revenu Récurrent Mensuel', 'ARR'],
    'Revenu contractuellement récurrent normalisé sur une base mensuelle, excluant '
    'les revenus non-récurrents (frais d''installation, services ponctuels). '
    'Indicateur central de la santé d''un modèle par abonnement. '
    'MRR Net = MRR Nouveau + MRR Expansion - MRR Churné.',
    'C''est le montant d''argent que tu es quasi-certain de recevoir le mois prochain '
    'grâce à tes abonnés actuels. C''est le fondement prévisible de ton business — '
    'contrairement à des ventes ponctuelles qui peuvent varier d''un mois à l''autre.',
    'C''est comme un loyer que tu reçois en tant que propriétaire. Tu sais que tes '
    'locataires vont payer chaque mois. Les nouvelles ventes de maisons, c''est du '
    'bonus — mais le loyer, c''est ta base stable.',
    'Une startup SaaS a 50 clients à 100$/mois et 10 clients à 300$/mois. '
    'MRR = (50 × 100) + (10 × 300) = 8 000$/mois. ARR = 96 000$/an.',
    'Décomposer le MRR en : New MRR, Expansion MRR, Churned MRR, Reactivation MRR. '
    'Ne jamais inclure les revenus non-récurrents. Suivre la croissance '
    'mois-sur-mois en pourcentage.',
    'Inclure des contrats annuels payés en avance sans les lisser. '
    'Additionner les revenus de services avec le MRR. '
    'Comparer des MRR de périodes différentes sans ajustement saisonnier.',
    ARRAY['Churn', 'LTV', 'CAC', 'Unit Economics', 'ARR'],
    'High Churn Rate, Negative Unit Economics, Cash Burn Too High',
    'SaaS Metrics 2.0 — David Skok'
),

(
    'Burn Rate',
    'metric',
    ARRAY['Taux de consommation de trésorerie', 'Cash Burn'],
    'Vitesse à laquelle une startup consomme ses liquidités pour couvrir ses '
    'dépenses opérationnelles. Le gross burn est le total des dépenses mensuelles ; '
    'le net burn est la différence entre dépenses et revenus. '
    'Runway = Trésorerie disponible / Net Burn mensuel.',
    'C''est à quelle vitesse tu dépenses l''argent que tu as en banque. Si tu as '
    '100 000$ et que tu dépenses 10 000$ par mois de plus que ce que tu gagnes, '
    'tu as 10 mois avant de manquer d''argent. Ces 10 mois, c''est ton runway.',
    'C''est l''autonomie de carburant d''un avion. Si tu as du carburant pour '
    '10 heures de vol et que tu consommes à vitesse normale, tu dois atterrir '
    '(lever des fonds ou atteindre la rentabilité) avant les 10 heures.',
    'Une startup avec 500 000$ en banque a des coûts fixes de 60 000$/mois '
    '(salaires, bureaux, outils) et des revenus de 20 000$/mois. '
    'Net burn = 40 000$/mois. Runway = 500 000 / 40 000 = 12,5 mois.',
    'Suivre le net burn hebdomadairement, pas mensuellement. Modéliser des '
    'scénarios à 6, 9, 12 mois. Commencer à lever des fonds avec 6 mois '
    'de runway encore disponible.',
    'Confondre gross burn et net burn. Ne pas anticiper les pics de dépenses '
    '(recrutement, marketing). Attendre d''avoir 3 mois de runway pour lever.',
    ARRAY['Runway', 'CAC', 'Unit Economics', 'MRR'],
    'Cash Burn Too High, Premature Scaling',
    'Venture Deals — Brad Feld & Jason Mendelson'
),

-- ---------------------------------------------------------------------------
-- STRATÉGIES ET PRINCIPES
-- ---------------------------------------------------------------------------

(
    'Engine of Growth',
    'strategy',
    ARRAY['Moteur de croissance'],
    'Mécanisme systémique qui alimente la croissance durable d''une startup. '
    'Eric Ries en identifie trois : sticky (rétention, faible churn), viral '
    '(chaque utilisateur en amène de nouveaux, coefficient K > 1), '
    'paid (revenus > CAC, permet de réinvestir en acquisition).',
    'C''est le mécanisme principal qui fait grandir ton entreprise naturellement. '
    'Soit tes clients restent longtemps (sticky), soit ils en parlent à d''autres '
    '(viral), soit chaque euro dépensé en marketing en rapporte plus en retour (paid). '
    'Le problème : beaucoup de startups n''ont pas encore identifié leur moteur.',
    'C''est le moteur d''une voiture. Tu peux pousser la voiture (growth hacking '
    'ponctuel), mais sans moteur qui tourne tout seul, tu t''épuises.',
    'WhatsApp a utilisé le moteur viral : chaque utilisateur invitait ses contacts '
    'pour que l''app soit utile. Le coefficient viral était > 1 — chaque utilisateur '
    'amenait en moyenne plus d''un nouvel utilisateur. La croissance était '
    'quasi-automatique.',
    'Identifier et tester un seul moteur à la fois. Mesurer les indicateurs '
    'spécifiques à chaque moteur (coefficient K pour viral, churn pour sticky, '
    'LTV/CAC pour paid). Ne pas changer de moteur sans données.',
    'Croire avoir un moteur viral sans mesurer le coefficient K. Combiner '
    'plusieurs moteurs trop tôt. Confondre une campagne marketing avec '
    'un moteur de croissance.',
    ARRAY['Build-Measure-Learn', 'Pivot', 'CAC', 'LTV', 'Churn'],
    'No Scalable Growth Engine, Distribution Problem',
    'The Lean Startup — Eric Ries (2011)'
),

(
    'Unit Economics',
    'metric',
    ARRAY['Économie unitaire', 'Economics unitaires'],
    'Analyse de la rentabilité directe générée par une unité de base du modèle '
    'économique (un client, une transaction, une livraison). Détermine si le modèle '
    'est structurellement profitable à l''échelle. Indicateur central : ratio LTV/CAC '
    '(sain si > 3, excellent si > 5).',
    'C''est la réponse à : "Est-ce que je gagne de l''argent sur chaque client ?" '
    'Si tu dépenses 200$ pour acquérir un client qui ne te rapporte que 150$ en '
    'tout, peu importe combien tu grandis — tu perds de l''argent à chaque client. '
    'Scaler un modèle avec des unit economics négatifs, c''est accélérer vers '
    'la faillite.',
    'C''est vérifier si ton restaurant gagne de l''argent sur chaque repas servi. '
    'Si chaque pizza te coûte 12€ à préparer et que tu la vends 10€, '
    'vendre plus de pizzas empire la situation.',
    'Une marketplace de livraison a un panier moyen de 25$, prend 15% de commission '
    '(3,75$), paye un livreur 4$ par livraison, et a des coûts variables de 0,50$. '
    'Marge par transaction = 3,75 - 4 - 0,50 = -0,75$. Chaque livraison perd de '
    'l''argent. Le modèle ne fonctionne qu''à très grande échelle avec d''autres '
    'leviers économiques.',
    'Calculer les unit economics avec les coûts réels (pas optimisés). '
    'Tester différents prix et modèles de monétisation. Modéliser à quelle '
    'échelle les unit economics deviennent positifs.',
    'Calculer les unit economics sans les coûts d''acquisition. Croire que '
    'les unit economics s''amélioreront automatiquement avec l''échelle. '
    'Comparer avec des industries différentes.',
    ARRAY['CAC', 'LTV', 'MRR', 'Burn Rate', 'Churn'],
    'Negative Unit Economics, Cash Burn Too High, Premature Scaling',
    'Venture Hacks / David Skok — SaaS Metrics'
);
