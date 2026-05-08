-- =============================================================================
-- SEED : investment_criteria
-- Critères d'évaluation par profil d'investisseur et stade
-- Permet au modèle d'adapter son analyse selon le profil de l'utilisateur
-- =============================================================================

INSERT INTO investment_criteria
    (investor_profile, stage, criterion_name, criterion_category,
     weight, description, how_to_assess, ideal_answer,
     red_flags, green_flags, simple_explain)
VALUES

-- =============================================================================
-- ANGEL INVESTOR — PRE-SEED
-- Les angels investissent tôt, sur la vision et l'équipe plus que les chiffres
-- =============================================================================

('angel', 'pre-seed', 'Qualité de l''équipe fondatrice', 'team',
 'critical',
 'Évaluation des compétences, de la complémentarité, de la résilience et de la '
 'motivation des fondateurs. À ce stade, l''équipe est souvent le seul actif réel '
 'de la startup. Les angels cherchent des fondateurs qui ont une raison profonde '
 'et personnelle de résoudre ce problème.',
 'Poser la question "Pourquoi vous ?" et écouter la réponse. Chercher une connexion '
 'personnelle avec le problème. Évaluer si les fondateurs se complètent techniquement '
 'et commercialement. Vérifier l''historique de travail ensemble.',
 'Fondateurs avec une expérience directe du problème (utilisateurs du produit eux-mêmes). '
 'Complémentarité claire (tech + business). Historique de réalisation ensemble. '
 'Capacité à articuler clairement ce qu''ils ne savent pas encore.',
 'Fondateurs qui se sont rencontrés récemment sans historique de collaboration. '
 'Équipe mono-compétence (ex: 3 développeurs, 0 profil commercial). '
 'Motivation exclusivement financière. Incapacité à nommer leurs plus grands risques.',
 'Fondateurs avec une histoire personnelle forte avec le problème. '
 'Complémentarité évidente des compétences. Ont déjà travaillé ou réalisé quelque chose ensemble. '
 'Savent exactement ce qu''ils ne savent pas encore.',
 'L''ange mise sur les personnes avant tout. La question centrale est : '
 '"Ces personnes sont-elles les mieux placées pour résoudre ce problème, '
 'et vont-elles tenir quand ça deviendra difficile ?"'),

('angel', 'pre-seed', 'Clarté de la vision et du problème', 'market',
 'critical',
 'Capacité des fondateurs à articuler clairement et de manière convaincante '
 'quel problème ils résolvent, pour qui, et pourquoi maintenant. '
 'La précision de la définition du problème prédit souvent la qualité '
 'de l''exécution.',
 'Demander : "Décrivez votre client idéal et sa journée sans votre produit." '
 'Évaluer si les fondateurs ont passé du temps avec de vrais clients. '
 'Chercher des insights contre-intuitifs que les fondateurs ont découverts.',
 'Description précise du client idéal (persona, contexte, comportement). '
 'Insight non-évident sur le problème. Preuve que le problème a été validé '
 'directement avec des utilisateurs (interviews, observations).',
 'Description vague du client cible ("tout le monde peut utiliser ça"). '
 'Problème identifié uniquement par analogie ("Uber de X"). '
 'Aucune interaction directe avec des utilisateurs potentiels avant de pitcher.',
 'Insight surprenant et contre-intuitif sur le problème. '
 'Client cible décrit avec une précision chirurgicale. '
 'Fondateurs qui ont parlé à 20+ personnes du segment cible.',
 'Plus les fondateurs connaissent précisément leur client et son problème, '
 'plus ils ont de chances de construire quelque chose que les gens veulent vraiment. '
 'La vague ("on résout le problème de la logistique") est un signal d''alarme.'),

('angel', 'pre-seed', 'Taille de marché adressable', 'market',
 'important',
 'Estimation de la taille totale du marché adressable (TAM), du marché serviceable (SAM) '
 'et du marché cible réaliste (SOM). Les angels cherchent des marchés suffisamment '
 'grands pour justifier une startup (> 1 milliard $) mais pas irréalistes.',
 'Vérifier la méthode de calcul (bottom-up vs top-down). Questionner les hypothèses. '
 'Évaluer si le segment initial est assez grand pour atteindre un premier palier '
 'de revenus (1M$ ARR) avant d''élargir.',
 'Calcul bottom-up avec hypothèses documentées. TAM > 1Md$. '
 'Segment initial suffisamment concentré pour être pénétrable (SOM 0.1-1% du SAM). '
 'Logique d''expansion claire depuis le segment initial.',
 'TAM calculé par analogie sans données. Chiffres astronomiques sans logique '
 'de pénétration réaliste. Aucune réflexion sur le segment initial prioritaire.',
 'Calcul bottom-up rigoureux. Identification d''un beachhead market précis. '
 'Comparaison avec des marchés analogues similaires.',
 'La taille du marché doit être grande, mais le premier pas doit être petit et précis. '
 '"On s''attaque au marché global de la logistique africaine (50Md$)" '
 'sans expliquer par où commencer est un signal d''alarme.'),

('angel', 'pre-seed', 'Premiers signaux de traction', 'traction',
 'important',
 'Toute preuve — même minimale — que de vraies personnes veulent ce produit : '
 'liste d''attente, lettres d''intention, premiers clients payants, '
 'pré-commandes, interviews avec engagement fort.',
 'Chercher des preuves de demande réelle (argent, temps, effort de la part d''utilisateurs). '
 'Distinguer l''intérêt poli ("bonne idée !") de l''engagement réel '
 '(pré-paiement, signature de LOI).',
 'Premiers clients payants, même peu nombreux. Lettres d''intention signées. '
 'Liste d''attente avec engagement actif. Interviews où des prospects ont offert '
 'de payer avant que le produit existe.',
 'Traction uniquement via le réseau personnel sans potentiel de généralisation. '
 '"Tout le monde à qui on a parlé a adoré l''idée" sans validation monétaire. '
 'Aucune tentative de valider avant de pitcher.',
 'Un ou deux clients payants même à tarif réduit. '
 'Prospects qui ont demandé spontanément quand le produit sera disponible. '
 'Lettres d''intention signées par des décideurs (pas juste des utilisateurs).',
 'À ce stade très précoce, même un seul client payant vaut mieux '
 'que 100 personnes qui disent "super idée". L''argent dit la vérité '
 'là où les mots peuvent mentir.'),

-- =============================================================================
-- VENTURE CAPITAL — SEED
-- Les VCs seed cherchent une répétabilité et un potentiel de grande échelle
-- =============================================================================

('vc', 'seed', 'Product-Market Fit émergent', 'product',
 'critical',
 'Signes précoces mais mesurables d''une adéquation entre le produit et le marché : '
 'rétention, engagement, referrals organiques, NPS. Les VCs seed tolèrent '
 'l''absence de PMF solide mais cherchent des signaux clairs que la direction est la bonne.',
 'Analyser les métriques de cohorte (rétention à 30, 60, 90 jours). '
 'Mesurer le score de Sean Ellis (% très déçus si produit disparaît). '
 'Chercher une croissance organique même marginale.',
 'Rétention à 30 jours > 25% pour B2C, > 60% pour B2B. '
 'NPS > 30. Score Sean Ellis > 40%. '
 'Présence de referrals non-solicités dans les données d''acquisition.',
 'Croissance exclusivement payante sans rétention. '
 'NPS < 10 ou score Sean Ellis < 25%. '
 'Fondateurs incapables de présenter des métriques de cohorte.',
 'Cohortes avec rétention qui se stabilise (courbe plate, pas tombante à 0). '
 'Utilisateurs qui défendent le produit spontanément. '
 'Demandes entrantes sans prospection active.',
 'Le VC seed cherche un signal : les premiers utilisateurs reviennent-ils ? '
 'En parle-t-on autour d''eux ? Ce n''est pas parfait, mais la direction doit être claire.'),

('vc', 'seed', 'Modèle économique et unit economics', 'financials',
 'critical',
 'Compréhension claire du modèle de monétisation et des unit economics à l''échelle. '
 'Les VCs seed acceptent des unit economics encore négatifs mais cherchent '
 'une vision claire du chemin vers la profitabilité unitaire.',
 'Demander le calcul du CAC, du LTV et du payback period. '
 'Vérifier si les hypothèses sont basées sur des données réelles. '
 'Évaluer si le chemin vers des unit economics positifs est crédible.',
 'CAC calculé sur données réelles (pas projections). '
 'LTV/CAC > 1 ou chemin clair vers ce ratio. '
 'Modèle de monétisation testé avec de vrais clients payants.',
 'Absence totale de réflexion sur la monétisation. '
 '"On monétisera la data plus tard." '
 'Unit economics impossibles à améliorer structurellement (ex: coûts fixes incompressibles).',
 'LTV/CAC > 1 dès les premiers clients. '
 'Marges brutes > 50% avec potentiel d''amélioration claire. '
 'Modèle de pricing testé et validé avec des clients réels.',
 'Le VC seed veut savoir si tu comprends comment tu vas gagner de l''argent '
 'et si les chiffres peuvent fonctionner à grande échelle. '
 'Pas besoin d''être rentable — mais il faut un chemin crédible.'),

('vc', 'seed', 'Scalabilité du go-to-market', 'market',
 'critical',
 'Évaluation de la capacité des canaux d''acquisition actuels à fonctionner '
 'à une échelle 10x sans coûts proportionnels. Les VCs seed investissent '
 'en anticipant une levée Série A — ils évaluent donc le potentiel de scale.',
 'Analyser les canaux d''acquisition actuels et leur scalabilité. '
 'Évaluer si la croissance repose sur des canaux répétables ou sur '
 'le réseau personnel des fondateurs.',
 'Au moins un canal d''acquisition scalable identifié et testé (SEO, partnerships, PLG). '
 'CAC qui diminue avec l''échelle ou reste stable. '
 'Pipeline commercial avec leads entrants.',
 'Croissance entièrement due au réseau personnel des fondateurs. '
 'Aucun canal scalable testé. '
 'CAC qui augmente linéairement avec les efforts marketing.',
 'Croissance organique (SEO, referral, communauté) représentant > 30% de l''acquisition. '
 'Premier partenariat de distribution signé. '
 'Product-led growth émergent (virality intégrée dans le produit).',
 'Le VC se demande : "Est-ce que ça peut croître 10x ?" '
 'Si la réponse implique de multiplier les commerciaux par 10, '
 'c''est moins attrayant que si le produit se vend partiellement tout seul.'),

-- =============================================================================
-- IMPACT INVESTOR — SEED
-- Les investisseurs à impact ajoutent une dimension sociale/environnementale
-- =============================================================================

('impact', 'seed', 'Clarté de la théorie du changement', 'market',
 'critical',
 'Articulation précise et mesurable de la chaîne causale entre les activités '
 'de la startup et l''impact social ou environnemental ciblé. '
 'Les investisseurs impact exigent une logique d''impact aussi rigoureuse '
 'que la logique financière.',
 'Demander : "Quel est le problème social que vous résolvez, pour combien de personnes, '
 'et comment mesurez-vous votre impact ?" Évaluer si les métriques d''impact '
 'sont définies, mesurées et reportées.',
 'Théorie du changement documentée avec inputs → activités → outputs → outcomes → impact. '
 'KPIs d''impact définis, mesurés et cohérents avec des standards reconnus (IRIS+, SDGs). '
 'Données de terrain sur l''impact réel (pas seulement estimations).',
 'Impact affirmé sans métriques. '
 '"On va changer des millions de vies" sans données. '
 'Confusion entre output (ce qu''on produit) et impact (ce qui change dans le monde).',
 'Métriques d''impact alignées sur des standards reconnus. '
 'Données terrain prouvant l''impact sur un échantillon représentatif. '
 'Fondateurs qui ont vécu le problème qu''ils résolvent.',
 'L''investisseur impact cherche la même rigueur que pour les finances, '
 'mais appliquée à l''impact. "On aide les agriculteurs" n''est pas une théorie du changement. '
 '"On réduit de 25% le coût des intrants pour 5 000 agriculteurs dans 3 régions" l''est.'),

('impact', 'seed', 'Viabilité financière et durabilité', 'financials',
 'critical',
 'Capacité du modèle économique à générer une rentabilité suffisante pour '
 'se pérenniser sans dépendance perpétuelle aux subventions ou aux dons. '
 'Les investisseurs impact cherchent des modèles "autosuffisants" à terme.',
 'Évaluer la part des revenus provenant de vrais clients (vs subventions). '
 'Modéliser le chemin vers l''autosuffisance financière. '
 'Analyser si l''impact et la viabilité financière sont alignés ou en tension.',
 'Revenus commerciaux représentant > 50% du financement. '
 'Chemin clair vers la rentabilité opérationnelle à 3-5 ans. '
 'Impact et viabilité financière naturellement alignés (plus de clients = plus d''impact).',
 'Dépendance > 80% aux grants et subventions. '
 'Modèle économique qui nécessite un prix subventionné indéfiniment. '
 'Impact et revenus en tension structurelle (servir les plus pauvres = moins de revenus).',
 'Revenus commerciaux croissants avec une trajectoire claire vers l''autosuffisance. '
 'Alignement naturel entre acquisition de clients et création d''impact.',
 'L''investisseur impact ne veut pas financer une ONG déguisée en startup. '
 'Il cherche un modèle où faire du bien ET faire des affaires sont la même chose, '
 'pas deux objectifs contradictoires.'),

-- =============================================================================
-- VC — SERIES A
-- À ce stade, les données doivent valider l'hypothèse de croissance massive
-- =============================================================================

('vc', 'series-a', 'Preuve de Product-Market Fit solide', 'product',
 'critical',
 'Validation robuste et mesurée de l''adéquation produit-marché sur un segment '
 'défini, avec des métriques de rétention, d''engagement et de NPS supérieures '
 'aux benchmarks sectoriels. À Série A, l''absence de PMF est rédhibitoire.',
 'Analyser les métriques de cohorte sur 6-12 mois. '
 'Vérifier la rétention à 90 et 180 jours. '
 'Demander le score Sean Ellis et le NPS. '
 'Évaluer si la croissance est principalement organique.',
 'Rétention à 90 jours > 40% (B2C) ou > 70% (B2B). '
 'NPS > 50. Score Sean Ellis > 50%. '
 'Croissance organique représentant > 40% de l''acquisition.',
 'Métriques de rétention inférieures aux benchmarks sectoriels. '
 'Croissance entièrement payante sans rétention. '
 'Churn mensuel > 3% en B2B.',
 'Courbes de rétention qui se stabilisent à un niveau élevé (pas de déclin infini). '
 'Expansion revenue (upsell) qui dépasse le churn (Net Revenue Retention > 110%). '
 'Utilisateurs qui utiliseraient leur propre argent si l''entreprise disparaissait.',
 'En Série A, le VC ne cherche plus un signal — il cherche une preuve. '
 'Les métriques doivent montrer clairement que les clients adorent le produit '
 'et ne veulent plus s''en passer.'),

('vc', 'series-a', 'Équipe de management scalable', 'team',
 'critical',
 'Présence d''une équipe de direction capable de gérer une organisation '
 'en forte croissance : recrutement, culture, délégation, décision dans '
 'l''ambiguïté. Les fondateurs doivent avoir montré qu''ils peuvent passer '
 'de "tout faire soi-même" à "construire une équipe".',
 'Évaluer qui a été recruté depuis le dernier tour. '
 'Demander comment les fondateurs délèguent et prennent les décisions. '
 'Chercher des preuves de culture organisationnelle intentionnelle.',
 'Premier VP Engineering, VP Sales ou COO recruté avec succès. '
 'Processus de recrutement documenté et répétable. '
 'Fondateurs qui peuvent articuler clairement ce qu''ils ont délégué.',
 'Fondateurs qui font encore tout eux-mêmes à 30 employés. '
 'Turn-over élevé dans l''équipe de direction. '
 'Absence de processus formalisés (OKRs, 1:1, performance reviews).',
 'Premières hires de direction de qualité institutionnelle. '
 'Culture d''entreprise documentée et visible dans les pratiques quotidiennes. '
 'Fondateurs qui ont su identifier et recruter des personnes meilleures qu''eux.',
 'En Série A, le VC sait que l''entreprise va tripler ou quadrupler en 18 mois. '
 'Il cherche des fondateurs capables de construire et diriger une organisation, '
 'pas seulement de construire un produit.'),

('vc', 'series-a', 'Go-to-market répétable et scalable', 'market',
 'critical',
 'Démonstration d''un processus d''acquisition client répétable avec des coûts '
 'prévisibles et des canaux qui scalent. Le playbook commercial doit être '
 'documenté et réplicable par de nouvelles recrues.',
 'Analyser le CAC par canal et son évolution dans le temps. '
 'Évaluer si le cycle de vente est documenté et reproductible. '
 'Demander le ratio Sales Efficiency (ARR gagné / dépenses S&M).',
 'CAC stable ou décroissant avec l''augmentation du budget. '
 'Cycle de vente documenté avec étapes et durée prévisibles. '
 'Sales Efficiency > 0.8 (ideally > 1).',
 'CAC qui augmente avec le budget marketing. '
 'Dépendance aux relationships personnelles des fondateurs pour closer les deals. '
 'Aucune documentation du processus commercial.',
 'CAC en baisse sur les 6 derniers mois malgré l''augmentation du budget. '
 'Premier commercial recruté qui performe aussi bien que les fondateurs. '
 'Plusieurs canaux d''acquisition fonctionnels et mesurés.',
 'Le VC Série A veut mettre de l''argent dans un moteur qui tourne déjà. '
 'Il ne finance pas la découverte du GTM — il finance l''accélération '
 'd''un GTM qui a prouvé son fonctionnement.');
