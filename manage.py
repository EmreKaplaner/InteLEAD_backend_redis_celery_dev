#!/usr/bin/env python3
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Force binding to 0.0.0.0:8000 regardless of the environment
    if len(sys.argv) < 2 or sys.argv[1] == 'runserver':
        sys.argv = sys.argv[:2] + ['0.0.0.0:8000']

    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
