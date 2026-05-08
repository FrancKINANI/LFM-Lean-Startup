-- =============================================================================
-- SEEDS RUNNER — LFM Lean Startup
-- Exécute tous les seeds dans le bon ordre (pas de dépendances entre tables
-- de seeds, mais lean_concepts en premier pour cohérence logique)
-- =============================================================================
-- Usage : psql -U <user> -d <database> -f database/seeds/seeds_runner.sql
-- =============================================================================

\echo '============================================================'
\echo 'LFM Lean Startup — Initialisation de la base de données'
\echo '============================================================'

BEGIN;

\echo ''
\echo '[1/4] Insertion des concepts Lean Startup...'
\i lean_concepts.sql
\echo '     OK'

\echo ''
\echo '[2/4] Insertion des patterns de risque...'
\i risk_patterns.sql
\echo '     OK'

\echo ''
\echo '[3/4] Insertion des benchmarks sectoriels...'
\i sector_benchmarks.sql
\echo '     OK'

\echo ''
\echo '[4/4] Insertion des critères d investissement...'
\i investment_criteria.sql
\echo '     OK'

COMMIT;

\echo ''
\echo '============================================================'
\echo 'Base de données initialisée avec succès.'
\echo '============================================================'

-- Vérification rapide des volumes insérés
\echo ''
\echo 'Vérification des volumes :'
SELECT 'lean_concepts'       AS table_name, COUNT(*) AS rows FROM lean_concepts
UNION ALL
SELECT 'risk_patterns',                      COUNT(*) FROM risk_patterns
UNION ALL
SELECT 'sector_benchmarks',                  COUNT(*) FROM sector_benchmarks
UNION ALL
SELECT 'investment_criteria',                COUNT(*) FROM investment_criteria;
