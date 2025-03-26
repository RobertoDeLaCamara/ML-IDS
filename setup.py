from setuptools import setup, find_packages

setup(
    name="ml-ids",  
    version="0.1",
    packages=find_packages(where="src"),  # Loops through 'src' to find packages
    package_dir={"": "src"},  # Indicates that the root package is in 'src'
    install_requires=[],  # Here you can add the dependencies
    extras_require={"test": ["pytest", "pytest-cov", "requests-mock"]},  # Dependencies for testing
    tests_require=["pytest", "pytest-cov", "requests-mock"],  # Dependencies for testing
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "train-model=src.train_model:main",
            "train-server=src.train_server:main"
        ]
    }
)
