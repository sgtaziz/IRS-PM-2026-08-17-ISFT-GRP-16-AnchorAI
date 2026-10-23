# AnchorAI presentation engine

Dependency-free HTML decks for the two project videos. Presented full screen in a browser, recorded with OBS at 1920x1080 with the webcam overlaid bottom right. Works from `file://`.

```
Video/presentation/
  engine/deck.css      design system + components
  engine/deck.js       stage, steps, transitions, presenter sync, component builders
  presenter.html       presenter window (opened with P)
  demo.html            every component and transition, 15 slides
  assets/              logo.svg, logo-light.svg, logo-mark.svg
```

Open `demo.html` (or any deck) in Chromium or Brave. Inter loads from Google Fonts; offline it falls back to the local Inter, then system-ui. App screenshots are referenced in place: `../../ProjectReport/latex/figures/screens/<name>.png`.

## Keys

| Key | Action |
| --- | --- |
| Right, Space, PageDown, Down, click | next beat (step, then next slide) |
| Left, PageUp, Up | back |
| Home / End | first / last slide |
| digits then Enter | jump to slide number (Esc cancels) |
| F | full screen |
| P | open presenter window |
| T | rehearsal overlay (elapsed vs target per section). Shift+R resets timers |
| C | camera safe zone outline (hidden by default) |

The URL hash is `#<slide>/<step>` (slide 1-based, step 0-based). A reload keeps your place. Timers survive reloads through `sessionStorage`.

## Camera safe zone

The webcam sits bottom right. Keep the rectangle x 1440 to 1920, y 780 to 1080 empty. In practice: anything below y 780 must end before x 1440. The footer chip and progress bar already respect this. Press C to see the zone while laying out. Slides have padding `104px 120px 128px`.

## Authoring a deck

```html
<link rel="stylesheet" href="engine/deck.css">
<div class="deck" data-id="video1" data-title="Video 1" data-speaker="Name" data-speaker-role="Stream A"
     data-total-target="5:00" data-transition="fade">
  <section class="slide dark" data-section="Intro" data-section-target="1:00" data-transition="zoom"> ... </section>
</div>
<script src="engine/deck.js"></script>
```

Deck attributes: `data-id` (links presenter window, use a unique one per deck), `data-title`, `data-speaker`, `data-speaker-role`, `data-total-target` (m:ss or seconds), `data-transition` (default), `data-presenter` (path to presenter.html if the deck is elsewhere).

Slide classes: theme `dark` (default), `light`, `brand`, `deep`; layout `center`, `middle`, `hero`, `section-open`. Slide attributes: `data-transition`, `data-section="Name"` (starts a section) with `data-section-target`, `data-speaker` (per-slide override), `data-chrome="off"` (hide footer chip and bar, use on hero and closing), `data-title`.

Utilities: `.row .col .grow .gap-8..96 .mt-8..96 .grid .grid-2/3/4 .abs`, type `.display .h1 .h2 .h3 .lead .body .small .eyebrow .grad .mint .dim`, `.pill (.mint .brand .warn)`, `.card`, `.rise` (fade up on slide enter, `style="--d:n"` delays by n x 90ms), `[data-tone="brand|mint|violet|warn|danger|muted"]`.

### Steps and notes

Any element with `data-step="n"` is hidden until step n (one click each). Options: `data-anim="left|right|zoom|fade|blur"`, `style="--sd:.2s"` delay, `data-step-out="n"` to hide again at step n. Class `raw` opts out of the default reveal style.

```html
<section class="slide dark">
  <h2 class="h2">Title</h2>
  <p class="lead" data-step="1">Appears on click 1</p>
  <p class="lead" data-step="2">Appears on click 2</p>
  <aside class="notes" data-beat="P1.1">Narration shown on entering the slide (step 0).</aside>
  <aside class="notes" data-beat="P1.2">Narration for step 1.</aside>
  <aside class="notes" data-beat="P1.3">Narration for step 2.</aside>
</section>
```

The k-th `aside.notes` is the narration for step k. Override with `data-step="n"`. An aside may also contain children `<p data-beat="..">`, one per step. A slide has as many steps as the highest of its `data-step` values and its note steps, so a note with no visual still costs a click, which is what keeps narration in sync. A step with no note keeps showing the previous one in the presenter window.

### Presenter window and timers

P opens `presenter.html`. It shows the current beat (large), the next beat, beat id, slide and step, speaker, a section timer and a total timer against `data-section-target` and `data-total-target`, the slide outline (click to jump), Back/Next buttons (Space and arrows work too) and Start/Pause/Reset. `+` and `-` resize the text. It is synced to the deck through `BroadcastChannel`, with `postMessage` to the popup/opener as a fallback, and works on `file://` (verified in Brave). Timers start on the first forward click. The T overlay on the main window shows the same timers and is never visible unless toggled.

### Transitions

Chosen per slide with `data-transition` on the destination slide (falls back to the deck default, then `fade`). Going backwards reverses the direction.

| Value | Look |
| --- | --- |
| `fade` | fade-through with slight scale |
| `slide` | push with parallax: old slide drifts and dims, new slide, background and content stagger in |
| `up` | same, vertical |
| `zoom` | zoom-blur out, in from small and blurred |
| `wipe` | diagonal mask wipe |
| `morph` | elements with the same `data-morph="id"` glide and resize from their old place to the new one while the backgrounds cross-fade |
| `cut` | instant |

The leaving slide keeps `.is-active` (plus `.is-leaving`) until its transition ends, so CSS written as `.is-active .x { animation ... }` keeps running and the old slide holds its last frame. The engine renders each incoming slide once in its unrevealed state before adding `.is-in` / `.is-shown`, and the parallax stagger only touches direct children that have no animation of their own, are not step-gated and are visible. Deck CSS can therefore use `opacity: 0` base states plus `animation: ... both` safely.

`prefers-reduced-motion` turns everything into a short cross-fade, stops background drift, packets and Ken Burns, and makes counts jump to their final value.

### Components

Title with animated logo:
```html
<section class="slide dark hero" data-chrome="off">
  <div class="logo-reveal" data-size="88"></div>           <!-- data-mark="only" for the icon alone -->
  <h1 class="display grad rise" style="--d:5">Title</h1>
  <p class="lead" data-step="1">Subtitle</p>
</section>
```

Section opener with lower third (appears after 0.7 s, leaves after `data-hold` ms; or give it `data-step` to time it):
```html
<section class="slide brand section-open" data-section="Part one" data-section-target="1:30">
  <div class="num-ghost">01</div>
  <p class="eyebrow">Part one</p><h2 class="h1">Heading</h2><p class="lead">Line</p>
  <div class="lower-third" data-name="Name" data-role="Role" data-hold="5000" data-delay="700"></div>
</section>
```

Kinetic number and caption (`data-count` works on any element; attributes `data-prefix data-suffix data-decimals data-from data-duration data-delay`):
```html
<div class="bignum"><div class="num" data-count="38" data-suffix="%"></div><div class="cap" data-step="1">Caption</div></div>
```

Stat grid:
```html
<div class="stat-grid">
  <div class="stat" data-tone="mint" data-step="1"><div class="num" data-count="5"></div><div class="lbl">label</div><div class="delta">up 6 pts</div></div>
</div>
```
`.delta.down` for negative.

Comparison bars (value, optional max default 100, `win` highlights):
```html
<div class="bars">
  <div class="bar" data-step="1" data-label="Greedy" data-sub="Best first" data-value="52" data-suffix="%" data-tone="brand"></div>
  <div class="bar win" data-step="2" data-label="GA" data-value="74" data-suffix="%" data-tone="mint"></div>
</div>
```

Line / area chart (SVG, drawn by stroke animation; series are JSON; `data-w data-h` set the size, `data-ymin data-ymax data-unit` optional):
```html
<div class="chart" data-w="1240" data-h="500" data-labels="W1,W2,W3" data-unit="%"
     data-series='[{"name":"Base","tone":"muted","data":[50,52,53]},{"name":"AnchorAI","tone":"mint","data":[50,58,66]}]'></div>
```

Flow diagram. Give `.flow` a size and position nodes absolutely; edges are `<i class="edge-cfg">`, drawn when their step arrives. Edge options: `data-label`, `data-packets` (moving dots), `data-packet-dur`, `data-dash`, `data-tone`, `data-from-side` / `data-to-side` (`l r t b`, otherwise chosen automatically):
```html
<div class="flow" style="width:1680px;height:480px">
  <div class="node" data-id="a" data-tone="brand" data-step="1" style="left:0;top:180px;width:260px;height:120px"><div class="node-title">Data</div><div class="node-sub">sub</div></div>
  <div class="node hl" data-id="b" data-tone="mint" data-step="2" style="left:400px;top:180px;width:300px;height:120px">...</div>
  <i class="edge-cfg" data-from="a" data-to="b" data-step="2" data-packets="2" data-label="plan"></i>
</div>
```

Browser or device frame with Ken Burns focus. `data-focus="x,y,w,h"` are image fractions (0 to 1). Each `.focus` becomes the active zoom from its step on; `data-label` adds a ring and callout (`data-ring` for a ring without text). Add `drift` for a slow idle zoom, `float` for a gentle bob, `data-ar` to force the aspect ratio, `data-max-zoom`:
```html
<div class="frame browser float" style="width:1160px" data-src="../../ProjectReport/latex/figures/screens/dashboard.png" data-url="anchorai.app/dashboard">
  <i class="focus" data-step="1" data-focus="0.205,0.2,0.775,0.25" data-label="Risk at a glance"></i>
  <i class="focus" data-step="2" data-focus="0,0,1,1"></i>
</div>
```
Use `class="frame device"` for the tablet bezel. Screenshots are 1800 px tall, so zooms past about 2.5x get soft.

Quote (words animate in; `<em>` is highlighted):
```html
<div class="quote"><div class="qmark">&ldquo;</div><p class="qtext" data-split>Words <em>reveal</em> one by one.</p>
  <div class="cite" data-step="1"><b>MM</b><div><div class="who">Name</div><div class="what">Role</div></div></div></div>
```
`data-split` works on any element.

Checklist (ticks draw in; `.fail` gives a red cross):
```html
<ul class="checklist"><li class="check-item" data-step="1">Item</li><li class="check-item fail" data-step="2">Bad item</li></ul>
```

Timeline (line fills as items arrive):
```html
<div class="timeline"><div class="tl-item" data-step="1"><div class="dot">1</div><div class="when">August</div><div class="what">Scope</div><div class="desc">Detail</div></div></div>
```

Pricing cards (`featured` is highlighted, `li.off` is a cross):
```html
<div class="pricing"><div class="plan featured" data-step="1"><div class="badge">Recommended</div><div class="pname">GA</div>
  <div class="price"><sup>$</sup>1,500</div><div class="per">weekly</div><ul><li>Feature</li><li class="off">Missing</li></ul></div></div>
```

Two column compare:
```html
<div class="compare"><div class="cc before" data-step="1"><div class="ch">Before</div><div class="ct">Title</div><ul><li>Bad</li></ul></div>
  <div class="vs" data-step="2">VS</div>
  <div class="cc after" data-step="2"><div class="ch">After</div><div class="ct">Title</div><ul><li>Good</li></ul></div></div>
```

## Known limitations

- `morph` animates position and size only; colours and fonts jump. Use it for shapes, logos and cards. The morph element must be visible at step 0 of both slides.
- Step-gated content inside a morph element is not supported. Flow diagram nodes must be direct children of `.flow`.
- Chart text is sized in SVG units, so keep `style="width"` close to `data-w`.
- Screenshots are zoomed with CSS, so extreme zooms are soft.
- Fullscreen (F) and popup windows need a user gesture. The popup may be blocked until you allow popups for the page (a toast says so).
- Count-up and lower-third timing use real time. In headless screenshots add `--virtual-time-budget`.
