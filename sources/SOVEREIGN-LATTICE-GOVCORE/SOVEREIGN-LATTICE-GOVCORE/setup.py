from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="sovereign-lattice-govcore",
    version="1.0.0",
    author="Deonte Watts",
    description="Evidence-lattice AI system for government and critical infrastructure",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf-8") if (Path(__file__).parent / "README.md").exists() else "",
    url="https://github.com/deontewatts/SOVEREIGN-LATTICE-GOVCORE",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["fastapi>=0.111.0","uvicorn[standard]>=0.29.0","pydantic>=2.7.0","python-dotenv>=1.0.0"],
    extras_require={"dev": ["pytest>=8.0","ruff>=0.4","pytest-cov>=5.0"]},
)
