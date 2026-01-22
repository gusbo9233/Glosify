https://github.com/gusbo9233/Glosify.git

# Backup and fix sources.list
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup && \
sudo bash -c 'cat > /etc/apt/sources.list << EOF
deb http://archive.debian.org/debian buster main contrib non-free
deb http://archive.debian.org/debian-security buster/updates main contrib non-free
deb http://archive.debian.org/debian buster-updates main contrib non-free
EOF'

# Update
sudo apt update