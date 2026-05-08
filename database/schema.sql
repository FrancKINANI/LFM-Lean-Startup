-- =============================================================================
-- LFM Lean Startup — Schéma PostgreSQL
-- =============================================================================
-- Organisation : 6 tables réparties en deux groupes
--
-- GROUPE CONNAISSANCE (cas et patterns issus de l'expérience réelle)
--   1. startups            — cas documentés de startups
--   2. pivot_cases         — pivots avec contexte et résultats
--   3. risk_patterns       — patterns de risque par secteur et stade
--
-- GROUPE RÉFÉRENCE (données de calibrage et frameworks)
--   4. sector_benchmarks   — métriques de référence par secteur et stade
--   5. lean_concepts       — concepts Lean Startup avec double explication
--   6. investment_criteria — critères d'évaluation par profil d'investisseur
-- =============================================================================


-- -----------------------------------------------------------------------------
-- EXTENSIONS
-- -----------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUIDs si besoin ultérieur
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- Recherche textuelle fuzzy


-- -----------------------------------------------------------------------------
-- TYPES ÉNUMÉRÉS
-- Centraliser les valeurs autorisées évite les fautes de frappe dans les seeds
-- et les requêtes du modèle
-- -----------------------------------------------------------------------------

CREATE TYPE startup_stage AS ENUM (
    'idea',
    'pre-seed',
    'seed',
    'series-a',
    'series-b',
    'growth',
    'mature'
);

CREATE TYPE startup_outcome AS ENUM (
    'success',
    'failure',
    'pivot',
    'acquired',
    'ongoing'
);

CREATE TYPE risk_criticality AS ENUM (
    'critical',
    'high',
    'medium',
    'low'
);

CREATE TYPE investor_profile AS ENUM (
    'angel',
    'vc',
    'impact',
    'strategic',
    'crowdfunding'
);

CREATE TYPE criterion_weight AS ENUM (
    'critical',
    'important',
    'nice-to-have'
);

CREATE TYPE lean_category AS ENUM (
    'framework',
    'metric',
    'strategy',
    'principle',
    'tool'
);


-- =============================================================================
-- GROUPE CONNAISSANCE
-- =============================================================================


-- -----------------------------------------------------------------------------
-- TABLE 1 : startups
-- Cas documentés de startups, réels ou construits pour l'entraînement.
-- Chaque entrée est un cas d'étude que le modèle peut interroger pour
-- trouver des analogies avec la startup analysée.
-- -----------------------------------------------------------------------------

CREATE TABLE startups (
    id                  SERIAL PRIMARY KEY,

    -- Identité
    name                VARCHAR(255)        NOT NULL,
    sector              VARCHAR(100)        NOT NULL,   -- 'marketplace', 'saas', 'fintech'...
    subsector           VARCHAR(100),                   -- 'b2b-saas', 'agritech'...
    stage               startup_stage       NOT NULL,
    region              VARCHAR(100),                   -- 'afrique_subsaharienne', 'europe'...
    country             VARCHAR(100),
    founding_year       INTEGER,

    -- Équipe
    team_size           INTEGER,
    founding_team_desc  TEXT,               -- description libre de l'équipe fondatrice

    -- Modèle économique
    description         TEXT        NOT NULL,           -- description libre du projet
    business_model      VARCHAR(100),                   -- 'subscription', 'commission', 'freemium'...
    target_customer     TEXT,                           -- qui est le client cible
    value_proposition   TEXT,                           -- quelle valeur est créée

    -- Traction au moment documenté
    mrr                 NUMERIC(12, 2),                 -- Monthly Recurring Revenue (USD)
    user_count          INTEGER,
    transaction_count   INTEGER,
    growth_rate_monthly NUMERIC(5, 2),                  -- taux de croissance mensuel en %

    -- Résultat final
    outcome             startup_outcome     NOT NULL,
    outcome_details     TEXT,                           -- ce qui s'est passé concrètement
    key_learnings       TEXT,                           -- leçons extraites pour le modèle

    -- Métadonnées
    source              VARCHAR(255),                   -- origine de l'information
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Index pour les requêtes fréquentes du modèle
CREATE INDEX idx_startups_sector       ON startups(sector);
CREATE INDEX idx_startups_stage        ON startups(stage);
CREATE INDEX idx_startups_outcome      ON startups(outcome);
CREATE INDEX idx_startups_region       ON startups(region);
CREATE INDEX idx_startups_sector_stage ON startups(sector, stage);

-- Index full-text pour recherche sémantique sur la description
CREATE INDEX idx_startups_description_trgm
    ON startups USING gin(description gin_trgm_ops);


-- -----------------------------------------------------------------------------
-- TABLE 2 : pivot_cases
-- Pivots documentés avec leur contexte, déclencheur et résultat.
-- Permet au modèle de répondre à : "A-t-on déjà vu une startup dans
-- cette situation pivoter avec succès ? Comment ?"
-- -----------------------------------------------------------------------------

CREATE TABLE pivot_cases (
    id                  SERIAL PRIMARY KEY,

    startup_id          INTEGER REFERENCES startups(id) ON DELETE CASCADE,

    -- Classification du pivot (taxonomie Lean Startup d'Eric Ries)
    pivot_type          VARCHAR(100)    NOT NULL,
    -- Valeurs possibles :
    -- 'zoom-in'            : une feature devient le produit entier
    -- 'zoom-out'           : le produit entier devient une feature
    -- 'customer-segment'   : même problème, client différent
    -- 'customer-need'      : même client, problème différent
    -- 'platform'           : d'application à plateforme (ou inverse)
    -- 'business-architecture' : volume élevé/marge faible → marge élevée/volume faible
    -- 'value-capture'      : changement du modèle de monétisation
    -- 'engine-of-growth'   : changement du moteur de croissance
    -- 'channel'            : changement du canal de distribution
    -- 'technology'         : même résultat, technologie différente

    -- Contexte du pivot
    bml_cycle_number    INTEGER,                -- à quel cycle BML le pivot s'est produit
    trigger_signal      TEXT        NOT NULL,   -- ce qui a déclenché le pivot
    trigger_metric      VARCHAR(100),           -- la métrique qui a alerté
    trigger_value       NUMERIC,                -- valeur de cette métrique au moment du pivot

    -- Avant / Après
    before_model        TEXT        NOT NULL,   -- modèle économique avant le pivot
    after_model         TEXT        NOT NULL,   -- modèle économique après le pivot
    pivot_duration_days INTEGER,                -- durée de la transition

    -- Résultat
    outcome             startup_outcome NOT NULL,
    outcome_details     TEXT,
    key_learnings       TEXT,

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pivot_startup    ON pivot_cases(startup_id);
CREATE INDEX idx_pivot_type       ON pivot_cases(pivot_type);
CREATE INDEX idx_pivot_outcome    ON pivot_cases(outcome);


-- -----------------------------------------------------------------------------
-- TABLE 3 : risk_patterns
-- Patterns de risque connus, classés par secteur, stade et criticité.
-- C'est la table centrale pour la détection des dangers.
-- Le modèle l'interroge pour identifier les risques applicables
-- à une startup donnée et les expliquer simplement.
-- -----------------------------------------------------------------------------

CREATE TABLE risk_patterns (
    id                  SERIAL PRIMARY KEY,

    -- Classification
    pattern_name        VARCHAR(255)        NOT NULL,
    sector              VARCHAR(100),                   -- NULL = applicable à tous les secteurs
    stage               startup_stage,                  -- NULL = applicable à tous les stades
    criticality         risk_criticality    NOT NULL,
    category            VARCHAR(100),
    -- Catégories possibles :
    -- 'market'         : risques liés au marché
    -- 'team'           : risques liés à l'équipe
    -- 'product'        : risques liés au produit
    -- 'financial'      : risques financiers
    -- 'execution'      : risques d'exécution
    -- 'regulatory'     : risques réglementaires
    -- 'competition'    : risques concurrentiels

    -- Double niveau d'explication
    description         TEXT        NOT NULL,   -- explication technique (niveau whitepaper)
    simple_explain      TEXT        NOT NULL,   -- explication accessible (niveau entrepreneur)

    -- Détection et réponse
    warning_signals     TEXT        NOT NULL,   -- signaux concrets qui indiquent ce risque
    example_case        TEXT,                   -- exemple réel ou fictif illustratif
    mitigation          TEXT        NOT NULL,   -- comment atténuer ce risque
    mitigation_simple   TEXT,                   -- version simplifiée de la mitigation

    -- Impact potentiel
    impact_on_runway    VARCHAR(50),            -- 'kills_company', 'critical', 'significant', 'moderate'
    time_to_impact      VARCHAR(100),           -- 'immediate', '1-3 months', '3-6 months', 'long-term'

    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_risk_sector       ON risk_patterns(sector);
CREATE INDEX idx_risk_stage        ON risk_patterns(stage);
CREATE INDEX idx_risk_criticality  ON risk_patterns(criticality);
CREATE INDEX idx_risk_category     ON risk_patterns(category);
CREATE INDEX idx_risk_sector_stage ON risk_patterns(sector, stage);

-- Index pour requêtes du modèle sans filtre secteur (patterns universels)
CREATE INDEX idx_risk_null_sector  ON risk_patterns(stage) WHERE sector IS NULL;


-- =============================================================================
-- GROUPE RÉFÉRENCE
-- =============================================================================


-- -----------------------------------------------------------------------------
-- TABLE 4 : sector_benchmarks
-- Métriques de référence par secteur et stade.
-- Permet au modèle de répondre à : "Est-ce que ce chiffre est normal
-- pour une startup à ce stade dans ce secteur ?"
-- -----------------------------------------------------------------------------

CREATE TABLE sector_benchmarks (
    id                  SERIAL PRIMARY KEY,

    -- Classification
    sector              VARCHAR(100)    NOT NULL,
    stage               startup_stage   NOT NULL,
    metric_name         VARCHAR(100)    NOT NULL,
    -- Métriques possibles :
    -- 'conversion_rate', 'churn_monthly', 'cac', 'ltv', 'ltv_cac_ratio',
    -- 'mrr_growth_monthly', 'burn_rate', 'runway_months',
    -- 'nps', 'dau_mau_ratio', 'gross_margin'

    -- Valeurs de référence
    value_median        NUMERIC,                -- valeur médiane du secteur
    value_good          NUMERIC,                -- seuil "bonne performance"
    value_excellent     NUMERIC,                -- seuil "excellente performance"
    value_warning       NUMERIC,                -- seuil d'alerte
    unit                VARCHAR(50)     NOT NULL,   -- '%', 'USD', 'months', 'ratio'

    -- Interprétation
    context             TEXT            NOT NULL,   -- ce que ce chiffre signifie concrètement
    interpretation_good TEXT,                       -- comment interpréter une bonne valeur
    interpretation_bad  TEXT,                       -- comment interpréter une mauvaise valeur

    -- Fiabilité de la donnée
    source              VARCHAR(255),
    sample_size         INTEGER,                    -- nombre de startups dans l'échantillon
    reference_year      INTEGER,

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_benchmark_unique
    ON sector_benchmarks(sector, stage, metric_name);

CREATE INDEX idx_benchmark_sector_stage
    ON sector_benchmarks(sector, stage);


-- -----------------------------------------------------------------------------
-- TABLE 5 : lean_concepts
-- Concepts du Lean Startup avec double niveau d'explication.
-- Permet au modèle de rendre accessible ce que les whitepapers
-- rendent opaque — mission centrale du projet.
-- -----------------------------------------------------------------------------

CREATE TABLE lean_concepts (
    id                  SERIAL PRIMARY KEY,

    -- Identification
    concept_name        VARCHAR(255)    NOT NULL UNIQUE,
    category            lean_category   NOT NULL,
    aliases             TEXT[],                     -- noms alternatifs du concept

    -- Double niveau d'explication
    technical_def       TEXT            NOT NULL,   -- définition issue des whitepapers
    simple_def          TEXT            NOT NULL,   -- explication accessible sans jargon
    analogy             TEXT,                       -- analogie du quotidien pour illustrer

    -- Application pratique
    example             TEXT            NOT NULL,   -- exemple concret avec une startup fictive
    how_to_apply        TEXT,                       -- comment l'appliquer concrètement
    common_mistakes     TEXT,                       -- erreurs fréquentes sur ce concept

    -- Relations
    related_concepts    TEXT[],                     -- noms des concepts connexes
    related_risks       TEXT,                       -- risques liés à ce concept

    -- Références
    source_whitepaper   VARCHAR(255),               -- whitepaper ou livre source
    source_page         VARCHAR(50),

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_concepts_category ON lean_concepts(category);
CREATE INDEX idx_concepts_name_trgm
    ON lean_concepts USING gin(concept_name gin_trgm_ops);


-- -----------------------------------------------------------------------------
-- TABLE 6 : investment_criteria
-- Critères d'évaluation d'investissement par profil d'investisseur et stade.
-- Permet au modèle d'adapter son analyse selon qui pose la question :
-- un angel investor n'évalue pas comme un VC Series A.
-- -----------------------------------------------------------------------------

CREATE TABLE investment_criteria (
    id                  SERIAL PRIMARY KEY,

    -- Classification
    investor_profile    investor_profile    NOT NULL,
    stage               startup_stage       NOT NULL,
    criterion_name      VARCHAR(255)        NOT NULL,
    criterion_category  VARCHAR(100),
    -- Catégories : 'team', 'market', 'product', 'traction',
    --              'financials', 'vision', 'competitive_moat'

    -- Importance
    weight              criterion_weight    NOT NULL,

    -- Contenu
    description         TEXT                NOT NULL,   -- ce que l'investisseur évalue
    how_to_assess       TEXT,                           -- comment évaluer ce critère
    ideal_answer        TEXT,                           -- ce que l'investisseur veut entendre/voir

    -- Signaux décisifs
    red_flags           TEXT                NOT NULL,   -- ce qui disqualifie immédiatement
    green_flags         TEXT                NOT NULL,   -- ce qui renforce la conviction

    -- Explication simple
    simple_explain      TEXT,               -- version accessible pour un entrepreneur non-technique

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_criteria_profile       ON investment_criteria(investor_profile);
CREATE INDEX idx_criteria_stage         ON investment_criteria(stage);
CREATE INDEX idx_criteria_profile_stage ON investment_criteria(investor_profile, stage);
CREATE INDEX idx_criteria_weight        ON investment_criteria(weight);


-- =============================================================================
-- VUES UTILITAIRES
-- Simplifier les requêtes fréquentes du modèle lors du tool use
-- =============================================================================

-- Vue : risques critiques par secteur et stade (requête la plus fréquente)
CREATE VIEW v_critical_risks AS
SELECT
    rp.id,
    rp.pattern_name,
    rp.sector,
    rp.stage,
    rp.criticality,
    rp.category,
    rp.simple_explain,
    rp.warning_signals,
    rp.mitigation_simple,
    rp.impact_on_runway,
    rp.time_to_impact
FROM risk_patterns rp
WHERE rp.criticality IN ('critical', 'high')
ORDER BY
    CASE rp.criticality
        WHEN 'critical' THEN 1
        WHEN 'high'     THEN 2
    END;

-- Vue : benchmarks enrichis avec interprétation (évite les jointures complexes)
CREATE VIEW v_benchmarks_with_context AS
SELECT
    sb.sector,
    sb.stage,
    sb.metric_name,
    sb.value_median,
    sb.value_good,
    sb.value_excellent,
    sb.value_warning,
    sb.unit,
    sb.context,
    sb.interpretation_good,
    sb.interpretation_bad
FROM sector_benchmarks sb
ORDER BY sb.sector, sb.stage, sb.metric_name;

-- Vue : startups avec nombre de pivots (indicateur de résilience)
CREATE VIEW v_startups_with_pivot_count AS
SELECT
    s.id,
    s.name,
    s.sector,
    s.stage,
    s.region,
    s.outcome,
    s.description,
    COUNT(pc.id) AS pivot_count,
    s.key_learnings
FROM startups s
LEFT JOIN pivot_cases pc ON pc.startup_id = s.id
GROUP BY s.id;


-- =============================================================================
-- TRIGGERS
-- Maintenir updated_at automatiquement
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_startups_updated_at
    BEFORE UPDATE ON startups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_risk_patterns_updated_at
    BEFORE UPDATE ON risk_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- =============================================================================
-- FIN DU SCHÉMA
-- =============================================================================