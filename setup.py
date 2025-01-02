from setuptools import setup,find_packages

setup(
    name='py3langid',
	packages=find_packages(
	# All keyword arguments below are optional:
		include=['py3langid','py3langid.*'],  # ['*'] by default
		exclude=['py3langid.tests','tests'],  # ['*'] by default
		),
	package_data= {
		'py3langid': ['data/*.plzma'],
		'*': ['README.rst'],
		},
	entry_points={
		'console_scripts': [
            'langid = py3langid.langid:main',
	        ]
		},
    url='https://github.com/adbar/py3langid',
    keywords=['language', 'identifier'],
    classifiers=[],
)
