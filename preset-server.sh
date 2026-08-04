#!/usr/bin/env bash
set -e

echo -e "\n=== 7. Configuring ENA Preset ==="
# Export the password environment variable for authentication

# Add the ENA custom preset

ascli conf preset update era   --url=ssh://fasp.sra.ebi.ac.uk:33001   --username=Webin-55129   --ts=@json:'{"target_rate_kbps":300000}'

# Set 'era' as the default preset for server operations

# in the case of private dataset use:

#export ASPERA_SCP_PASS='your_password_here'
#ascli conf preset update mypriv   --url=ssh://fasp.sra.ebi.ac.uk:33001   --username=Webin-55129   --ts=@json:'{"target_rate_kbps":300000}'
