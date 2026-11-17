-- Run as the database owner. Set a strong login password separately through
-- secret provisioning; no password or writer-role membership belongs here.
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'taxrora_library_reader') THEN
        CREATE ROLE taxrora_library_reader NOLOGIN NOSUPERUSER NOCREATEDB
            NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'taxrora_library_reader'
        AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
        OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member =
            (SELECT oid FROM pg_roles WHERE rolname = 'taxrora_library_reader')) THEN
        RAISE EXCEPTION 'Existing library reader has excessive privileges or memberships';
    END IF;
END $$;
GRANT CONNECT ON DATABASE postgres TO taxrora_library_reader;
GRANT USAGE ON SCHEMA database, database_integration TO taxrora_library_reader;
GRANT SELECT ON database.meta, database.doc, database.clause,
    database.param, database.jurisdiction, database.treaty, database.decision,
    database_integration.source_review TO taxrora_library_reader;
ALTER ROLE taxrora_library_reader SET default_transaction_read_only = on;
ALTER ROLE taxrora_library_reader SET statement_timeout = '5s';
COMMIT;
