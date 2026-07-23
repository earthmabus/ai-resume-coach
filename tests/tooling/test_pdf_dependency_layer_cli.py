from pathlib import Path

from tools.build.pdf_dependency_layer import parse_args


ROOT = Path(__file__).resolve().parents[2]


def test_pdf_dependency_layer_cli_defaults_to_repository_root():
    args = parse_args([])

    assert args.repository_root == ROOT
    assert (args.repository_root / "lambda_layer" / "requirements.txt").is_file()
