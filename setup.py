from setuptools import setup, find_packages

setup(
    name="tuat-self-healing-agent",
    version="1.0.0",
    description="Autonomous Multi-Agent Coding Assistant with Self-Healing TDD Loop and Localhost Security",
    author="Developer",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "duckduckgo-search>=6.1.7",
        "openai>=1.12.0",
        "pydantic>=2.6.0",
        "google-generativeai>=0.3.0",
        "pyyaml>=6.0.1",
        "pytest>=8.0.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.28.0",
        "jinja2>=3.1.3",
        "rich>=13.7.1"
    ],
    entry_points={
        "console_scripts": [
            "heal=main:main_entry",
            "shc=main:main_entry"
        ]
    },
    python_requires=">=3.10",
)
