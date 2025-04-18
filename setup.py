from setuptools import setup, find_packages

setup(
    name="ml-ids",
    version="0.1",
    packages=find_packages(where="src"),  # Descubre los paquetes en 'src'
    package_dir={"": "src"},
    install_requires=[],  # Las dependencias se gestionan por requirements.txt específicos
    extras_require={
        "notebooks": [
            # Instalar con: pip install -r requirements.txt (en la raíz)
        ],
        "inference_server": [
            # Instalar con: pip install -r src/inference_server/requirements.txt
        ],
        "retraining_server": [
            # Instalar con: pip install -r src/retraining_server/requirements.txt
        ],
        "test": ["pytest", "pytest-cov", "requests-mock"]
    },
    python_requires=">=3.8",
)

# Uso recomendado:
# - Para notebooks y desarrollo: pip install -r requirements.txt (en la raíz)
# - Para el servidor de inferencia: pip install -r src/inference_server/requirements.txt
# - Para el servidor de reentrenamiento: pip install -r src/retraining_server/requirements.txt
# - Para tests: pip install pytest pytest-cov requests-mock
