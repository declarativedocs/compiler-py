"""CLI entry point: ddf <input.yaml> [output]"""
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: ddf <input.yaml> [output]")
        print("       python -m ddf <input.yaml> [output]")
        print()
        print("Auto-detects format from YAML root key:")
        print("  presentation:  → .pptx")
        print("  document:      → .docx")
        print("  pdf:           → .pdf")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        from . import compile
        result = compile(input_path, output_path)
        print(f"✓ {result}")
    except Exception as e:
        print(f"✗ {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
