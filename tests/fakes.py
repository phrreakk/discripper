"""In-memory adapters for the run(args, log) seam that Disc and Encoder take."""


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
