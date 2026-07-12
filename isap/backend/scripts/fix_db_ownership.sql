-- Выполнить от суперпользователя postgres
-- Цель: передать владение таблицами isap_user для выполнения миграций

-- 1. Сбросить все владения на isap_user
DO $$DECLARE r RECORD;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner != 'isap_user'
  LOOP
    EXECUTE format('ALTER TABLE %I OWNER TO isap_user;', r.tablename);
  END LOOP;
END$$;

-- 2. Проверить результат
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
