# UI Style Directive — DeepSeek × TypeSafe

Version 1.0 · September 17, 2026

## 1. Purpose and authority

Create an original AI workspace that combines DeepSeek’s calm, spacious interaction design with TypeSafe’s retro computer personality. It should feel contemporary, capable, approachable, and comfortable for long sessions.

This document is the implementation brief for designers and coding agents. The rules below define a proposed original design system, not the official design system of either reference company. Exact colors, dimensions, and component specifications are design decisions for this product.

Apply the direction to chat, activity, files, settings, login, and public product pages. Build only features required by the product; a style directive does not authorize adding unrelated functionality.

“studio” was a placeholder in the concept. Replace it with the actual product name. Create an original identity; do not reuse either company’s logo, mascot, wordmark, or proprietary artwork.

## 2. Core direction

**A modern AI workspace made by people who love old computers.**

Give the work a clear, quiet surface. Concentrate personality in the surrounding controls, window frames, typography, and occasional pink texture.

Priority order:

1. Readability and obvious actions.
2. Consistent spacing and hierarchy.
3. Distinctive pink identity.
4. Restrained retro details.
5. Optional decorative texture and motion.

If decoration competes with content, reduce decoration. When adding a new screen, preserve the same visual grammar instead of inventing a new style.

## 3. Reference findings and research limits

The research inspected public websites, TypeSafe documentation, and both companies’ platform sign-in screens. Authenticated chat and dashboard interiors were not accessible. Treat the proposed chat and platform layouts below as original synthesis, not a verified reconstruction of private screens.

| Reference | Observed traits | Design lesson |
| --- | --- | --- |
| DeepSeek public homepage | Pale blue atmosphere, a subtle grid, generous space, a central composer, rounded DeepThink and Search controls | Make the first action clear; give input and reading room to breathe |
| DeepSeek platform sign-in | White form area, pill-shaped fields, restrained typography, a dark photographic side panel | Separate expressive atmosphere from functional controls |
| TypeSafe public homepage | Pink dithered textures, vintage gray windows, oversized black headlines, terminal lettering, version labels and technical annotations | Build personality through a deliberate contrast of modern type and vintage software details |
| TypeSafe console sign-in | Mostly monochrome, square controls, geometric mark, pixel imagery | Product surfaces can be much quieter than marketing surfaces |
| TypeSafe documentation | Structured navigation, dark surfaces in the inspected appearance, selective pink emphasis | Use pink to mark navigation and actions rather than filling every panel |

TypeSafe’s inspected homepage used Die Grotesk, LisaTerminal, and JetBrains Mono. These are reference observations, not required dependencies. The proposed font pairing below is intentionally different.

Sources consulted September 17, 2026:

- [DeepSeek homepage](https://www.deepseek.com/en/)
- [DeepSeek chat sign-in](https://chat.deepseek.com/sign_in)
- [DeepSeek platform sign-in](https://platform.deepseek.com/sign_in)
- [TypeSafe homepage](https://typesafe.ai/)
- [TypeSafe console sign-in](https://console.typesafe.ai/login)
- [TypeSafe documentation](https://docs.typesafe.ai/introduction)

## 4. Color system

Use semantic tokens. Do not scatter unrelated color values through component code.

| Token | Light | Dark | Role |
| --- | --- | --- | --- |
| Canvas | `#FCFAF9` | `#191719` | Main reading surface |
| Sidebar | `#F2EEED` | `#211E22` | Navigation and secondary areas |
| Panel | `#FFFFFF` | `#242025` | Composer, dialogs, menus |
| Text | `#222125` | `#F3ECEF` | Primary content |
| Muted text | `#706A70` | `#B5AAB3` | Secondary labels and metadata |
| Border | `#DED7DB` | `#423941` | Quiet separators and structural edges |
| Pink | `#ED9DC4` | `#E4A0C4` | Brand accent and primary action fill |
| On pink | `#281B23` | `#281B23` | Text/icons on pink buttons |
| Pink wash | `#F5DCE8` | `#392634` | Selected navigation background |
| Blue | `#435CC4` | `#A9B7FF` | Links, focus indicators, selected tool modes |
| Blue wash | `#EEF0FF` | `#30334D` | Active tool-mode background |
| Retro panel | `#E8E4E4` | `#302B31` | Compact tool-window title bars |
| Success text | `#286448` | `#98D8B3` | Confirmed successful outcomes |
| Warning text | `#825316` | `#ECC58B` | Attention or review required |
| Error text | `#A52F46` | `#FFA8B8` | Failed actions and validation |

Color rules:

- Neutral surfaces dominate working screens. Pink is the recognizable brand accent.
- Pink buttons use dark text; do not assume white text is readable on pastel pink.
- Blue has a functional role. Do not alternate pink and blue arbitrarily between equivalent controls.
- Use labeled semantic states for success, warnings, and errors. Never communicate state with color alone.
- Decorative pink gradients may appear on welcome or marketing surfaces. Reading surfaces remain solid.
- Validate the actual foreground/background combinations in implementation. Aim for at least 4.5:1 for normal text, 3:1 for large text, and 3:1 for essential control indicators. Quiet divider tokens alone must not be the only way to identify an essential control.

## 5. Typography

Use **DM Sans** for the main interface and **IBM Plex Mono** for supporting technical labels. Bundle approved font assets when offline operation is required; use system fallbacks if loading fails.

| Role | Desktop size | Weight | Line height | Treatment |
| --- | --- | --- | --- | --- |
| Welcome heading | 34–40px | 500 | 1.15–1.2 | Slightly tight tracking |
| Page heading | 28–32px | 500 | 1.2 | Sentence case |
| Section heading | 18–20px | 500–600 | 1.35 | Clear, compact |
| Conversation text | 16px | 400 | 1.65–1.75 | Highest reading comfort |
| Main interface text | 14px | 400–500 | 1.45–1.6 | Neutral and legible |
| Supporting metadata | 12px | 400 | 1.5 | Muted, still readable |
| Technical micro-label | 11–12px | 400–500 | 1.4 | Monospace, occasional uppercase |
| Code | 13–14px | 400 | 1.6 | Monospace |

At small widths, reduce the welcome heading to 28–30px and keep editable input text at least 16px.

Use monospace for filenames, tool identifiers, timestamps, and short activity labels. Use normal sans-serif for explanations and long responses. Pixel lettering is optional for short brand moments only; it must never become the body font.

Marketing headlines may be larger, but the application should keep its modest scale. Avoid all-uppercase paragraphs, tiny essential labels, and exaggerated tracking.

## 6. Layout and spacing

Use a spacing scale of **4, 8, 12, 16, 24, 32, 48, 64px**.

### Desktop application

- Top bar: approximately 48–56px high.
- Sidebar: approximately 208–240px wide; compact layouts may use 194px.
- Main reading column: maximum 680–760px, centered in available space.
- Composer: aligned to the reading column.
- Main horizontal padding: 24–32px.
- Conversation turns: 24–32px apart.
- Related control groups: 8–12px apart.
- Use one main content region. Open supporting information on demand.

### Mobile and narrow windows

- Below approximately 720px, collapse the sidebar into a drawer or compact navigation.
- Use 16px horizontal content padding.
- Keep send, stop, and composer controls reachable without horizontal scrolling.
- Tables may scroll within their own container; the overall page must not overflow.
- Use roughly 44px touch targets even when the visible icon is smaller.
- Preserve reading order and all essential actions when navigation collapses.

Do not add permanent dashboards, empty metric cards, or decorative side panels simply to fill space.

## 7. Shape and surface language

The contrast between comfortable conversation surfaces and precise tool surfaces is central to the design.

| Element | Radius | Surface treatment |
| --- | --- | --- |
| Composer | 12–16px | Solid panel, thin border, very soft shadow |
| User message | 10–14px | Quiet neutral fill |
| Assistant response | None by default | Text directly on the canvas |
| Tool/activity window | 2–4px | Thin frame, compact title bar |
| Standard button | 4–6px | Restrained fill or border |
| Primary send button | 6–8px | Pink fill and dark icon |
| Selected navigation row | 3–5px | Pink wash |
| Dialog | 8–12px | Opaque surface and clear hierarchy |

Use a subtle 1–2px offset shadow on selected retro elements, such as a tool window or new-conversation control. Keep it occasional. Use quiet borders for most structural separation.

Avoid thick black frames around every element, excessive inset bevels, universal pill shapes, glass effects over reading text, and stacked layers of decorative cards.

## 8. Chat components and states

### Welcome screen

Show the product identity, one short welcome line, the composer, and only the most useful starter actions. The greeting should help someone begin rather than deliver a marketing pitch.

Optional pink dithering may occupy the upper background and fade out before dense content begins.

Example greeting: “What would you like to work on?”

### Sidebar

Place new conversation near the top. Show actual product navigation and conversation history. Use a pink wash for the current location. Keep selected and hovered states distinct.

Do not invent extra destinations just to make the app appear more capable.

### Composer

- Solid background, thin outline, comfortable padding.
- Message input is the primary focus.
- Place optional modes along the lower left and the send/stop action at the lower right.
- Selected modes receive blue text, border, and a subtle blue wash.
- Show attachment controls only when attachments are supported.
- Disabled, focused, sending, and error states must be visibly different.
- In a functioning application, show only actions backed by actual capabilities.

### Conversation

- User messages may use a restrained neutral bubble.
- Assistant responses sit directly on the main canvas.
- Keep body text sans-serif, high contrast, and generously spaced.
- Put copy, retry, and related actions in a quiet row after the response.
- Preserve code formatting, link affordances, selection, and keyboard navigation.
- Pin the composer near the bottom during active conversation without obscuring content or the mobile keyboard.

### Tool activity

Use a compact framed module with a small monospace title bar. The visible summary should answer what ran and whether it completed.

Good labels: “Reading files”, “Running checks”, “Plan ready”, “Needs your review”.

Expand to reveal meaningful details, logs, and outputs. Distinguish queued, running, completed, failed, and awaiting-review states with text plus a visual indicator. Keep failure and required-review information visible even when details are collapsed.

A confidence value may appear only when the system provides a defined, meaningful value. Never invent confidence, savings, latency, or success statistics for visual effect.

## 9. Platform screens

### Activity

Use compact rows for real runs or tasks. Show the title, status, relevant timestamp, and an obvious path to details. Add metrics only when they support a decision and come from actual data.

### Files

Use straightforward rows with file names, types, and relevant actions. Keep selection visible. Use the retro window treatment on previews or generated outputs sparingly.

### Settings

Group controls by purpose. Use sentence-case labels and short supporting explanations. Show save feedback near the changed control or section. Never use a large promotional panel in the main settings workflow.

### Login

A split composition can pair a quiet form with a pink dithered illustration or monochrome pixel field. On mobile, prioritize the form. Keep the same typography and component geometry used elsewhere.

### Public homepage

Allow larger typography, stronger pink texture, and playful window compositions. Maintain clear calls to action and an honest product demonstration. Do not carry the full marketing density into the working application.

## 10. Texture, icons, and identity

- Use original, subtle dithering or pixel fields as atmosphere.
- Keep texture outside long reading passages and input text.
- Favor thin, consistent outline icons around 16–20px in controls.
- Give icon-only actions accessible names and visible focus.
- Choose one icon family; avoid mixing chunky pixels, emoji, and unrelated outline styles in navigation.
- A small original symbol can provide recognition without a large mascot.
- Technical labels must carry useful meaning. Avoid fake version numbers, random base64 strings, or ornamental telemetry in everyday workflows.

## 11. Motion and interaction

- Hover and pressed feedback: approximately 100–150ms.
- Expand/collapse and panel transitions: approximately 150–220ms.
- Keep motion short, subtle, and connected to state changes.
- Respect reduced-motion preferences.
- Let decorative welcome animation settle; do not loop motion behind reading text.
- Retain drafts when changing modes or viewing supporting information.
- Show actual progress when available. If progress is unknown, use an honest indeterminate state.
- Keep the conversation position stable while streaming. Do not force-scroll someone who has scrolled up to read.

## 12. Voice and microcopy

Write plainly, directly, and with quiet confidence. Prefer action labels that explain the next step.

| Use | Avoid |
| --- | --- |
| New conversation | Initiate intelligence session |
| View activity | Inspect cognitive telemetry |
| Running checks | Intelligence engine engaged |
| Needs your review | Human intervention protocol |
| Try again | Reinitialize inference sequence |
| Save changes | Commit configuration mutation |

Keep developer terminology in developer-facing details where it helps. Avoid promotional claims inside task workflows. Errors should explain what happened and what the user can do next.

## 13. Implementation guidance

Keep the visual system independent of the UI framework. For a Python application, the chosen frontend must be able to reproduce the tokens, typography, spacing, and states above.

- Define reusable tokens for color, type, spacing, radius, shadow, and motion.
- Build shared navigation, button, composer, tool-window, status, and dialog components.
- Resolve system appearance through complete light and dark token sets.
- Use semantic controls and visible keyboard focus.
- Keep prototype-only content clearly separate from production data.
- In a preview without a backend, disclose that messages do not run a model.
- Avoid allowing a framework’s default theme to override this direction accidentally.

If delivery constraints require simplification, preserve typography, spacing, neutral surfaces, and pink identity first. Decorative texture and beveling can be reduced without losing the core design.

## 14. Acceptance checklist

- [ ] The main action is obvious on every screen.
- [ ] Conversation text remains readable and comfortable over a long session.
- [ ] Neutral surfaces dominate; pink provides a consistent identity.
- [ ] Blue consistently identifies links, focus, and selected tool modes.
- [ ] Retro details are concentrated in useful controls and activity surfaces.
- [ ] The composer is comfortable and the tool panels are precise.
- [ ] Every visible control has an implemented state and meaningful behavior.
- [ ] Loading, empty, error, disabled, and review-required states are designed.
- [ ] No invented metrics, fake system activity, or meaningless technical decoration appears.
- [ ] Keyboard navigation, touch targets, contrast, zoom, and reduced motion are checked.
- [ ] Light and dark appearances preserve the same identity and readable contrast.
- [ ] Narrow layouts work without clipping or page-level horizontal overflow.
- [ ] Branding and artwork are original.
- [ ] Chat, activity, files, settings, and login feel like one product.

## 15. Agent handoff instruction

Implement an original AI workspace using this directive. Preserve DeepSeek-inspired spaciousness and clarity while expressing TypeSafe-inspired vintage computing through restrained pink accents, monospace metadata, sharp tool windows, and subtle dithering. Use the proposed semantic tokens and font pairing. Keep conversations clean, controls understandable, and activity inspectable. Reuse components across screens. Implement the actual product’s features only, and validate real states, responsive behavior, and accessibility before delivery.
