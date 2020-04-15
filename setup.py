import setuptools

with open("README.MD", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="prayer",
    version="0.1.1",
    description="Library, for working with PRAY files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Creatures-Developer-Network/prayer",
    author="KeyboardInterrupt",
    author_email="keyboardinterrupt@keyboardinterrupt.com",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
    python_requires='>=3.6',
)
