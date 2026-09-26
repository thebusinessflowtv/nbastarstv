# NBA Stars — Automated YouTube Factory

English-first automated production system for **NBA Stars**.

This repository inherits the proven production architecture from **The Business Flow**, while keeping NBA Stars channel data, media, credentials and editorial rules isolated.

## Pipeline

```text
Topic / editorial queue
  -> research + fact checking
  -> English (US) basketball story script
  -> narration
  -> media selection
  -> MediaForge render
  -> render validation
  -> thumbnail
  -> upload_ready
  -> YouTube PRIVATE upload
  -> youtube_video_id checkpoint
  -> manual/publication gate
```

## Channel profile

- Channel: NBA Stars
- Locale: en-US
- Primary market: United States
- Niche: NBA stories, players, teams, curiosities and documentaries
- Default YouTube privacy: private
- Editorial style: high-CTR, high-retention factual basketball storytelling

## Migration policy

Production code and tooling are mirrored from The Business Flow. Historical business media, research packs, queue state, checkpoints and one-off recovery requests are intentionally excluded. The original Actions workflows are preserved under `.github/workflows-template/` and remain disabled until NBA Stars secrets and channel-specific checks are configured.

## Safety rules

- Never commit YouTube OAuth credentials, API keys or voice-reference audio.
- YouTube uploads remain PRIVATE until the publication gate explicitly approves them.
- Use only media with a known and acceptable usage basis.
- Do not fabricate NBA trades, injuries, quotes, statistics or rumors.
- Keep NBA Stars code, media and credentials isolated in this repository.
