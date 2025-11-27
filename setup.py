from setuptools import setup, find_packages

setup(
    name="workspace-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]",
        "pydantic",
        "watchdog",
    ],
    entry_points={
        "console_scripts": [
            "workspace=workspace_cli.main:app",
        ],
    },
)
