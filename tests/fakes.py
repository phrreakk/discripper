"""In-memory adapters for the seams: run(args, log) that Disc and Encoder take,
and fetch(path, params) that MediaLookup takes."""

from media_lookup import LookupFailed


class FakeTool:
    """Records each run's args and writes canned output to its log.

    output is a function from args to the text the tool would print.
    """

    def __init__(self, output):
        self.output = output
        self.calls = []

    def __call__(self, args, log):
        self.calls.append(args)
        log.write_text(self.output(args), encoding="utf-8")


def handbrake_that_finishes(args):
    """What HandBrakeCLI prints at the end of a good encode; also writes the output file."""
    output = args[args.index("-o") + 1]
    with open(output, "w", encoding="utf-8"):
        pass
    return f'"File": "{output}"\nEncode done!\n'


def makemkv_that_copies(args):
    """What makemkvcon -r mkv prints after a good copy; also writes the Rip."""
    folder, title = args[-1], int(args[-2])
    with open(f"{folder}/title_t{title:02d}.mkv", "w", encoding="utf-8"):
        pass
    return 'MSG:5036,260,1,"Copy complete. 1 titles saved.","Copy complete. %1 titles saved.","1"\n'


class StrictTmdb:
    """Fetch seam adapter with canned JSON keyed by path, which fails like TMDB for any other path.

    Every request, answered or not, is recorded in calls.
    """

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, path, params):
        self.calls.append((path, params))
        if path not in self.responses:
            raise LookupFailed(f"404 Not Found: {path}")
        return self.responses[path]
