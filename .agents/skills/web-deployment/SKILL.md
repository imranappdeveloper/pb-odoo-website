---
name: web-deployment
description: Automates the zero-downtime deployment of the Pacific Boeki Website integration module (pb_website), including version bumping, remote server git pull, initial module installation or update on dummy port, service restart, and port-based health check. Use when deploying pb_website to production.
---

# Fast Website Module Deployment

## Quick start

Run the deployment process using the command sequence specified in this skill to ensure safe and zero-downtime releases.

## Workflows

### Zero-Downtime Deployment Flow
Follow this checklist to deploy:

- [ ] **Identify Next Version**: Determine the next release version number from the current branch list.
- [ ] **Update Manifest**: Bump the version in `pb_website/__manifest__.py` by incrementing the minor part (e.g. `1.X` to `1.Y`).
- [ ] **Commit & Push**: Commit the manifest change with message "Release vX: Version maintenance bump" and push to origin main.
- [ ] **Record Current Hash**: Save the current commit hash on the remote server to support manual rollback if needed.
- [ ] **Deploy to Server**: SSH into the remote server, pull the latest code, perform the database install/update on a dummy port (`--http-port=8899`), and restart the Odoo service.
- [ ] **Health Check**: Verify the server is UP on port `7079` by polling for HTTP 200 or 303 status.
- [ ] **Verify Version**: Confirm that the correct version is active on the server.
- [ ] **Release Branch**: Create and push a new `release/vX` branch.

### Deployment Command Script
Use this script for automated execution:
```bash
# Variables
SERVER_IP="45.32.45.184"
REMOTE_PATH="/opt/odoo18/pb_website"
PORT=7079
MODULE="pb_website"

# 1. Identify Next Version and Update Files
NEXT_VER=$(git branch -r | grep "origin/release/v" | sed 's/.*v//' | sort -n | tail -1 | awk '{print $1 + 1}')
if [ -z "$NEXT_VER" ]; then NEXT_VER=1; fi

echo "Bumping version to 1.$NEXT_VER..."
# Update manifest version
sed -i '' "s/'version': '[^']*'/'version': '1.$NEXT_VER'/" pb_website/__manifest__.py
# Update menu version text
sed -i '' "s/Website Admin (v[^)]*)/Website Admin (v1.$NEXT_VER)/" pb_website/views/menus.xml

# 2. Commit and Push Version Bump
git add pb_website/__manifest__.py pb_website/views/menus.xml
git commit -m "Release v$NEXT_VER: Version maintenance bump"
git push origin main

# 3. Record current hash for easy manual rollback
if ssh root@$SERVER_IP "[ -d $REMOTE_PATH/.git ]"; then
  PREV_HASH=$(ssh root@$SERVER_IP "cd $REMOTE_PATH && git rev-parse HEAD")
  echo "Starting optimized deployment. Previous hash: $PREV_HASH"
else
  echo "First-time deployment. No previous hash."
fi

# 4. Clone or Pull changes on Server and Install/Update
ssh root@$SERVER_IP << EOF
  if [ ! -d "$REMOTE_PATH" ]; then
    echo "Cloning repository on server..."
    git clone git@github.com:imranappdeveloper/pb-odoo-website.git $REMOTE_PATH
    chown -R odoo18:odoo18 $REMOTE_PATH
  fi

  cd $REMOTE_PATH
  git pull

  # Update Apps list and check if module is already installed on pb_tus
  MODULE_STATUS=$(sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo-bin shell -c /etc/odoo18.conf -d pb_tus --stop-after-init --http-port=8899 --shell-interface=python << 'PY_EOF'
env['ir.module.module'].update_list()
module = env['ir.module.module'].search([('name', '=', 'pb_website')])
print(module.state if module else 'not_found')
PY_EOF
  )

  # Trim whitespace from output
  MODULE_STATUS=$(echo \$MODULE_STATUS | tr -d '\r\n[:space:]')
  echo "Module status in Odoo DB: \$MODULE_STATUS"

  if [ "\$MODULE_STATUS" = "installed" ] || [ "\$MODULE_STATUS" = "to upgrade" ]; then
    echo "Updating module pb_website on dummy port (8899)..."
    sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo-bin -c /etc/odoo18.conf -u $MODULE -d pb_tus --stop-after-init --http-port=8899
  else
    echo "Installing module pb_website for the first time on dummy port (8899)..."
    sudo -u odoo18 /opt/odoo18/venv/bin/python3 /opt/odoo18/odoo-bin -c /etc/odoo18.conf -i $MODULE -d pb_tus --stop-after-init --http-port=8899
  fi

  # Restart main Odoo service
  systemctl restart odoo18.service
EOF

# 5. Fast Health Check
echo "Verifying server status on port $PORT..."
for i in {1..15}; do
  HTTP_STATUS=\$(curl -s -o /dev/null -w "%{http_code}" http://\$SERVER_IP:\$PORT || echo "000")
  if [ "\$HTTP_STATUS" = "200" ] || [ "\$HTTP_STATUS" = "303" ]; then
    echo "✅ Server is UP (Status: \$HTTP_STATUS)"
    SUCCESS=1
    break
  fi
  echo "Waiting for server... (\$i/15)"
  sleep 2
done

if [ -z "\$SUCCESS" ]; then
    echo "❌ Health check failed after 30s. Check server logs."
    exit 1
fi

# 6. Verify Deployed Version
echo "Verifying deployed version on server..."
DEPLOYED_VER=\$(ssh root@$SERVER_IP "grep \"'version'\" $REMOTE_PATH/pb_website/__manifest__.py | cut -d\"'\" -f4")
echo "✅ Deployed Version: \$DEPLOYED_VER"

# 7. Create and Push Release Branch
echo "Creating release/v$NEXT_VER..."
git checkout -b release/v$NEXT_VER
git push origin release/v$NEXT_VER
git checkout main
```

### Safety and Rollback
- **Dummy Port (8899)**: Always install/update database with `--stop-after-init --http-port=8899` to keep production server listening on `7079` during schema update.
- **Rollback**: To rollback code and restore the previous state:
  - If initial release failed and you need to uninstall/revert:
    `ssh root@45.32.45.184 "cd /opt/odoo18/pb_website && git reset --hard <PREV_HASH> && systemctl restart odoo18.service"`
  - Or comment out the `/opt/odoo18/pb_website` from `addons_path` in `/etc/odoo18.conf` and restart to completely disable.
