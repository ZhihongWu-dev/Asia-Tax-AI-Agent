-- Private, review-gated overlay for sources present in main but absent or
-- different in the separately uploaded Li law library. No public API grants.
CREATE SCHEMA IF NOT EXISTS database_integration;
REVOKE ALL ON SCHEMA database_integration FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS database_integration.source_review (
    cite_id text PRIMARY KEY,
    doc_id text NOT NULL,
    difference text NOT NULL CHECK (difference IN ('main_only', 'different_text')),
    review_status text NOT NULL DEFAULT 'candidate'
        CHECK (review_status IN ('candidate', 'accepted', 'rejected')),
    source_commit text NOT NULL,
    base_uploaded_at text NOT NULL,
    document_title text,
    document_url text,
    document_sha256 text,
    document_in_base boolean NOT NULL,
    review_note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    reviewed_at timestamptz,
    CHECK (review_status <> 'accepted' OR reviewed_at IS NOT NULL)
);
REVOKE ALL ON database_integration.source_review FROM PUBLIC, anon, authenticated;

CREATE INDEX IF NOT EXISTS source_review_status_idx
    ON database_integration.source_review (review_status, difference);
