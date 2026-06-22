# audio-word-occurrence-playback Specification

## Purpose
TBD - created by archiving change audio-word-candidate-playback. Update Purpose after archive.
## Requirements
### Requirement: Stored occurrences can be previewed on demand
The system SHALL allow an operator to request playback for any stored occurrence candidate. Playback
MUST render a temporary preview from the stored offsets using configurable pre-roll, post-roll, fade
in, and fade out settings. The workflow MUST NOT require permanent clip attachment or mutate the stored
occurrence artifact.

#### Scenario: Preview playback is requested
- **WHEN** an operator requests playback for a stored occurrence candidate
- **THEN** the system renders a temporary preview window from the source audio using the stored offsets
  plus the configured padding and fades

#### Scenario: Preview request does not create a permanent clip
- **WHEN** preview playback completes successfully
- **THEN** the system leaves the persisted occurrence artifact unchanged and does not attach or store a
  permanent snippet as part of v1 playback

### Requirement: Playback preserves source provenance and degrades gracefully
Preview playback SHALL report the source audio asset, occurrence identifier, and effective playback
window it used. If the source audio is missing, unreadable, or cannot be played locally, the workflow
MUST return a clear status rather than silently failing.

#### Scenario: Local playback support is unavailable
- **WHEN** an operator requests playback on a machine without a supported local player
- **THEN** the system returns the rendered preview path and an explicit playback-unavailable status

#### Scenario: Source audio cannot be previewed
- **WHEN** an operator requests playback for an occurrence whose source audio asset is missing or in an
  unsupported format for v1 preview
- **THEN** the system reports the reason and does not mark the occurrence as played

