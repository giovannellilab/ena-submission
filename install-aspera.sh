#!/usr/bin/env bash
set -e

echo "=== 1. Verifying Conda Environment ==="
if [ -z "$CONDA_PREFIX" ]; then
    echo "ERROR: No active Conda environment found! Please run 'conda activate aspera' first."
    exit 1
fi
echo "Active environment: $CONDA_PREFIX"

echo -e "\n=== 2. Fixing Conda Ruby Symlink ==="
RUBYGEMS_BIN_DIR="$CONDA_PREFIX/share/rubygems/bin"
mkdir -p "$RUBYGEMS_BIN_DIR"

if [ -f "$CONDA_PREFIX/bin/ruby" ]; then
    ln -sf "$CONDA_PREFIX/bin/ruby" "$RUBYGEMS_BIN_DIR/ruby"
    echo "Linked $CONDA_PREFIX/bin/ruby -> $RUBYGEMS_BIN_DIR/ruby"
else
    echo "ERROR: Ruby binary not found in $CONDA_PREFIX/bin. Run 'conda install -c conda-forge ruby' first."
    exit 1
fi

echo -e "\n=== 3. Setting GEM Environment Variables ==="
# Export GEM_PATH so Ruby knows where to look for installed gems in Conda
export GEM_HOME="$CONDA_PREFIX/share/rubygems"
export GEM_PATH="$CONDA_PREFIX/share/rubygems:$CONDA_PREFIX/lib/ruby/gems/3.1.0"
export PATH="$CONDA_PREFIX/bin:$RUBYGEMS_BIN_DIR:$PATH"

echo -e "\n=== 4. Installing IBM aspera-cli Gem ==="
gem install --bindir "$CONDA_PREFIX/bin" aspera-cli --force

echo -e "\n=== 5. Installing Transfer Engine (ascp) ==="
ascli config transferd install

echo -e "\n=== 6. Verification ==="
echo "ascli path:    $(which ascli)"
echo "ascli version: $(ascli --version)"

ascli conf preset set default server era


echo -e "\nSetup completed successfully!"
