# Contributing

## Submitting a card or a connection

1. Build it in nexdeck (System, Custom cards) and test it with real data. Add demo data to a card: the preview pictures are drawn from them, and nobody else sees your real answers.
2. In nexdeck, use "Submit to the workshop". Or open the [form](../../issues/new?template=submit.yml) and paste the text of the card.
3. Wait for the comment. It takes a minute or two. Green: your entry is added and the issue is closed with a link. Red: the comment lists every reason; edit the issue (or comment `/recheck`) and it is checked again.

### What is checked

- The definition is valid for the nexdeck version of `kit/VERSION`, and `min_nexdeck` is not newer than that.
- Paths are relative to the connection, buttons use POST, PUT, PATCH or DELETE, nothing acts through a read.
- No key, token or password, in the definition, its demo data, the description or the list of changes.
- The sizes are within the limits (a definition with demo data: 60,000 characters).
- Texts in several languages have an English one; a card has demo data; the category is one of Media, Downloads, Network, Server, Smart home, Other.
- Your preview can be drawn.

The check class of an entry is `read` (only reads), `buttons` (has buttons that change something) or `login` (a connection that signs in). nexdeck shows it before anyone installs.

### Updates

Submit again with the same short name from the same account: it is an update, with a higher version and a list of changes.
Only the account that made an entry (by its numeric id; renaming the account changes nothing) and the maintainers can update it.
Somebody else who wants a different version makes a new entry and says "Based on" the first.
A maintainer updating another person's entry fills in "Update of" with the id of the entry.

An account can add 10 new entries a day; more wait for the next daily run.

### Taking an entry back

Comment `/withdraw` on the issue you submitted it with. It stays in the catalog as withdrawn by the author and cannot be installed any more.
Maintainers comment `/remove harmful <reason>` or `/remove not_useful <reason>`, or run the *moderate* workflow by hand.
What a maintainer removed stays removed: `/withdraw` does not change it and an update does not bring it back. Only a maintainer can, with `/restore` in the issue of the entry.

## For tools that make issues (nexdeck)

An issue is read from its Markdown body; the headings are the fields of the form: `### Type` (Card or Connection),
`### Category`, `### Definition` (a fenced `yaml` block), `### Description`, `### Changes`, `### Based on`,
`### Update of` (`_No response_` for an empty field) and `### License` with a ticked box `- [x] I submit this under the MIT License and I have the right to do so.`
`tools/issue_form.py` has `build_body`, which writes it.

## The tools

```
pip install -r requirements-dev.txt
python -m pytest
```

The actions run `tools/submit.py` (on every issue), `tools/daily.py` (once a day), `tools/moderate.py` (comments and manual removal) and `tools/publish.py`
(posts the comments after the files are pushed). `kit/` is made by `backend/tools/workshop_kit.py` in nexdeck and replaced as a whole.
