import setuptools
import os 

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

long_desc = ""
if os.path.exists('README.md'):
    with open("README.md", "r") as f:
        long_desc = f.read()

setuptools.setup( # TODO
    name = "lerrix",
    version = "1.0",
    license = 'TODO',
    author = 'Andrea Ivkovic',
    author_email = 'andrea.ivkovic01@gmail.com',
    description = 'Scrape, download and unsilence videos from sharepoint',
    long_description = long_desc,
    long_description_content_type="text/markdown",
    packages = setuptools.find_packages(),
    install_requires = requirements,
    entry_points = {
        "console_scripts": [
            "ler-down = cli.ler-down:main",
            "lerrix = cli.lerrix:main",
        ]
    }
)
