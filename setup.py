from setuptools import setup, find_packages

setup(
    name="hq-agent-sdk",
    version="1.0.0",
    description="HQ Agent SDK for LLM session management and tool calling",
    author="HQ Team",
    packages=find_packages(),
    install_requires=[
        "openai",
        "typing_extensions",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)