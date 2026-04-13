"""CLI entry point: python -m ddf_pptx <input.yaml> [output.pptx]"""
import sys
import re
from .compiler import compile_yaml

def main():
    if len(sys.argv) < 2:
        print("Usage: ddf-pptx <input.yaml> [output.pptx]")
        print("       python -m ddf_pptx <input.yaml> [output.pptx]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else re.sub(r"\.ya?ml$", ".pptx", inp, flags=re.I)
    try:
        compile_yaml(inp, out)
        print(f"✓ {out}")
    except Exception as e:
        print(f"✗ {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
