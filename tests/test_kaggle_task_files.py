from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks"


def test_u01_to_u10_task_files_follow_kaggle_percent_format_contract():
    files = sorted(TASKS.glob("u[0-9][0-9]_*.py"))
    assert len(files) == 10

    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "# %%" in source, path.name
        assert "import kaggle_benchmarks as kbench" in source, path.name
        assert "@kbench.task(" in source, path.name
        assert ".run(kbench.llm)" in source, path.name


def test_task_names_are_unique_and_suite_prefixed():
    files = sorted(TASKS.glob("u[0-9][0-9]_*.py"))
    names = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        marker = 'name="'
        start = source.index(marker) + len(marker)
        end = source.index('"', start)
        names.append(source[start:end])

    assert len(names) == len(set(names)) == 10
    assert all(name.startswith("unison-u") for name in names)
