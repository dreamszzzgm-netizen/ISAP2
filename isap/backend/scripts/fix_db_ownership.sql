-- Безопасное исправление владения для Alembic
-- Выполнить от суперпользователя postgres в psql или pgAdmin.
-- 
-- Принцип:
--   * создаётся роль для миграций с владением объектами схемы;
--   * runtime-роль isap_user получает только DML-права;
--   * isap_user НЕ становится владельцем таблиц.
--
-- Если создание отдельной роли невозможно в текущем окружении —
-- альтернатива: точечная смена владельца только таблиц ISAP.
--
-- Вариант A (рекомендуемый): создать роль для миграций
-- =========================================================
-- CREATE ROLE isap_migration WITH LOGIN PASSWORD '...';
-- GRANT ALL ON DATABASE isap TO isap_migration;
-- GRANT ALL ON SCHEMA public TO isap_migration;
-- ALTER TABLE ... OWNER TO isap_migration;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO isap_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO isap_user;

-- Вариант B (минимальный для текущего окружения):
-- точечная смена владельца только таблиц ISAP
-- =========================================================
ALTER TABLE emergency_rescue_units     OWNER TO isap_user;
ALTER TABLE emergency_services         OWNER TO isap_user;
ALTER TABLE pasf_documents             OWNER TO isap_user;
ALTER TABLE hazardous_facilities       OWNER TO isap_user;
ALTER TABLE equipment                  OWNER TO isap_user;
ALTER TABLE hazardous_substances       OWNER TO isap_user;
ALTER TABLE organizations              OWNER TO isap_user;
ALTER TABLE responsible_persons        OWNER TO isap_user;
ALTER TABLE documents                  OWNER TO isap_user;
ALTER TABLE document_versions          OWNER TO isap_user;
ALTER TABLE pmla_questionnaires        OWNER TO isap_user;
ALTER TABLE pmla_samples               OWNER TO isap_user;
ALTER TABLE scenario_matrix            OWNER TO isap_user;
ALTER TABLE opo_details                OWNER TO isap_user;
ALTER TABLE calculation_results        OWNER TO isap_user;
ALTER TABLE import_jobs                OWNER TO isap_user;
ALTER TABLE import_rows                OWNER TO isap_user;
ALTER TABLE regulatory_documents       OWNER TO isap_user;
ALTER TABLE alembic_version            OWNER TO isap_user;

-- Проверка
SELECT tablename, tableowner FROM pg_tables
WHERE schemaname = 'public' AND tableowner != 'isap_user'
ORDER BY tablename;
