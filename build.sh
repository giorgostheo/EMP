pip uninstall -y emp-package
python setup.py sdist bdist_wheel 
python -m pip install dist/emp_package-0.1.0-py3-none-any.whl