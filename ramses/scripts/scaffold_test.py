from nefertari.scripts.scaffold_test import (
    ScaffoldTestCommand as NefTestCommand)


class ScaffoldTestCommand(NefTestCommand):
    file = __file__


def main(*args, **kwargs):
    ScaffoldTestCommand().run()


if __name__ == '__main__':
    main()
