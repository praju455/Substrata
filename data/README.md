# Demo data

Reserved for visibly labelled synthetic fixtures, a text evidence corpus and
event replay files. **[Design]**

The eventual seed will keep hidden ground-truth relationships separate from the
declared graph available to the application. **[Design]** No dataset exists yet.

Generated local databases are ignored by Git.

M1.1 adds `python scripts/dev.py migrate`, which creates/upgrades
`data/substrata.sqlite3`. M1.2 adds the graph and provenance schema. All five
domain tables remain empty; migration preserves existing records and does not
generate scenario fixtures. ERP tables and seeding follow in later M1 checkpoints.

At M0.4, `python scripts/dev.py seed` explicitly reports that seeding is pending
and creates no database or fixtures.
