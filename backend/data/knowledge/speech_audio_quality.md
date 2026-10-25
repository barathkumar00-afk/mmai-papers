# Voice and Speech Recording — Clinical Data Quality Note

PROVENANCE: Local reference note authored for the MedExplain AI research prototype.
Not a published article, no PMID or DOI. Included so the retrieval pipeline has
real local material to search. Relevant because the pipeline's acoustic
features are only interpretable under stated conditions.

## Recording conditions matter

Speech-based clinical capture is only as reliable as its recording conditions.
Key variables:

- **Ambient noise floor** — background noise degrades word error rate sharply.
  A noise floor within roughly 10 dB of the speech level causes severe
  degradation; within 20 dB causes measurable but usable degradation.
- **Signal-to-noise ratio** is a better predictor of transcript reliability than
  absolute volume.
- **Microphone distance** — a consistent 15-20 cm working distance keeps level
  stable. Unconstrained distance is a common source of level variation.
- **Room reverberation** blurs formants, particularly the second formant, and
  degrades phoneme discrimination.

## Consequences for acoustic features

The pipeline's acoustic features are computed on the decoded waveform. They
are only interpretable when the recording conditions are adequate:

- **Zero-crossing rate** is inversely related to dominant frequency. It is
  strongly speaker- and channel-dependent, and microphone high-pass filtering
  removes the lowest-frequency crossings.
- **Spectral centroid** is the balance point of the power spectrum. It rises with
  brightness and with harshness, and is also strongly channel-dependent.
- **Spectral flatness** approaches 1 for noise and falls with tonal content.
  It is frequently the best single indicator of an un-usable recording.
- **Spectral rolloff (85%)** marks the frequency below which 85% of energy lies.
  It rises with bandwidth.

Because these features are channel-dependent, they support **recording-quality
gating** and **prosody (contour, tempo, pause) assessment**. They do **not**
support diagnostic claims about voice pathology. Voice quality indices such as
jitter and shimmer computed on a consumer microphone are not clinically valid.

## Telemetry is more reliable than features

For deciding whether a recording is usable, the proportion of non-speech
("silence") frames, the SNR estimate, and the spectral flatness summary are more
robust than any single feature vector.

## Clinical safety

An automatically produced transcript is a **draft for confirmation**, not a
record of what the patient said. Any clinical decision that depends on the
transcript must be checked against the clinician's own documentation.
