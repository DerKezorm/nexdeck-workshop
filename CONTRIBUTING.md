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
- The description is a few sentences of English: at least 3 words and 20 characters, with common words such as "the", "with" or "how". An update has a list of changes of at least 3 characters.
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

Every action runs `tools/work.py` (`python -m tools.work`), which works from the state of the repository and not from the event that woke it.
The actions are `submit` (an issue opened or edited), `moderate` (a comment) and `daily` (once a day, with `--daily`); `tools/publish.py` posts the comments after the files are pushed.
`kit/` is made by `backend/tools/workshop_kit.py` in nexdeck and replaced as a whole.

### Why a run works from the state

GitHub keeps one waiting run per concurrency group and drops the others when a newer one arrives. So a run cannot be trusted to be the one that
was started for a given event. Instead every run takes up everything that is still open: the submissions that changed since the last run
(`state.json` holds the moment; it only moves on when the run judged every issue it looked at), and the daily run takes up all of them.
A dropped run therefore costs nothing: what it was for is found by the next one. The comments of an issue are only read for the issues that
changed, and lists are read page by page up to their end.

Commands in comments (`/remove`, `/restore`, `/withdraw`, `/recheck`) work the same way: a run carries out every command it finds that
the bot has not marked done (the reply of the bot carries `<!-- workshop:done:<comment id> -->`), so it does not matter which run was started for a comment.
A removal started by hand (the *moderate* workflow) is first written to `orders/` by a job that is never dropped; every run carries out the
orders that lie there before it does anything else.

### Why the runs go one after the other, on the newest main

Every action that writes to `main` (`submit`, `daily` and the `order` and `comment` jobs of `moderate`) is in the one group `workshop-write`, with
`cancel-in-progress: false`: a run that started while another still works waits and is never cancelled. A run that waited must not work on what `main`
was when its event happened, so every checkout takes `ref: main`, the newest `main` at the moment the run starts. Eight issues opened within a minute
once made one run fail for exactly that reason: it had checked out the state of its event and met the `state.json` of the run before it.
`.github/scripts/push.sh` takes in the newest `main` again with `pull --rebase` before it pushes, and once more if the push is refused because `main`
moved in between (a person pushing, or the job that records an order, which has a group of its own so that it is never dropped). A conflict that is
left stops the run with the error; it is not resolved by guessing, and the next run finds the work again, since runs work from the state.
