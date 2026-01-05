#!/bin/bash

# ============================================
# Interactive Package Installer for Manjaro
# ============================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Options (1 = enabled, 0 = disabled)
declare -A OPTIONS=(
    [1]="1"  # Refresh keyring
    [2]="1"  # Update mirrors
    [3]="1"  # Update system
    [4]="1"  # Setup Fish shell
    [5]="1"  # Install software
    [6]="1"  # Configure Docker
    [7]="1"  # Setup directories
)

declare -A OPTION_NAMES=(
    [1]="Refresh pacman keyring"
    [2]="Update mirrors & DNS"
    [3]="Update system (pacman)"
    [4]="Setup Fish shell + NVM"
    [5]="Install software (yay)"
    [6]="Configure Docker"
    [7]="Setup directories"
)

# Software packages list
PACKAGES=(
    gvim
    zip
    google-chrome
    brave-bin
    spotify
    visual-studio-code-bin
    cursor-bin
    docker
    docker-compose
    kubectl
    postman-bin
    apidog-bin
    ttf-fira-code
    flatpak
    yarn
)

show_menu() {
    clear
    echo "============================================"
    echo "  🛠️  Manjaro Setup Script"
    echo "============================================"
    echo ""
    echo "Toggle options with their number, then press 'r' to run:"
    echo ""

    for i in {1..7}; do
        if [ "${OPTIONS[$i]}" = "1" ]; then
            echo -e "  ${GREEN}[✓]${NC} $i. ${OPTION_NAMES[$i]}"
        else
            echo -e "  ${RED}[ ]${NC} $i. ${OPTION_NAMES[$i]}"
        fi
    done

    echo ""
    echo "--------------------------------------------"
    echo "  a = Select all    n = Deselect all"
    echo "  r = Run selected  q = Quit"
    echo "============================================"
}

toggle_option() {
    local num=$1
    if [ "${OPTIONS[$num]}" = "1" ]; then
        OPTIONS[$num]="0"
    else
        OPTIONS[$num]="1"
    fi
}

select_all() {
    for i in {1..7}; do
        OPTIONS[$i]="1"
    done
}

deselect_all() {
    for i in {1..7}; do
        OPTIONS[$i]="0"
    done
}

# ============================================
# Step Functions
# ============================================

step_refresh_keyring() {
    echo ""
    echo "============================================"
    echo "[*] Refreshing pacman keyring..."
    echo "============================================"
    sudo pacman -Sy --noconfirm archlinux-keyring manjaro-keyring
    sudo pacman-key --init
    sudo pacman-key --populate archlinux manjaro
}

step_update_mirrors() {
    echo ""
    echo "============================================"
    echo "[*] Configuring system..."
    echo "============================================"

    # Enable colored output in pacman
    sudo sed -i -e 's/#Color/Color/g' /etc/pacman.conf

    # Speed up package compression
    sudo sed -i -e 's/pkg.tar.xz/pkg.tar/g' /etc/makepkg.conf

    # Find fastest mirrors
    sudo pacman-mirrors --fasttrack

    echo ""
    echo "[*] Updating nameservers..."
    echo -e "nameserver 8.8.8.8\nnameserver 8.8.4.4" | sudo tee /etc/resolv.conf
}

step_update_system() {
    echo ""
    echo "============================================"
    echo "[*] Updating system..."
    echo "============================================"
    sudo pacman -Syyu --noconfirm git yay base-devel fish xdotool
}

step_setup_fish() {
    echo ""
    echo "============================================"
    echo "[*] Setting up Fish shell..."
    echo "============================================"

    # Change default shell to fish
    sudo chsh -s $(which fish) $USER

    # Install fisher and nvm.fish using fish
    fish -c '
        curl -sL https://git.io/fisher | source && fisher install jorgebucaran/fisher
        fisher install jorgebucaran/nvm.fish
        nvm install lts
        set --universal nvm_default_version lts
    '
}

step_install_software() {
    echo ""
    echo "============================================"
    echo "[*] Installing Softwares..."
    echo "============================================"

    # Remove vim first (conflicts with gvim)
    sudo pacman -Rns --noconfirm vim 2>/dev/null || true

    # Track results
    FAILED=()
    INSTALLED=()

    # Install packages one by one
    for pkg in "${PACKAGES[@]}"; do
        echo ""
        echo "📦 Installing $pkg..."
        if yay -S --noconfirm --needed --answerdiff=None --answerclean=None "$pkg" 2>/dev/null; then
            INSTALLED+=("$pkg")
            echo -e "  ${GREEN}✅ $pkg installed${NC}"
        else
            FAILED+=("$pkg")
            echo -e "  ${RED}❌ $pkg failed${NC}"
        fi
    done

    # Show summary
    echo ""
    echo "============================================"
    echo "📊 Software Installation Summary"
    echo "============================================"
    echo -e "  ${GREEN}✅ Installed: ${#INSTALLED[@]}${NC}"
    echo -e "  ${RED}❌ Failed: ${#FAILED[@]}${NC}"

    if [ ${#FAILED[@]} -gt 0 ]; then
        echo ""
        echo "  Failed packages:"
        for pkg in "${FAILED[@]}"; do
            echo "    - $pkg"
        done
        echo ""
        echo "  Retry failed with:"
        echo "    yay -S --noconfirm ${FAILED[*]}"
    fi
    echo "============================================"
}

step_configure_docker() {
    echo ""
    echo "============================================"
    echo "[*] Configuring Docker..."
    echo "============================================"

    # Create docker group if it doesn't exist
    sudo groupadd docker 2>/dev/null || true

    # Add current user to docker group
    sudo usermod -aG docker $USER

    # Enable and start Docker services
    sudo systemctl enable docker.service
    sudo systemctl enable containerd.service
    sudo systemctl start docker
}

step_setup_directories() {
    echo ""
    echo "============================================"
    echo "[*] Setting up directories..."
    echo "============================================"
    mkdir -p ~/Documents/Projects
    echo "  ✅ Created ~/Documents/Projects"
}

# ============================================
# Run Selected Steps
# ============================================

run_selected() {
    clear
    echo "============================================"
    echo "  🚀 Running selected steps..."
    echo "============================================"

    [ "${OPTIONS[1]}" = "1" ] && step_refresh_keyring
    [ "${OPTIONS[2]}" = "1" ] && step_update_mirrors
    [ "${OPTIONS[3]}" = "1" ] && step_update_system
    [ "${OPTIONS[4]}" = "1" ] && step_setup_fish
    [ "${OPTIONS[5]}" = "1" ] && step_install_software
    [ "${OPTIONS[6]}" = "1" ] && step_configure_docker
    [ "${OPTIONS[7]}" = "1" ] && step_setup_directories

    echo ""
    echo "============================================"
    echo -e "  ${GREEN}[✓] All selected steps complete!${NC}"
    echo "============================================"
    echo ""
    echo "⚠️  Log out and back in for shell/docker changes."
}

# ============================================
# Main Menu Loop
# ============================================

# Check for --all flag (run everything without menu)
if [ "$1" = "--all" ] || [ "$1" = "-a" ]; then
    select_all
    run_selected
    exit 0
fi

# Interactive menu
while true; do
    show_menu
    read -n 1 -s choice

    case $choice in
        [1-7])
            toggle_option $choice
            ;;
        a|A)
            select_all
            ;;
        n|N)
            deselect_all
            ;;
        r|R)
            run_selected
            exit 0
            ;;
        q|Q)
            echo ""
            echo "Cancelled."
            exit 0
            ;;
    esac
done
