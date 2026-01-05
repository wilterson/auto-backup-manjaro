#!/bin/bash

set -e  # Exit on error

echo "============================================"
echo "[*] Refreshing pacman keyring..."
echo "============================================"

# Fix PGP signature issues (common on fresh installs)
sudo pacman -Sy --noconfirm archlinux-keyring manjaro-keyring
sudo pacman-key --init
sudo pacman-key --populate archlinux manjaro

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
echo "============================================"
echo "[*] Updating nameservers..."
echo "============================================"

echo -e "nameserver 8.8.8.8\nnameserver 8.8.4.4" | sudo tee /etc/resolv.conf

echo ""
echo "============================================"
echo "[*] Updating system..."
echo "============================================"

sudo pacman -Syyu --noconfirm git yay base-devel fish xdotool

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

echo ""
echo "============================================"
echo "[*] Installing Softwares..."
echo "============================================"

# Remove vim first (conflicts with gvim)
sudo pacman -Rns --noconfirm vim 2>/dev/null || true

# List of packages to install
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

# Track results
FAILED=()
INSTALLED=()

# Install packages one by one
for pkg in "${PACKAGES[@]}"; do
    echo ""
    echo "📦 Installing $pkg..."
    if yay -S --noconfirm --needed --answerdiff=None --answerclean=None "$pkg" 2>/dev/null; then
        INSTALLED+=("$pkg")
        echo "  ✅ $pkg installed"
    else
        FAILED+=("$pkg")
        echo "  ❌ $pkg failed"
    fi
done

# Show summary
echo ""
echo "============================================"
echo "📊 Software Installation Summary"
echo "============================================"
echo "  ✅ Installed: ${#INSTALLED[@]}"
echo "  ❌ Failed: ${#FAILED[@]}"

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

echo ""
echo "============================================"
echo "[*] Setting up directories..."
echo "============================================"

mkdir -p ~/Documents/Projects

echo ""
echo "============================================"
echo "[✓] Package installation complete!"
echo "============================================"
