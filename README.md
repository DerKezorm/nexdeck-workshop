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

### Downloads

#### [Downloads](entries/188376159/test-downloads) (test)

Card, version 1.1.0, reach: read, by [DerKezorm](https://github.com/DerKezorm), 1 thumbs up

Shows the torrents of a download client with their progress. A test entry that stays as test data.

![Preview, light](entries/188376159/test-downloads/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/test-downloads/preview-dark.png#gh-dark-mode-only)

### Other

#### [Example box](entries/188376159/test-box) (test)

Connection, version -, reach: login, by [DerKezorm](https://github.com/DerKezorm), 0 thumbs up

A made-up connection that signs in with a user name and a password. A test entry that stays as test data.

![Preview, light](entries/188376159/test-box/preview-light.png#gh-light-mode-only)![Preview, dark](entries/188376159/test-box/preview-dark.png#gh-dark-mode-only)


<!-- entries:end -->

## What is in this repository

| Path | What |
|---|---|
| `entries/<github user id>/<short name>/` | One entry: `definition.yaml`, `README.md`, `CHANGELOG.md`, `entry.json`, two preview pictures |
| `catalog.json` | The catalog nexdeck reads, made by the actions |
| `schema/` | The JSON schemas of a card and of a connection |
| `kit/` | The check and the drawing page, taken from nexdeck (see `kit/VERSION`) |
| `tools/` | The code of the actions |
| `MAINTAINERS` | The people who can update and remove any entry |
