from setuptools import setup, find_packages

from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="dev-ws",
    version="0.1.1",
    description="A CLI tool for managing multiple workspaces with git worktrees and live preview.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/luokinging/workspace-cli",
    author="Luoking",
    # author_email="", # User didn't provide email, skipping or using dummy? Best to skip if unknown.
    packages=find_packages(),
    install_requires=[
        "typer[all]",
        "pydantic",
        "watchdog",
    ],
    entry_points={
        "console_scripts": [
            "workspace=workspace_cli.main:app",
            "workspace-cli=workspace_cli.main:app", # Add alias
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
