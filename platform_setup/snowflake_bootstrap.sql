-- Run as a role allowed to create a test database/warehouse, or adapt names to existing objects.
CREATE WAREHOUSE IF NOT EXISTS SAC_TEST_WH
  WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE;
CREATE DATABASE IF NOT EXISTS SAC_TEST_DB;
CREATE SCHEMA IF NOT EXISTS SAC_TEST_DB.SAC_CONFORMANCE;
-- If using a custom role, grant the required privileges to that role here.
