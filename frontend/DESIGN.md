# JalSaathi public frontend

Design process: the frontend-design skill from anthropics/claude-code,
plugins/frontend-design/skills/frontend-design/SKILL.md (main), read in this chat.

## Plan and review

Audience: rural residents need to understand a recorded water-test result, its advice,
and whether corrective work is complete. Officials need to prioritize cases by block.

Palette: white #ffffff, water-blue #eef6f8, ink #173f55, teal #087a79,
alert red #b43c35, resolved green #287553. Amber is reserved for lab confirmation pending.
Typography: self-hosted Noto Sans Devanagari for Hindi, DM Sans for English; local font fallbacks.
Text is left aligned. Paragraphs stay below 70 characters where space permits.

Considered a large dark marketing hero, then rejected it because it pushes advice
below the fold and gives a generic promotional treatment to a water test.
Use a compact status notice with an original droplet illustration instead.
Status colour is reinforced by text and icons. There is no ambient animation.

```
Desktop                         Mobile
Brand / navigation / language   Brand / language
Village and location            Navigation
Status notice / water symbol    Village / status
Advice           Telegram       Advice / audio
Audio            Poster         Six-stage timeline
Six-step journey Details        Telegram / poster
```

Components: shell, villagePage, caseAdvice, timeline, directoryPage, blockPage,
poster dialog. Pure model helpers own routing, formatting, ordering, and progress.
The API adapter owns timeouts, cancellation, and explicitly selected mock mode.
Only the map and poster load their heavier libraries on demand.

Routes: / directory, /?v=key village, /?b=key block. Append demo=1 for the
fixture preview. Never automatically substitute preview data for a failed live request.
Advice in mock mode is imported from content/advice.json without rewriting it.

Validation: model and rendering tests cover status interpretation, reopened cases,
private timeline actors, unsafe links, route persistence and chemical advice. Verify
desktop/mobile layouts and keyboard/poster interactions in a real browser before release.

## About-first revision (Sat 10 Oct, from Umar's brief)

The site now opens on About; Find my village is the primary action at the top right (`/?find`).
Direction: warm editorial (references: Claude and Notion entries in VoltAgent/awesome-claude-design), adapted to water:
ivory canvas #f7f4ec, ink #173f55 and teal #087a79 kept, earth #9a7655 and gold #c9a66b for cartographic detail.
Display type Fraunces (Latin) and Tiro Devanagari Hindi; body type unchanged.
No stock photography: the hero is a "living map" drawn from the real coordinates of every village with a failed test
(hollow = approximate location), with the demo village marked. Figures come from the live API only (105 days, 87%,
149); if a figure can't load, its block is hidden rather than invented. The brief's heritage framing ("reconnect with
your roots") was not used: JalSaathi is about unsafe drinking water, and the page says so.
Checked at 360, 390 and 1440 px with mobile emulation: no horizontal overflow on any page.
