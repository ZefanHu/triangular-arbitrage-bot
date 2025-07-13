import sys
import os

def test_python_version():
    print(f"Python version: {sys.version}")

def test_project_structure():
    project_dirs = [
        'config',
        'core', 
        'models',
        'utils',
        'tests',
        'okex'
    ]
    
    for dir_name in project_dirs:
        assert os.path.exists(dir_name), f"Directory '{dir_name}' does not exist"
        assert os.path.isdir(dir_name), f"'{dir_name}' is not a directory"
        
        init_file = os.path.join(dir_name, '__init__.py')
        assert os.path.exists(init_file), f"'{init_file}' does not exist"
    
    print("All project directories exist and have __init__.py files")

if __name__ == "__main__":
    test_python_version()
    test_project_structure()
    print("Environment validation completed successfully!")