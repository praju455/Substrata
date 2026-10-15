-- Local Compose only; production secrets and roles must be provisioned externally.
CREATE ROLE substrata_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD 'local-only-change-me';
GRANT CONNECT ON DATABASE substrata TO substrata_app;
GRANT USAGE ON SCHEMA public TO substrata_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT ALL ON TABLES TO substrata_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT ALL ON SEQUENCES TO substrata_app;
