#!/usr/bin/env python
import os
import sys
import subprocess

def run_coverage():
    """Run coverage analysis for autoreply app"""
    os.chdir('/Users/aalviian/Documents/Julo/products/cx-service')
    
    # Run tests with coverage
    subprocess.run([
        'uv', 'run', 'coverage', 'run', 
        '--source=src/autoreply', 
        'src/manage.py', 'test', 'autoreply.tests'
    ])
    
    # Generate report
    subprocess.run(['uv', 'run', 'coverage', 'report', '--show-missing'])
    
    # Generate HTML report
    subprocess.run(['uv', 'run', 'coverage', 'html'])
    
    print("\nHTML coverage report generated at htmlcov/index.html")

if __name__ == '__main__':
    run_coverage()