#!/usr/bin/env bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Guidely Backend Non-Sudo Setup ===${NC}\n"

# 1. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed or not in PATH.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Found Python version: ${GREEN}${PYTHON_VERSION}${NC}"

# 2. Create virtual environment without pip (bypasses missing python3-venv / ensurepip)
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "Creating virtual environment at ./${VENV_DIR} using --without-pip..."
    python3 -m venv --without-pip "$VENV_DIR"
else
    echo -e "Virtual environment directory ${VENV_DIR} already exists."
fi

# 3. Bootstrap pip inside the virtual environment if not present
if [ ! -f "${VENV_DIR}/bin/pip" ]; then
    echo -e "Bootstrapping pip into ${VENV_DIR} using get-pip.py..."
    GET_PIP_TMP=$(mktemp)
    if command -v curl &> /dev/null; then
        curl -sSL https://bootstrap.pypa.io/get-pip.py -o "$GET_PIP_TMP"
    elif command -v wget &> /dev/null; then
        wget -qO "$GET_PIP_TMP" https://bootstrap.pypa.io/get-pip.py
    else
        echo -e "${RED}Error: Neither curl nor wget was found to download get-pip.py.${NC}"
        rm -f "$GET_PIP_TMP"
        exit 1
    fi

    "${VENV_DIR}/bin/python" "$GET_PIP_TMP" --quiet
    rm -f "$GET_PIP_TMP"
    echo -e "${GREEN}pip successfully bootstrapped in virtual environment!${NC}"
else
    echo -e "${GREEN}pip is already available in ${VENV_DIR}/bin/pip${NC}"
fi

# 4. Install backend dependencies
echo -e "\nInstalling backend dependencies from requirements.txt..."
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -r requirements.txt

# 5. Set up .env file if missing
if [ ! -f ".env" ]; then
    echo -e "\nCopying .env.example to .env..."
    cp .env.example .env
    echo -e "${YELLOW}Created .env file. Please edit .env and configure your GEMINI_API_KEY.${NC}"
else
    echo -e "\n.env file already exists."
fi

echo -e "\n${GREEN}===========================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "To start the backend server, run:\n"
echo -e "  ${CYAN}source venv/bin/activate${NC}"
echo -e "  ${CYAN}uvicorn backend.main:app --reload --port 8000${NC}\n"
