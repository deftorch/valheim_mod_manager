"""
Setup script for Valheim Mod Manager
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="valheim-mod-manager",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A modern mod manager for Valheim with smart deployment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/valheim-mod-manager",
    packages=find_packages(exclude=['tests', 'scripts', 'docs']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.4.3',
            'pytest-qt>=4.2.0',
            'pytest-cov>=4.1.0',
            'black>=23.12.1',
            'pylint>=3.0.3',
            'mypy>=1.8.0',
        ],
        'build': [
            'pyinstaller>=6.3.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'valheim-mod-manager=main:main',
        ],
        'gui_scripts': [
            'valheim-mod-manager-gui=main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': [
            'resources/**/*',
            'config/*.py',
        ],
    },
    zip_safe=False,
    project_urls={
        "Bug Reports": "https://github.com/yourusername/valheim-mod-manager/issues",
        "Source": "https://github.com/yourusername/valheim-mod-manager",
        "Documentation": "https://github.com/yourusername/valheim-mod-manager/wiki",
    },
    keywords="valheim mod manager modding gaming thunderstore",
)
