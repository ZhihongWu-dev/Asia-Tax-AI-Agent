"""Persistence layer: SQLAlchemy metadata, engine/session helpers and ORM models.

The relational schema is a mechanical translation of the shared data contract in
packages/contracts. Allowed enum values for CHECK constraints are imported from
packages.contracts.enums — never hand-copied — so the database cannot drift from
the contract vocabulary.
"""
