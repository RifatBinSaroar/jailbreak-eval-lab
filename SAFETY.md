# Safety and Public-Repository Policy

This repository is intentionally open source. Reproducibility must be balanced with safe handling of dual-use material.

## Public by default

Safe to publish when licensing permits:

- research code
- evaluation interfaces
- metric implementations
- schemas
- benchmark manifests and identifiers
- literature metadata
- annotation rubrics
- aggregate results
- non-operational synthetic fixtures
- documentation and website code

## Do not commit casually

Do not commit:

- secrets, API keys, tokens, or credentials
- real personal data
- uncontrolled executable malware or host-impacting payloads
- benchmark artefacts whose licence forbids redistribution
- raw third-party datasets when a manifest or download script is sufficient
- code intended to escape or weaken the experiment sandbox

## Experiment boundary

Any functional validation that executes code must run only inside an explicitly isolated test environment using designated synthetic data. Test fixtures should be constructed so that success can be measured without affecting real user files, networks, services, credentials, or systems.

## Public test fixtures

Automated CI should use benign stand-ins and synthetic fixtures. CI must not execute harmful benchmark payloads.

## Data provenance

For each external dataset or benchmark, record:

- source
- version / commit where possible
- licence
- retrieval date
- transformation steps
- whether redistribution is permitted

## Review trigger

Any pull request that adds execution, sandboxing, external tools, or dual-use benchmark material requires an explicit safety review before merge.
