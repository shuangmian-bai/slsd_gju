from setuptools import setup, find_packages

setup(
    name="slsd-pingjiao",
    version="1.0.0",
    description="湖南水利水电职业技术学院自动评教脚本",
    py_modules=["login", "pingjiao"],
    python_requires=">=3.8",
    install_requires=[
        "requests",
        "beautifulsoup4",
        "pycryptodome",
        "ddddocr",
    ],
    entry_points={
        "console_scripts": [
            "pingjiao=pingjiao:main",
            "sso-login=login:main",
        ],
    },
)
