# ddf-pptx

Python reference compiler for the [DDF Presentation](https://github.com/declarativedocs/spec) schema. Turns YAML into .pptx files.

Part of the [Declarative Document Format](https://ddf.dev) project. Created by [WeAreBrain](https://wearebrain.com).

## Install

```bash
pip install ddf-pptx
```

## Usage

### CLI

```bash
ddf-pptx my-deck.yaml                  # → my-deck.pptx
ddf-pptx my-deck.yaml output.pptx      # → output.pptx
python -m ddf_pptx my-deck.yaml        # same thing
```

### Python API

```python
from ddf_pptx import compile_yaml

compile_yaml("my-deck.yaml", "output.pptx")
```

### From string

```python
import yaml
from ddf_pptx.compiler import compile_presentation

spec = yaml.safe_load("""
presentation:
  slides:
    - background: "1E2761"
      elements:
        - type: text
          x: 1  y: 2  w: 8  h: 1.5
          text: Hello DDF
          size: 44
          color: FFFFFF
          bold: true
          align: center
""")
# compile_presentation(spec["presentation"], "output.pptx")
```

## Supported elements

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

- **Theme variables** — `$primary`, `$heading`, etc.
- **Slide masters** — Reusable templates with `{{placeholder}}` binding
- **Auto-layout** — `row` and `grid` with configurable gap
- **Card styling** — Fill, radius, shadow, border on group items
- **Shadow presets** — `default`, `soft`, `hard`, `glow`, `up`
- **Bullet lists** — Proper indentation and tight spacing
- **Icons in cards** — Automatic positioning above text

## Schema

See the full [DDF Presentation specification](https://github.com/declarativedocs/spec/blob/main/presentation.v0.1.0.yaml).

## Examples

See the [examples/](examples/) directory for complete YAML files.

## License

Apache 2.0
