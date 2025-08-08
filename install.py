#!/usr/bin/env python3
"""
Force One IT Lead Extractor - Quick Setup
Configuração rápida do sistema
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Execute command with description"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} - OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ERRO: {e}")
        return False


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required. Current: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True


def setup_environment():
    """Setup Python environment"""
    print("🚀 Force One IT Lead Extractor - Quick Setup\n")
    
    if not check_python_version():
        return False
    
    # Create virtual environment
    if not run_command("python -m venv venv", "Creating virtual environment"):
        return False
    
    # Activate and install requirements
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate && pip install -r requirements.txt"
    else:  # Linux/Mac
        activate_cmd = "source venv/bin/activate && pip install -r requirements.txt"
    
    if not run_command(activate_cmd, "Installing dependencies"):
        return False
    
    # Copy .env file
    if not Path('.env').exists():
        if Path('.env.example').exists():
            run_command("copy .env.example .env" if os.name == 'nt' else "cp .env.example .env", 
                       "Creating .env configuration file")
    
    # Create directories
    directories = ['data', 'data/cache', 'data/exports', 'logs']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Edit .env file with your API keys:")
    print("   - GOOGLE_MAPS_API_KEY (required)")
    print("   - HUBSPOT_API_KEY (optional)")
    print("   - LINKEDIN_USERNAME/PASSWORD (optional)")
    print("\n2. Test the installation:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("   python leadextractor.py --help")
    print("\n3. Run your first extraction:")
    print("   python leadextractor.py extract --sector technology --limit 10")
    
    return True


if __name__ == "__main__":
    success = setup_environment()
    sys.exit(0 if success else 1)