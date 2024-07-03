from setuptools import setup, find_packages

setup(
    name='ratcrawler',
    version='1.0.0',  
    packages=find_packages(),  
    py_modules=['ratcrawler'],
    install_requires=[
        'requests>=2.28.1',
        'Pillow>=10.4.0',
        'opencv-python>=4.10.0.84',
    ],
    entry_points={
        'console_scripts': [
            'ratcrawler=ratcrawler:main',
        ],
    },
    author='burnem',  
    author_email='dfkburnem@gmail.com',  
    description='A GUI for finding summoning pairs in DFK',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/dfkburnem/Ratcrawler',  
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
    ],
    python_requires='>=3.6,<4',
)
