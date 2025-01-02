from setuptools import setup,find_packages

setup(
    name='py3langid',
	packages=find_packages(
	# All keyword arguments below are optional:
		include=['py3langid*','*rst'],  # ['*'] by default
		),
	package_data= {
		        'py3langid': ['data/*.plzma'],
		        '*': ['README.rst'],
				},
    url='https://github.com/adbar/py3langid',
    keywords=['language', 'identifier'],
    classifiers=[],
)
