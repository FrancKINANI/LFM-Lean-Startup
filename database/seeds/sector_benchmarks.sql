-- =============================================================================
-- SEED : sector_benchmarks
-- Métriques de référence par secteur et stade
-- Permettent au modèle de répondre à : "Ce chiffre est-il normal ?"
-- =============================================================================

INSERT INTO sector_benchmarks
    (sector, stage, metric_name, value_median, value_good, value_excellent,
     value_warning, unit, context,
     interpretation_good, interpretation_bad,
     source, reference_year)
VALUES

-- =============================================================================
-- SAAS B2B
-- =============================================================================

('saas', 'seed', 'churn_monthly',       3.0,  2.0,  1.0,  5.0,  '%',
 'Pourcentage de clients ou de MRR perdus chaque mois. Inclut les résiliations volontaires et les échecs de paiement.',
 'Un churn mensuel < 2% en B2B SaaS indique un produit bien ancré dans les workflows clients. À ce niveau, la croissance nette est réellement possible avec une acquisition modeste.',
 'Un churn > 5% mensuel en B2B est un signal fort de problème de product-market fit ou de mauvaise adéquation entre le segment cible et le produit. L''acquisition seule ne peut pas compenser.',
 'SaaS Metrics 2.0 — David Skok / OpenView Partners', 2024),

('saas', 'seed', 'ltv_cac_ratio',       2.5,  3.0,  5.0,  1.5,  'ratio',
 'Ratio entre la valeur totale générée par un client (LTV) et le coût pour l''acquérir (CAC). Indicateur central de la viabilité économique d''un modèle SaaS.',
 'Un ratio LTV/CAC > 3 signifie que chaque euro investi en acquisition en rapporte 3 de valeur. C''est le seuil standard pour justifier l''accélération de la croissance.',
 'Un ratio < 1.5 signifie que l''entreprise détruit de la valeur à chaque client acquis. Scaler dans ces conditions accélère la destruction de trésorerie.',
 'SaaS Metrics 2.0 — David Skok', 2024),

('saas', 'seed', 'cac_payback_months',  18.0, 12.0,  6.0, 24.0, 'months',
 'Nombre de mois nécessaires pour récupérer le coût d''acquisition d''un client via sa marge brute. Indicateur clé pour évaluer l''efficience du go-to-market.',
 'Un payback < 12 mois en B2B SaaS indique un modèle capable de s''autofinancer rapidement. Certains leaders du secteur atteignent 6 mois.',
 'Un payback > 24 mois expose la startup à un risque de trésorerie élevé. Avec un churn de 3%/mois, certains clients partent avant même d''avoir été remboursés.',
 'Bessemer Venture Partners — State of the Cloud', 2024),

('saas', 'seed', 'mrr_growth_monthly',  10.0, 15.0, 20.0,  5.0, '%',
 'Croissance mensuelle du MRR (revenus récurrents mensuels), exprimant la vélocité de croissance du revenu récurrent.',
 'Une croissance MRR > 15% mensuel en phase seed est considérée excellente et correspond à ce que les VCs qualifient de "triple triple double" sur plusieurs années.',
 'Une croissance < 5% mensuel en seed indique soit un problème de PMF, soit un go-to-market insuffisant. En dessous de ce seuil, atteindre une taille significative prend trop longtemps.',
 'YC Benchmark / Stripe Atlas Startup Data', 2024),

('saas', 'seed', 'nps',                 35.0, 50.0, 70.0, 20.0, 'score',
 'Net Promoter Score : mesure la probabilité que les clients recommandent le produit (score de 0 à 10). NPS = % Promoteurs (9-10) - % Détracteurs (0-6).',
 'Un NPS > 50 en SaaS indique une forte satisfaction et un moteur de croissance organique (referrals). C''est un signal de product-market fit fort.',
 'Un NPS < 20 indique que les clients sont neutres ou insatisfaits. La croissance devra être entièrement financée par l''acquisition payante, sans referral.',
 'Satmetrix NPS Benchmarks / Bain & Company', 2024),

('saas', 'series-a', 'gross_margin',    70.0, 75.0, 85.0, 60.0, '%',
 'Pourcentage des revenus restant après déduction des coûts directs (infrastructure, support client, coût de livraison du service). Indique la scalabilité du modèle.',
 'Une marge brute > 75% est le standard SaaS Series A. Elle indique que le modèle est scalable : chaque nouveau dollar de revenu coûte moins de 25 cents à produire.',
 'Une marge brute < 60% en SaaS signale souvent une composante services trop importante, une infrastructure sous-optimisée, ou un modèle hybride difficile à scaler.',
 'OpenView Partners SaaS Benchmarks Report', 2024),

('saas', 'series-a', 'rule_of_40',      40.0, 50.0, 60.0, 30.0, 'score',
 'Indicateur de santé SaaS = Taux de croissance ARR (%) + Marge d''exploitation (%). Un score > 40 indique un équilibre sain entre croissance et rentabilité.',
 'Un score > 50 place la startup dans le top quartile des SaaS Series A. Les investisseurs l''utilisent pour évaluer si la croissance est durable.',
 'Un score < 30 signale soit une croissance trop lente, soit des pertes trop importantes pour être justifiées. C''est souvent le signal d''une révision du modèle nécessaire.',
 'McKinsey Software Growth Report', 2024),

-- =============================================================================
-- MARKETPLACE
-- =============================================================================

('marketplace', 'pre-seed', 'gmv_growth_monthly', 15.0, 25.0, 40.0, 8.0, '%',
 'Croissance mensuelle du Gross Merchandise Volume (valeur totale des transactions réalisées sur la plateforme). Indicateur de traction de la marketplace.',
 'Une croissance GMV > 25% mensuel en pré-seed indique que la plateforme résout un problème réel et que les deux côtés s''engagent. C''est le signal de viabilité le plus fort.',
 'Une croissance < 8% mensuel en pré-seed sur une marketplace suggère un problème de cold start non résolu ou un manque de valeur ajoutée par rapport aux alternatives.',
 'Andreessen Horowitz Marketplace Report', 2024),

('marketplace', 'pre-seed', 'take_rate',            12.0, 15.0, 20.0, 8.0, '%',
 'Pourcentage du GMV retenu par la plateforme comme commission. Varie fortement selon le secteur (3-5% pour le e-commerce généraliste, 15-30% pour les services).',
 'Un take rate > 15% indique que la plateforme crée suffisamment de valeur pour que les deux parties acceptent de partager une part significative de la transaction.',
 'Un take rate < 8% rend difficile la construction d''un modèle économique viable à moins d''atteindre des volumes très élevés. Souvent le signe d''une pression concurrentielle forte.',
 'a16z Marketplace 100', 2024),

('marketplace', 'seed', 'liquidity_rate',           20.0, 35.0, 50.0, 10.0, '%',
 'Pourcentage des offres disponibles qui résultent en une transaction dans un délai donné. Indicateur de la santé des deux côtés de la marketplace.',
 'Un taux de liquidité > 35% indique que l''offre et la demande sont bien équilibrées. La marketplace remplit sa fonction de matching efficacement.',
 'Un taux < 10% signale un déséquilibre grave entre offre et demande, ou une inadéquation entre ce que propose l''offre et ce que cherche la demande.',
 'Andreessen Horowitz Marketplace Report', 2024),

('marketplace', 'seed', 'repeat_transaction_rate',  40.0, 55.0, 70.0, 25.0, '%',
 'Pourcentage de clients ayant réalisé plus d''une transaction sur la plateforme dans les 90 jours suivant leur première commande. Indicateur de rétention et de valeur perçue.',
 'Un taux de répétition > 55% indique que les utilisateurs trouvent suffisamment de valeur pour revenir spontanément. C''est le signe d''un moteur de croissance "sticky" émergent.',
 'Un taux < 25% signale que la marketplace est utilisée de manière ponctuelle, sans créer de dépendance. La croissance nécessite une acquisition continue très coûteuse.',
 'Lenny Rachitsky — Marketplace Retention Benchmarks', 2024),

-- =============================================================================
-- FINTECH
-- =============================================================================

('fintech', 'pre-seed', 'kyc_completion_rate',  65.0, 75.0, 85.0, 50.0, '%',
 'Pourcentage d''utilisateurs ayant complété le processus de vérification d''identité (KYC) parmi ceux qui ont initié l''inscription. Révèle la fluidité de l''onboarding.',
 'Un taux > 75% indique un processus KYC bien conçu, fluide et adapté aux contraintes des utilisateurs (documents disponibles, connexion, compréhension).',
 'Un taux < 50% signale un onboarding trop complexe ou des exigences documentaires inadaptées au segment cible. C''est une fuite majeure dans le tunnel d''acquisition.',
 'Fintech Africa Report — Quona Capital', 2024),

('fintech', 'seed', 'transaction_frequency',    2.5,  4.0,  8.0,  1.5,  'times/month',
 'Nombre moyen de transactions par utilisateur actif par mois. Indique l''engagement et l''intégration du service dans les habitudes financières de l''utilisateur.',
 'Une fréquence > 4 transactions/mois indique que le service est intégré dans les habitudes financières régulières. C''est le signal d''un moteur de rétention fort.',
 'Une fréquence < 1.5 transactions/mois signale une utilisation occasionnelle, souvent symptomatique d''une proposition de valeur trop étroite.',
 'GSMA Mobile Money Report', 2024),

('fintech', 'seed', 'default_rate',              3.0,  2.0,  1.0,  6.0,  '%',
 'Pourcentage de prêts ou de transactions de crédit qui ne sont pas remboursés. Indicateur central du risque de crédit pour les fintechs de lending.',
 'Un taux de défaut < 2% en micro-crédit digital indique un scoring efficace et une sélection de clientèle rigoureuse. C''est le niveau requis pour des unit economics positifs.',
 'Un taux > 6% rend les unit economics structurellement négatifs pour la plupart des modèles de micro-crédit. Il faut revoir le modèle de scoring ou la cible.',
 'Accion Venture Lab Portfolio Data', 2024),

-- =============================================================================
-- AGRITECH / MARCHÉS ÉMERGENTS
-- =============================================================================

('agritech', 'seed', 'farmer_adoption_rate',    15.0, 25.0, 40.0,  8.0, '%',
 'Pourcentage d''agriculteurs ayant adopté et utilisé activement le service dans une zone de déploiement cible après 6 mois de présence. Indicateur de penetration locale.',
 'Un taux > 25% dans une zone ciblée après 6 mois indique que le service répond à un besoin réel et que la distribution fonctionne. C''est le niveau requis pour passer à une zone suivante.',
 'Un taux < 8% signale soit un problème de valeur perçue, soit des barrières à l''adoption non résolues (prix, complexité, confiance). Scaler avant ce seuil est risqué.',
 'Acumen / Dalberg Agri-Fintech Report', 2024),

('agritech', 'seed', 'input_cost_reduction',    15.0, 20.0, 30.0,  8.0, '%',
 'Réduction du coût des intrants agricoles (semences, engrais, pesticides) obtenue par les agriculteurs grâce au service, par rapport aux canaux traditionnels.',
 'Une réduction > 20% est suffisamment significative pour déclencher l''adoption spontanée et le bouche-à-oreille entre agriculteurs. C''est un moteur de croissance viral.',
 'Une réduction < 8% ne justifie pas le changement de comportement pour la plupart des agriculteurs, surtout si le service implique un effort d''adoption (smartphone, etc.).',
 'GSMA AgriTech Report / IFC', 2024),

-- =============================================================================
-- EDTECH
-- =============================================================================

('edtech', 'seed', 'course_completion_rate',   35.0, 50.0, 70.0, 20.0, '%',
 'Pourcentage d''apprenants qui complètent un cours ou programme jusqu''à la fin. Indicateur clé de l''engagement et de la valeur perçue du contenu.',
 'Un taux > 50% est excellent en edtech et indique une forte pertinence du contenu et un bon design pédagogique. Coursera et edX se situent en général à 5-15% — le seuil est donc relatif au format.',
 'Un taux < 20% signale soit un problème de pertinence du contenu, soit un mauvais ciblage des apprenants, soit un design pédagogique insuffisant.',
 'Class Central Edtech Report', 2024),

('edtech', 'seed', 'b2b_contract_renewal_rate', 70.0, 80.0, 90.0, 60.0, '%',
 'Pourcentage d''entreprises clientes qui renouvellent leur contrat annuel. Indicateur de la valeur perçue par les acheteurs institutionnels (RH, responsables formation).',
 'Un taux > 80% en B2B EdTech indique que les acheteurs voient un ROI clair. C''est aussi le niveau requis pour construire un modèle de revenus prévisible.',
 'Un taux < 60% signale que les clients ne voient pas de ROI suffisant pour justifier le renouvellement. Revenir sur la proposition de valeur et les métriques de succès.',
 'HolonIQ EdTech Report', 2024),

-- =============================================================================
-- HEALTHTECH
-- =============================================================================

('healthtech', 'seed', 'patient_adherence_rate', 45.0, 60.0, 75.0, 30.0, '%',
 'Pourcentage de patients qui suivent le programme de soin ou de suivi recommandé sur 90 jours. Indicateur d''impact réel du service sur les comportements de santé.',
 'Un taux > 60% indique que le service améliore réellement les comportements de santé, ce qui est à la fois un indicateur d''impact et de rétention.',
 'Un taux < 30% signale que le service ne s''intègre pas suffisamment dans les habitudes du patient. C''est souvent un problème de UX, de fréquence de contact ou de pertinence.',
 'Rock Health Digital Health Report', 2024),

('healthtech', 'seed', 'provider_adoption_rate', 20.0, 35.0, 50.0, 10.0, '%',
 'Pourcentage de professionnels de santé (médecins, infirmiers) qui utilisent activement le service dans leur pratique après 3 mois de déploiement.',
 'Un taux > 35% parmi les praticiens ciblés indique que le service s''intègre dans leur workflow. C''est le seuil à partir duquel la croissance organique (referrals entre praticiens) peut s''enclencher.',
 'Un taux < 10% indique des frictions fortes à l''adoption : trop complexe, pas intégré aux outils existants, ou valeur insuffisante pour le praticien lui-même.',
 'Rock Health Digital Health Report', 2024);
