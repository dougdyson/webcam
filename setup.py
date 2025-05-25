"""
Setup configuration for webcam-detection package.
Makes the human detection system available as a pip-installable package.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Advanced multi-modal human detection system with service integration"

# Read requirements from requirements.txt
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="webcam-detection",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Advanced multi-modal human detection system with service integration",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/webcam-detection",
    
    # Package configuration - find packages in src directory
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Include package data
    package_data={
        "": [
            "config/*.yaml",
            "config/*.yml",
        ],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=[
        "opencv-python>=4.8.0",
        "mediapipe>=0.10.0",
        "numpy>=1.24.0",
        "PyYAML>=6.0",
        "python-dotenv>=1.0.0",
        "dataclasses-json>=0.6.0",
    ],
    
    # Optional dependencies for service layer
    extras_require={
        "service": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "websockets>=12.0",
            "aiohttp>=3.9.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
        ],
        "all": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0", 
            "websockets>=12.0",
            "aiohttp>=3.9.0",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
        ]
    },
    
    # Entry points for CLI
    entry_points={
        "console_scripts": [
            "webcam-detection=src.cli.main:main",
            "webcam-detect=src.cli.main:main",
            "webcam-service=src.service.cli:main",
        ],
    },
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    
    # Keywords for discovery
    keywords=[
        "computer-vision",
        "human-detection", 
        "mediapipe",
        "opencv",
        "presence-detection",
        "multi-modal",
        "pose-detection",
        "face-detection",
        "service-integration",
        "api",
        "websocket",
        "real-time"
    ],
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/yourusername/webcam-detection/issues",
        "Source": "https://github.com/yourusername/webcam-detection",
        "Documentation": "https://github.com/yourusername/webcam-detection/blob/main/README.md",
    },
) 