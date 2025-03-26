from setuptools import setup, find_packages

setup(
    name="ml-ids",  # Nombre del paquete
    version="0.1",
    packages=find_packages(where="src"),  # Busca paquetes dentro de 'src'
    package_dir={"": "src"},  # Indica que los paquetes están en 'src'
    install_requires=[],  # Aquí puedes incluir dependencias si es necesario
)
