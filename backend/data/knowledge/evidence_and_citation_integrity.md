# Evidence Retrieval and Citation Integrity — System Design Note

PROVENANCE: Local design note authored for the MedExplain AI research prototype.
This document is **about the system itself**, not about medicine. No PMID or DOI.

## Purpose

This note records the rules the MedExplain AI retrieval layer enforces, so that
the behaviour is auditable and so that reviewers can verify that no citation is
ever produced that is not traceable to a stored local document.

## Rules enforced by the pipeline

1. **No citation without a source.** Every evidence item returned by
   `POST /api/retrieve/evidence` corresponds to a specific chunk of a specific
   document in the local knowledge directory. There is no generative path that
   can invent a reference.

2. **Identifiers are validated, not trusted.** Only identifiers that match the
   issued pattern are accepted as grounding targets. A model that produces
   `[doc:some-thing-not-issued]` has that reference dropped and the response
   marked as insufficiently grounded.

3. **Empty index is a first-class state.** When the knowledge base is not
   initialized, the API returns `Knowledge base not initialized` and an empty
   evidence list. It does **not** fall back to model-recalled references.

4. **Local notes carry no external identifiers.** The documents in
   `backend/data/knowledge/` are local reference notes authored for this
   prototype. They deliberately carry **no PMID and no DOI**, because no
   published identifier was verified. A note that asserted one would be a
   fabricated citation.

5. **Similarity scores are not evidence of clinical truth.** A cosine similarity
   is a measure of embedding proximity, nothing more. It carries no clinical
   meaning and is not a confidence.

6. **Grounding is necessary, not sufficient.** A citation that resolves proves
   only that the text exists in the local store. It does not prove the retrieved
   text answers the question asked.

## What the retrieval layer deliberately does not do

- It does not query PubMed, Crossref, or any network service.
- It does not perform web search to fill an empty index.
- It does not let the language model add references that retrieval did not
  return.
- It does not report recall, precision, or any retrieval quality metric, because
  none has been measured against a labelled query set.

## Verification procedure

To confirm the system honours these rules:

1. Start with an empty index and query. Expect an explicit not-initialized
   response and zero evidence items.
2. Ingest documents, restart, query. Expect evidence items whose `source` and
   `document_id` match ingested files.
3. Ask the model directly for a citation with no supporting retrieval. Expect
   the reference to be dropped and the grounding flag to report it.
