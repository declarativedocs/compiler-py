# declarativedocs

Python reference compiler for the [Declarative Document Format (DDF)](https://ddf.dev). Turns YAML into real documents.

Created by [WeAreBrain](https://wearebrain.com).

## Install

```bash
pip install declarativedocs
```

## Supported formats

| Format | Schema | Status |
|--------|--------|--------|
| Presentation (.pptx) | `presentation:` | ✅ Available |
| Document (.docx) | `document:` | 🔜 Planned |
| PDF (.pdf) | `pdf:` | 🔜 Planned |

The compiler auto-detects the format from the YAML root key.

## Usage

### CLI

```bash
ddf my-deck.yaml                    # → my-deck.pptx (auto-detected)
ddf my-deck.yaml output.pptx        # → explicit output path
```

### Python API

```python
from ddf import compile

compile("my-deck.yaml", "output.pptx")
```

## Element types (Presentation)

| Type | Description |
|------|-------------|
| `text` | Text box with plain text, rich text runs, or bullet lists |
| `shape` | Rectangle, rounded rectangle, oval, line |
| `image` | Image from file path or base64 |
| `chart` | Bar, line, pie, doughnut, scatter, radar |
| `table` | Data table with styled cells |
| `group` | Auto-layout container (row or grid) with card styling |
| `icon` | Colored circle with glyph character |

## Features

- **Theme variables** — Define colors and fonts once, reference with `$name`
- **Slide masters** — Reusable templates with `{{placeholder}}` data binding
- **Auto-layout** — `row` and `grid` with configurable gap
- **Card styling** — Fill, radius, shadow, border on group items
- **Shadow presets** — `default`, `soft`, `hard`, `glow`, `up`
- **Bullet lists** — Proper indentation and tight spacing
- **Icons in cards** — Automatic positioning above text

## Quick example

```yaml
presentation:
  layout: "16x9"
  theme:
    colors:
      primary: "1E2761"
      white: "FFFFFF"
    fonts:
      heading: Georgia

  slides:
    - background: $primary
      elements:
        - type: text
          x: 1  y: 2  w: 8  h: 1.5
          text: "Hello DDF"
          font: $heading
          size: 44
          color: $white
          bold: true
          align: center
```

```bash
ddf hello.yaml  # → hello.pptx
```

## Schema

See the full [DDF specification](https://github.com/declarativedocs/spec).

## Examples

See the [examples/](examples/) directory for complete YAML files.

## Why DDF?

LLMs currently write 800+ lines of imperative library code to produce a 10-slide deck. DDF describes the same deck in ~200 lines of YAML. That's 3-5x fewer tokens, with significantly fewer bugs.

DDF is a declarative spec — the LLM describes *what* it wants, the compiler figures out *how*. The YAML is the contract, the compiler is a swappable implementation detail.

## License

Apache 2.0
