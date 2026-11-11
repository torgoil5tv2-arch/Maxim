import os
import sys

# Додаємо кореневу директорію проєкту до шляхів пошуку модулів Python
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import app
