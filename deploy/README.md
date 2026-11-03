# Production setup

World66 runs from a dedicated Unix account, like Meelboek. The account owns the
checkout, virtualenv, generated search index and user-created passports. Its
systemd user service can be restarted without sudo.

## Layout

```text
/home/world66/app          Git checkout
/home/world66/venv         Python virtualenv
/home/world66/data         Generated and user-created data
/home/world66/staticfiles  collectstatic output
```

The checkout contains these ignored symlinks:

```text
search.db   -> ../data/search.db
passports   -> ../data/passports
media       -> ../data/media
staticfiles -> ../staticfiles
```

## One-time cutover

Create the account and its directories:

```bash
sudo adduser --disabled-password --gecos '' world66
sudo install -d -o world66 -g world66 -m 700 /home/world66/.config
sudo install -d -o world66 -g world66 -m 700 /home/world66/.ssh
sudo cp /home/django/.ssh/authorized_keys /home/world66/.ssh/authorized_keys
sudo chown world66:world66 /home/world66/.ssh/authorized_keys
sudo chmod 600 /home/world66/.ssh/authorized_keys
sudo install -d -o world66 -g world66 -m 755 \
  /home/world66/data/passports /home/world66/data/media /home/world66/staticfiles
sudo -u world66 git clone https://github.com/DOsinga/world66.git /home/world66/app
sudo -u world66 python3.12 -m venv /home/world66/venv
sudo -u world66 /home/world66/venv/bin/python -m pip install -r /home/world66/app/requirements.txt
```

Copy the generated search index and any user data from the old checkout, then
link them into the new one:

```bash
sudo cp /home/django/sites/world66/search.db /home/world66/data/search.db
sudo cp -a /home/django/sites/world66/passports/. /home/world66/data/passports/ 2>/dev/null || true
sudo cp -a /home/django/sites/world66/media/. /home/world66/data/media/ 2>/dev/null || true
sudo chown -R world66:world66 /home/world66/data
sudo -u world66 ln -s ../data/search.db /home/world66/app/search.db
sudo -u world66 ln -s ../data/passports /home/world66/app/passports
sudo -u world66 ln -s ../data/media /home/world66/app/media
sudo -u world66 ln -s ../staticfiles /home/world66/app/staticfiles
```

Install the service files. Copy the secret values from the old system service
into `world66.env`; do not copy that file into Git.

```bash
sudo install -Dm644 -o world66 -g world66 \
  /home/world66/app/deploy/world66.service \
  /home/world66/.config/systemd/user/world66.service
sudo install -Dm600 -o world66 -g world66 \
  /home/world66/app/deploy/world66.env.example \
  /home/world66/.config/world66.env
sudoedit /home/world66/.config/world66.env
sudo loginctl enable-linger world66
sudo -u world66 XDG_RUNTIME_DIR=/run/user/$(id -u world66) systemctl --user daemon-reload
sudo -u world66 XDG_RUNTIME_DIR=/run/user/$(id -u world66) systemctl --user enable --now world66
```

Build static files and verify the new service before changing traffic:

```bash
ssh world66@douwe.com /home/world66/app/scripts/deploy_production
curl -H 'Host: world66.ai' http://127.0.0.1:8066/
```

Switch nginx, then stop the old root-managed service:

```bash
sudo install -m 644 /home/world66/app/deploy/nginx.conf /etc/nginx/sites-available/world66
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl disable --now world66
```

The search index is kept outside Git and preserved across deployments. Rebuild
it separately when search data needs refreshing; the production host does not
have the local MLX embedding model used by `indexer.py`.
