"""
Declarative Document Format (DDF) — Python reference compiler
https://ddf.dev
"""

__version__ = "0.1.0"


def compile(input_path: str, output_path: str | None = None) -> str:
    """Compile a DDF YAML file to its target format.

    Auto-detects format from the YAML root key:
      presentation: → .pptx
      document:     → .docx  (planned)
      pdf:          → .pdf   (planned)

    Args:
        input_path:  Path to the DDF YAML file.
        output_path: Path for the output file. If omitted, replaces
                     the .yaml extension with the appropriate format.

    Returns:
        The output file path.
    """
    import re
    import yaml

    with open(input_path) as f:
        raw = yaml.safe_load(f)

    if "presentation" in raw:
        from .pptx.compiler import compile_yaml
        if not output_path:
            output_path = re.sub(r"\.ya?ml$", ".pptx", input_path, flags=re.I)
        return compile_yaml(input_path, output_path)

    elif "document" in raw:
        raise NotImplementedError("DDF Document (.docx) compiler is not yet available.")

    elif "pdf" in raw:
        raise NotImplementedError("DDF PDF compiler is not yet available.")

    else:
        raise ValueError(
            "Unrecognized DDF schema. Expected a root key of: "
            "presentation, document, or pdf"
        )
