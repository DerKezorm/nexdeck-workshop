"""Stands in for the registry of connections: the kinds and categories of that nexdeck, and no adapters."""

from types import SimpleNamespace

_KINDS = frozenset(['actualbudget', 'adguard', 'alertmanager', 'amp', 'anchor', 'arcane', 'aria2', 'audiobookshelf', 'authentik', 'autobrr', 'backrest', 'bazarr', 'beszel', 'blocky', 'bookorbit', 'bookstack', 'caddy', 'calendar', 'calibreweb', 'changedetection', 'cloudflare', 'coolify', 'core', 'cronicle', 'crowdsec', 'cup', 'custom', 'dashdot', 'dawarich', 'deluge', 'docker', 'dockhand', 'duplicati', 'elasticsearch', 'emby', 'esphome', 'evcc', 'filebrowserquantum', 'fileflows', 'firefly', 'forgejo', 'fortigate', 'freshrss', 'frigate', 'fritzbox', 'fronius', 'garage', 'gatus', 'ghostfolio', 'gitea', 'github', 'gitlab', 'glances', 'gluetun', 'goatcounter', 'gotify', 'grafana', 'grocy', 'hackernews', 'headscale', 'healthchecks', 'homeassistant', 'homebox', 'homebridge', 'ical', 'imap', 'immich', 'influxdb', 'jackett', 'jellyfin', 'jellyseerr', 'jellystat', 'jenkins', 'jsonapi', 'karakeep', 'kavita', 'keycloak', 'kimai', 'kitchenowl', 'kodi', 'komga', 'komodo', 'kopia', 'kubernetes', 'lemmy', 'lidarr', 'linkding', 'linkwarden', 'llamacpp', 'lubelogger', 'm3ueditor', 'mailcow', 'mailpit', 'maintainerr', 'mastodon', 'mealie', 'meilisearch', 'memos', 'metube', 'mikrotik', 'minecraft', 'miniflux', 'moonraker', 'myspeed', 'n8n', 'navidrome', 'netalertx', 'netbird', 'netbox', 'netdata', 'neutarr', 'nexbeat', 'nexbrand', 'nexcanvas', 'nexcrate', 'nexdiary', 'nexlore', 'nexmail', 'nexpaper', 'nexpulse', 'nexsift', 'nextcloud', 'nextdns', 'nextrmnl', 'nexview', 'nginxignition', 'nodered', 'nomad', 'npm', 'ntfy', 'nut', 'nzbget', 'octoprint', 'ollama', 'ombi', 'opendtu', 'openhab', 'openmediavault', 'openwebui', 'openwrt', 'opnsense', 'overseerr', 'owncast', 'pangolin', 'paperless', 'papra', 'patchmon', 'pbs', 'peanut', 'peertube', 'pfsense', 'photoprism', 'pihole', 'planka', 'plex', 'pocketid', 'portainer', 'prometheus', 'prowlarr', 'proxmenux', 'proxmox', 'pterodactyl', 'publicip', 'pulse', 'pyload', 'qbittorrent', 'qui', 'radarr', 'rclone', 'readarr', 'readeck', 'readmeabook', 'realdebrid', 'reclaimerr', 'registry', 'reolink', 'romm', 'rss', 'rtorrent', 'sabnzbd', 'scrutiny', 'seerr', 'semaphore', 'sftpgo', 'shelly', 'shlink', 'slskd', 'snmp', 'sonarr', 'speedtest', 'spoolman', 'sportarr', 'stalwart', 'stash', 'steam', 'stocks', 'synapse', 'syncthing', 'syncthingrelay', 'synology', 'tailscale', 'tandoor', 'tasmota', 'tautulli', 'tdarr', 'technitium', 'traccar', 'tracearr', 'traefik', 'transmission', 'trilium', 'truenas', 'tubearchivist', 'twitch', 'umami', 'unifi', 'unmanic', 'unraid', 'uptimekuma', 'uptimerobot', 'urbackup', 'vikunja', 'wallos', 'warrior', 'watchtower', 'wazuh', 'weather', 'wgeasy', 'wger', 'wikijs', 'wol', 'woodpecker', 'wud', 'xteve', 'yourspotify', 'youtube', 'zabbix', 'zerobyte'])
_CATEGORIES = frozenset(['basics', 'downloads', 'feeds', 'generic', 'hosts', 'media', 'monitoring', 'nas', 'network', 'other'])


def builtin_kinds():
    return _KINDS


def builtin_categories():
    return _CATEGORIES


def get_adapter(kind):
    if kind not in _KINDS:
        raise KeyError(kind)
    return SimpleNamespace(kind=kind, raw_read_commands=None)


def all_adapters():
    return []
