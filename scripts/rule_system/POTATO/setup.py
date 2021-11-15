from setuptools import find_packages, setup

setup(
    name="potato",
    version="0.1",
    description="XAI human-in-the-loop information extraction framework",
    license="MIT",
    install_requires=[
        "beautifulsoup4",
        "tinydb",
        "pandas",
        "tqdm",
        "stanza",
        "sklearn",
        "eli5",
        "matplotlib",
        "graphviz",
        "openpyxl",
        "streamlit",
        "streamlit-aggrid",
    ],
    packages=find_packages(),
    zip_safe=False,
)
