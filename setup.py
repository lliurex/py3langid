from setuptools import setup,find_packages

setup(
    name='py3langid',
	packages=find_packages(
	# All keyword arguments below are optional:
		include=['py3langid*'],  # ['*'] by default
		),
	package_data= {
		'py3langid': ['data/*.plzma'],
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
