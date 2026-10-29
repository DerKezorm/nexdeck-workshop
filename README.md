# nexdeck workshop

Custom cards and own connections for [nexdeck](https://github.com/DerKezorm/nexdeck), shared by the people who made them.

A **card** shows what you pick out of the answer of a service: a number, a few numbers, a list, a wall of pictures, or a layout of blocks.
A **connection** teaches nexdeck to talk to an app it does not know: the address, the sign-in and what is worth reading.
Neither one contains code. They are data that nexdeck checks and draws with its own parts.

Nothing here is installed by itself. In nexdeck, an administrator switches on the Card shop, browses this catalog and installs what they want.
Without nexdeck you can browse the list below.

## Submit

Use the Card shop in nexdeck (it hands the card in for you), or write the card in nexdeck's editor and use the
[submission form](../../issues/new?template=submit.yml). An action checks it against the same rules nexdeck applies when
you save a card, draws the preview pictures from the demo data and, when everything is green, adds it to the list and
closes your issue. If something is wrong, the comment says what, one reason per line. See [CONTRIBUTING.md](CONTRIBUTING.md).

Every submission is published under the [MIT License](LICENSE).

## Entries

<!-- entries:start -->

### Media

#### [Library](entries/188376159/immich-library)

Card, version 1.0.0, reach: read, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Shows what is in your Immich library at a glance: the number of photos and videos, how many people use it and how much space it takes. It needs the API key of an administrator.

![Preview, light](entries/188376159/immich-library/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/immich-library/preview-dark.png#gh-dark-mode-only)

#### [Missing movies](entries/188376159/radarr-missing)

Card, version 1.0.0, reach: read, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Shows how many of the movies in your Radarr library are monitored but still missing. The card turns yellow as soon as at least one movie is missing.

![Preview, light](entries/188376159/radarr-missing/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/radarr-missing/preview-dark.png#gh-dark-mode-only)

#### [Next episodes](entries/188376159/sonarr-next-episodes)

Card, version 1.0.1, reach: buttons, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Shows the series of your Sonarr library that have an episode coming, with the day it airs, the nearest first. Every row has a button that asks Sonarr to search the missing episodes of that series.

![Preview, light](entries/188376159/sonarr-next-episodes/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/sonarr-next-episodes/preview-dark.png#gh-dark-mode-only)

#### [Recently added](entries/188376159/jellyfin-recently-added)

Card, version 1.0.1, reach: read, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Shows the movies and series that were added to your Jellyfin library last, as a row of posters. Every poster has the title and the year underneath.

![Preview, light](entries/188376159/jellyfin-recently-added/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/jellyfin-recently-added/preview-dark.png#gh-dark-mode-only)

### Downloads

#### [Active downloads](entries/188376159/qbittorrent-active-downloads)

Card, version 1.0.0, reach: buttons, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Shows the torrents that qBittorrent is downloading right now, with their progress and speed. Every row has a Pause button that stops that torrent. The button needs qBittorrent 5.0 or newer.

![Preview, light](entries/188376159/qbittorrent-active-downloads/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/qbittorrent-active-downloads/preview-dark.png#gh-dark-mode-only)

### Server

#### [Server at a glance](entries/188376159/server-at-a-glance)

Card, version 1.0.0, reach: read, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Shows the first node of your Proxmox host with its processor and memory load, and the guests of the cluster with their state. The card only reads and changes nothing. It was checked against a live Proxmox VE 9 host.

![Preview, light](entries/188376159/server-at-a-glance/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/server-at-a-glance/preview-dark.png#gh-dark-mode-only)

### Other

#### [NocoDB](entries/188376159/nocodb)

Connection, version -, reach: read, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Connects nexdeck to NocoDB, the spreadsheet-like front end for databases. It uses an API token that is sent in the header xc-token, so there is no sign-in to keep. Your cards can then read the bases and, with a path, the rows of a table.

![Preview, light](entries/188376159/nocodb/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/nocodb/preview-dark.png#gh-dark-mode-only)

#### [Shiori](entries/188376159/shiori)

Connection, version -, reach: login, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Connects nexdeck to Shiori, a simple bookmarks manager you host yourself. It signs in with your account and keeps the session. Your cards can then read the latest bookmarks and the tags.

![Preview, light](entries/188376159/shiori/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/shiori/preview-dark.png#gh-dark-mode-only)

#### [Wallabag](entries/188376159/wallabag)

Connection, version -, reach: login, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

Connects nexdeck to Wallabag, the read-it-later service you host yourself. It signs in with the API client and the account of the Wallabag user, the way the apps of Wallabag do, and keeps the session. Your cards can then read the entries and the tags.

![Preview, light](entries/188376159/wallabag/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/wallabag/preview-dark.png#gh-dark-mode-only)


<!-- entries:end -->

## What is in this repository

| Path | What |
|---|---|
| `entries/<github user id>/<short name>/` | One entry: `definition.yaml`, `README.md`, `CHANGELOG.md`, `entry.json`, two preview pictures |
| `catalog.json` | The catalog nexdeck reads, made by the actions |
| `schema/` | The JSON schemas of a card and of a connection |
| `kit/` | The check and the drawing page, taken from nexdeck (see `kit/VERSION`) |
| `tools/` | The code of the actions |
| `state.json` | The moment up to which the last run took up issues and comments (made by the actions) |
| `orders/` | Removals started by hand that no run has carried out yet (made by the actions) |
| `MAINTAINERS` | The people who can update and remove any entry |
| `starters.json` | The ids of the entries that nexdeck offers as examples to start from; only maintainers change it |
